from flask import Flask
from pathlib import Path
import os

def create_app():
    # Configure template paths for VSCode
    base_dir = Path(__file__).resolve().parent.parent
    template_path = base_dir / 'templates'
    static_path = base_dir / 'static'
    
    app = Flask(__name__, 
              template_folder=str(template_path),
              static_folder=str(static_path))
    
    app.config.from_object('app.config.Config')
    
    # Initialize database and tables
    from .models import Base, ImageHash, Feedback
    from sqlalchemy import create_engine
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    app.config['SQLALCHEMY_ENGINE'] = engine
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Register routes
    from .routes import register_routes
    register_routes(app)
    
    return app