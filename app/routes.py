from flask import request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from app.models import ImageHash
from app.utils.hashing import generate_hashes, generate_file_hash, calculate_similarity
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

    @app.route('/static/<path:filename>')
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
                
            if 'file' not in request.files:
                return jsonify({'status': 'error', 'error': 'No file uploaded'}), 400
                
            file = request.files['file']
            if file.filename == '':
                return jsonify({'status': 'error', 'error': 'Empty filename'}), 400

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
            temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, secure_filename(file.filename))
            file.save(temp_path)

            # Generate hashes
            file_hash = generate_file_hash(temp_path)
            perceptual_hashes = generate_hashes(temp_path)
            
            session = Session()
            
            # Check for duplicates
            duplicate = session.query(ImageHash).filter(
                (ImageHash.file_hash == file_hash) |
                (ImageHash.phash == perceptual_hashes['phash'])
            ).first()

            if duplicate:
                try:
                    similarity = 100 if duplicate.file_hash == file_hash else calculate_similarity(perceptual_hashes, duplicate)
                    return jsonify({
                        'status': 'duplicate',
                        'existing': duplicate.path,
                        'similarity': similarity
                    }), 200
                except Exception as e:
                    app.logger.error(f"Similarity calculation failed: {str(e)}")
                    return jsonify({
                        'status': 'error',
                        'error': 'Failed to calculate similarity'
                    }), 500

            # Permanent save with hash-based directory structure
            file_ext = os.path.splitext(filename)[1]
            permanent_dir = os.path.join(
                app.config['UPLOAD_FOLDER'], 
                'permanent',
                file_hash[:2], 
                file_hash[2:4]
            )
            os.makedirs(permanent_dir, exist_ok=True)
            permanent_path = os.path.join(permanent_dir, f"{file_hash}{file_ext}")

            # Atomic file move
            if os.path.exists(permanent_path):
                os.remove(temp_path)
            else:
                os.rename(temp_path, permanent_path)

            # Store in database
            new_image = ImageHash(
                path=permanent_path,
                file_hash=file_hash,
                **perceptual_hashes
            )
            session.add(new_image)
            session.commit()

            return jsonify({
                'status': 'success',
                'path': permanent_path,
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