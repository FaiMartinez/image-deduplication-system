from app.config import Config
from app.models import ImageHash, Base
from app.utils.hashing import generate_hashes, generate_file_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path
import time

def init_database(engine):
    Base.metadata.create_all(engine)

def calculate_image_hashes(image_path):
    """Wrapper function to get all hashes for an image"""
    perceptual_hashes = generate_hashes(image_path)
    file_hash = generate_file_hash(image_path)
    return {**perceptual_hashes, 'file_hash': file_hash}

def import_images(batch_size=100):
    start_time = time.time()
    processed_count = 0
    batch_count = 0
    
    # Connect to database
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    init_database(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        batch = []
        # Walk through the uploads directory
        for root, _, files in os.walk(Config.UPLOAD_FOLDER):
            for file in files:
                if file.endswith(('.jpg', '.jpeg', '.png')):
                    image_path = os.path.join(root, file)
                    
                    # Check if image already exists in database
                    existing_image = session.query(ImageHash).filter_by(path=image_path).first()
                    if existing_image:
                        print(f"Skipping {image_path} - already in database")
                        continue

                    try:
                        # Calculate all hashes including file hash
                        hashes = calculate_image_hashes(image_path)
                        
                        # Create new database entry
                        image_hash = ImageHash(
                            path=image_path,
                            **hashes
                        )
                        batch.append(image_hash)
                        processed_count += 1

                        # Commit in batches
                        if len(batch) >= batch_size:
                            session.bulk_save_objects(batch)
                            session.commit()
                            batch_count += 1
                            print(f"Committed batch {batch_count} ({processed_count} images processed)")
                            batch = []

                    except Exception as e:
                        print(f"Error processing {image_path}: {str(e)}")
                        continue

        # Commit any remaining items
        if batch:
            session.bulk_save_objects(batch)
            session.commit()

        end_time = time.time()
        duration = end_time - start_time
        print(f"\nImport completed successfully!")
        print(f"Processed {processed_count} images in {duration:.2f} seconds")
        print(f"Average speed: {processed_count/duration:.2f} images/second")
        
    except Exception as e:
        print(f"Error during import: {str(e)}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    import_images()
