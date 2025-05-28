from sqlalchemy import Column, Integer, String, Index, cast, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class ImageHash(Base):
    __tablename__ = 'image_hashes'

    id = Column(Integer, primary_key=True)
    path = Column(String(256), unique=True, index=True)
    file_hash = Column(String(64), nullable=True, index=True)
    phash = Column(String(16), index=True)
    ahash = Column(String(16), index=True)
    dhash = Column(String(16), index=True)

    # Optimized indexes for similarity searches
    __table_args__ = (
        Index('idx_hashes_combined', 'phash', 'ahash', 'dhash'),
        Index('idx_phash_cast', cast(phash, Integer)),
        Index('idx_ahash_cast', cast(ahash, Integer)),
        Index('idx_dhash_cast', cast(dhash, Integer))
    )

class Feedback(Base):
    __tablename__ = 'user_feedback'

    id = Column(Integer, primary_key=True)
    accuracy_rating = Column(Integer)  # 1-5 rating for accuracy
    speed_rating = Column(Integer)     # 1-5 rating for speed
    found_duplicates = Column(Boolean) # Whether duplicates were found
    comments = Column(String(500))     # User comments
    created_at = Column(DateTime, default=datetime.utcnow)