import hashlib
import imagehash
from PIL import Image

def calculate_similarity(new_hashes, existing_record):
    """Calculate similarity percentage between new and existing hashes"""
    total_similarity = 0
    hash_types = ['phash', 'ahash', 'dhash']
    
    for hash_type in hash_types:
        new_hash = imagehash.hex_to_hash(new_hashes[hash_type])
        existing_hash = imagehash.hex_to_hash(getattr(existing_record, hash_type))
        max_bits = len(new_hash.hash) ** 2
        similarity = 100 * (1 - (new_hash - existing_hash) / max_bits)
        total_similarity += similarity
    
    return round(total_similarity / len(hash_types), 2)

def generate_hashes(image_path):
    with Image.open(image_path) as img:
        return {
            'phash': str(imagehash.phash(img)),
            'ahash': str(imagehash.average_hash(img)),
            'dhash': str(imagehash.dhash(img))
        }

def generate_file_hash(image_path):
    sha256 = hashlib.sha256()
    with open(image_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()