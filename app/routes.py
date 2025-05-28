from flask import request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from app.models import ImageHash, Feedback
from app.utils.hashing import generate_hashes, calculate_similarity, generate_file_hash
from sqlalchemy.orm import sessionmaker
from werkzeug.exceptions import RequestEntityTooLarge
from sqlalchemy import func, or_
import os
import time
import traceback
import magic
import imagehash

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
            
            try:
                # First check for exact matches
                exact_matches = session.query(ImageHash).filter(
                    or_(
                        ImageHash.phash == perceptual_hashes['phash'],
                        ImageHash.ahash == perceptual_hashes['ahash'],
                        ImageHash.dhash == perceptual_hashes['dhash']
                    )
                ).all()

                # If no exact matches, get potential matches for similarity check
                potential_matches = session.query(ImageHash).limit(1000).all() if not exact_matches else []
                
                results = []
                # Process exact matches first
                for match in exact_matches:
                    relative_path = os.path.relpath(match.path, str(app.config['UPLOAD_FOLDER'])).replace('\\', '/')
                    results.append({
                        'path': relative_path,
                        'similarity': 100.0  # Exact match
                    })

                # Then process potential matches
                similarity_threshold = app.config.get('SIMILARITY_THRESHOLD', 70)
                for match in potential_matches:
                    try:
                        similarity = calculate_similarity(perceptual_hashes, match)
                        
                        if similarity >= similarity_threshold:
                            relative_path = os.path.relpath(match.path, str(app.config['UPLOAD_FOLDER'])).replace('\\', '/')
                            results.append({
                                'path': relative_path,
                                'similarity': float(similarity)
                            })
                            
                            # Early exit if we found enough matches
                            if len(results) >= 100:  # Limit max results
                                break
                                
                    except Exception as e:
                        app.logger.error(f"Error comparing with {match.path}: {str(e)}")
                        continue

                if results:
                    # Sort results by similarity (descending)
                    results.sort(key=lambda x: x['similarity'], reverse=True)
                    os.remove(temp_path)
                    return jsonify({
                        'status': 'duplicate',
                        'matches': results[:10],  # Return top 10 matches
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

    @app.route('/feedback', methods=['POST'])
    def submit_feedback():
        try:
            data = request.json
            session = Session()
            
            feedback = Feedback(
                accuracy_rating=data.get('accuracyRating'),
                speed_rating=data.get('speedRating'),
                found_duplicates=data.get('foundDuplicates'),
                comments=data.get('comments')
            )
            
            session.add(feedback)
            session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Thank you for your feedback!'
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error saving feedback: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Unable to save feedback'
            }), 500
        finally:
            if 'session' in locals():
                session.close()

