from app.config import Config
from app.models import Base, Feedback
from sqlalchemy import create_engine

def init_feedback_table():
    try:
        engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
        
        # Create feedback table
        Feedback.__table__.create(engine, checkfirst=True)
        print("Feedback table initialized successfully")
        
    except Exception as e:
        print(f"Error initializing feedback table: {e}")

if __name__ == "__main__":
    init_feedback_table()
