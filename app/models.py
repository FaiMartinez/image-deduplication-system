from sqlalchemy import Column, Integer, String, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ImageHash(Base):
    __tablename__ = 'image_hashes'

    id = Column(Integer, primary_key=True)
    path = Column(String(256), unique=True)
    file_hash = Column(String(64), nullable=True)
    phash = Column(String(16), index=True)
    ahash = Column(String(16), index=True)
    dhash = Column(String(16), index=True)