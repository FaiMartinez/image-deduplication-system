from pathlib import Path
import os

class Config:
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
    ALLOWED_MIME_TYPES = {
        'image/png', 
        'image/jpeg', 
        'image/webp', 
        'image/gif'
    }
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB (REQUIRED)
    
    SQLALCHEMY_ENGINE = None
    # 1. Define BASE_DIR first
    BASE_DIR = Path(__file__).resolve().parent.parent
    
    # 2. Now use it in other configurations
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{BASE_DIR}/instance/image_database.db'
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    TEMP_FOLDER = BASE_DIR / 'uploads' / 'temp'
    
    # 3. Fix in create_dirs method
    @classmethod
    def create_dirs(cls):
        dirs_to_create = [
            cls.UPLOAD_FOLDER,
            cls.TEMP_FOLDER,
            cls.BASE_DIR / 'instance'
        ]
        
        for directory in dirs_to_create:
            directory.mkdir(parents=True, exist_ok=True)

# 4. Initialize directories
Config.create_dirs()