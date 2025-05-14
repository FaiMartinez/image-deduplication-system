from app.models import ImageHash
from app.config import Config
from sqlalchemy import create_engine
import shutil
import os

def cleanup():
    # Connect to database
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    
    # Delete all records
    ImageHash.__table__.drop(engine)
    ImageHash.__table__.create(engine)
    
    # Remove uploads directory and recreate it
    if os.path.exists(Config.UPLOAD_FOLDER):
        shutil.rmtree(Config.UPLOAD_FOLDER)
    
    # Recreate directories
    Config.create_dirs()
    
    print("Database and uploads folder have been reset")

if __name__ == "__main__":
    cleanup()