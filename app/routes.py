from flask import request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from app.models import ImageHash
from app.utils.hashing import generate_hashes, calculate_similarity
from sqlalchemy.orm import sessionmaker
from werkzeug.exceptions import RequestEntityTooLarge
import os
import time
import traceback
import magic

def register_routes(app):
    engine = app.config['SQLALCHEMY_ENGINE']
    Session = sessionmaker(bind=engine)

    @app.route('/')
    def home():
        return render_template('index.html')

    @app.route('/uploads/<path:filename>')
    def serve_image(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.route('/upload', methods=['POST'])
    def upload_image():
        start_time = time.time()
        
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'error': 'Empty filename'}), 400

        try:
            # Add file size validation
            max_size = app.config.get('MAX_CONTENT_LENGTH', 0)
            if max_size and request.content_length and request.content_length > max_size:
                raise RequestEntityTooLarge(f"File exceeds {max_size//(1024*1024)}MB limit")
                
            # Validate file extension
            filename = secure_filename(file.filename)
            allowed_extensions = app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'webp'})
            if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
                return jsonify({'status': 'error', 'error': 'Invalid file extension'}), 400

            file_stream = file.stream
            file_start = file_stream.read(1024)
            file_stream.seek(0)

            mime = magic.Magic(mime=True)
            file_type = mime.from_buffer(file_start)
            allowed_types = app.config.get('ALLOWED_MIME_TYPES', set())

            if file_type not in allowed_types:
                return jsonify({
                    'status': 'error',
                    'error': f'Invalid file type: {file_type}'
                }), 400

            # Temporary save
            temp_dir = str(app.config['TEMP_FOLDER'])
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, secure_filename(file.filename))
            file.save(temp_path)

            # Generate perceptual hashes
            perceptual_hashes = generate_hashes(temp_path)
            app.logger.debug(f"Generated hashes for uploaded image: {perceptual_hashes}")
            
            session = Session()
            
            # Check for similar images based on perceptual hashes
            duplicates = session.query(ImageHash).filter(
                ImageHash.phash != None  # Ensure phash exists for comparison
            ).all()

            if duplicates:
                try:
                    # Calculate similarity for all duplicates
                    results = []
                    for duplicate in duplicates:
                        app.logger.debug(f"Comparing with duplicate: path={duplicate.path}, hashes={duplicate.__dict__}")
                        similarity = calculate_similarity(perceptual_hashes, duplicate)
                        app.logger.debug(f"Similarity score: {similarity}")
                        if similarity is None or not isinstance(similarity, (int, float)):
                            app.logger.error(f"Invalid similarity score for {duplicate.path}: {similarity}")
                            continue
                        # Only include matches above a similarity threshold (e.g., 70%)
                        if similarity >= app.config.get('SIMILARITY_THRESHOLD', 70):
                            relative_path = os.path.relpath(duplicate.path, str(app.config['UPLOAD_FOLDER'])).replace('\\', '/')
                            results.append({
                                'path': relative_path,
                                'similarity': float(similarity)  # Ensure numeric value
                            })

                    if results:
                        # Sort results by similarity (descending)
                        results.sort(key=lambda x: x['similarity'], reverse=True)
                        os.remove(temp_path)  # Remove temp file since we found similar images
                        return jsonify({
                            'status': 'duplicate',
                            'matches': results,
                            'message': f'Found {len(results)} similar image(s)'
                        }), 200

                except Exception as e:
                    app.logger.error(f"Similarity calculation failed: {str(e)}\n{traceback.format_exc()}")
                    return jsonify({
                        'status': 'error',
                        'error': 'Failed to calculate similarity'
                    }), 500

            # If no similar images found, proceed with permanent save
            file_ext = os.path.splitext(filename)[1]
            # Use a simple directory structure
            permanent_dir = str(app.config['UPLOAD_FOLDER'])
            os.makedirs(permanent_dir, exist_ok=True)
            # Use a timestamp-based filename to avoid collisions
            timestamp = str(int(time.time() * 1000))
            permanent_path = os.path.join(permanent_dir, f"{timestamp}{file_ext}")

            # Atomic file move
            if os.path.exists(permanent_path):
                os.remove(temp_path)
            else:
                os.rename(temp_path, permanent_path)

            # Store in database without file_hash
            new_image = ImageHash(
                path=permanent_path,
                **perceptual_hashes
            )
            session.add(new_image)
            session.commit()

            relative_path = os.path.relpath(permanent_path, str(app.config['UPLOAD_FOLDER']))
            return jsonify({
                'status': 'success',
                'path': relative_path,
                'processing_time': time.time() - start_time
            }), 201
        
        except RequestEntityTooLarge:
            return jsonify({
                'status': 'error',
                'error': f'File too large (max {app.config["MAX_CONTENT_LENGTH"]//(1024*1024)}MB)'
            }), 413

        except Exception as e:
            app.logger.error(f"Upload error: {str(e)}\n{traceback.format_exc()}")
            return jsonify({
                'status': 'error',
                'error': 'Server error'
            }), 500
        finally:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            if 'session' in locals():
                session.close()

