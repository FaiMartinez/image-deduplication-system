import shutil
import os
from pathlib import Path
from app.config import Config

def reset_data():
    # Remove database file
    db_path = Path(Config.BASE_DIR) / 'instance' / 'image_database.db'
    if db_path.exists():
        os.remove(db_path)
        print("Database deleted successfully")
    
    # Remove uploads directory
    uploads_dir = Config.UPLOAD_FOLDER
    if uploads_dir.exists():
        shutil.rmtree(str(uploads_dir))
        print("Uploads folder deleted successfully")
    
    # Remove temp directory
    temp_dir = Config.TEMP_FOLDER
    if temp_dir.exists():
        shutil.rmtree(str(temp_dir))
        print("Temp folder deleted successfully")
    
    # Recreate necessary directories
    Config.create_dirs()
    print("Directories recreated successfully")

if __name__ == "__main__":
    reset_data()