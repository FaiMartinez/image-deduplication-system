import json
from pathlib import Path
import os
from ..utils.hashing import calculate_similarity
from ..config import Config
import time

def load_ground_truth(json_path):
    """Load ground truth data from JSON file"""
    with open(json_path, 'r') as f:
        return json.load(f)

def normalize_path_for_comparison(path):
    """Convert any path to format matching ground truth (image0000/original.jpg)"""
    try:
        # Convert path to Path object
        path = Path(path)
        
        # Get the parts after 'uploads' instead of 'temp'
        if 'uploads' in str(path):
            parts = str(path).split('uploads')[-1].strip(os.sep).split(os.sep)
        else:
            parts = str(path).split(os.sep)
        
        # Get the last two parts (folder and filename)
        relevant_parts = parts[-2:]
        # Join with forward slash to match ground truth format
        return '/'.join(relevant_parts)
    except Exception as e:
        print(f"Error normalizing path {path}: {str(e)}")
        return str(path)

def calculate_metrics(session, ImageHash, ground_truth, similarity_threshold=80):
    """Calculate precision, recall, and F1 score using database records"""
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    true_negatives = 0
    per_image_stats = []

    # Get all images from database
    all_images = session.query(ImageHash).all()
    print(f"Total images in database: {len(all_images)}")

    # Create lookup dictionary with normalized paths
    image_dict = {}
    for img in all_images:
        norm_path = normalize_path_for_comparison(img.path)
        image_dict[norm_path] = img
        print(f"Normalized path: {norm_path} <- {img.path}")

    # Process each original image in ground truth
    total_start_time = time.time()
    
    for original, duplicates in ground_truth.items():
        image_start_time = time.time()
        print(f"\nProcessing original: {original}")
        
        # Find the original image in database
        original_record = image_dict.get(original)
        if not original_record:
            print(f"Warning: Original image not found in database: {original}")
            print("Available paths:", list(image_dict.keys())[:5])
            continue

        # Convert duplicate paths to set for comparison
        actual_duplicates = set(duplicates)
        all_possible_images = set(image_dict.keys())
        actual_non_duplicates = all_possible_images - {original} - actual_duplicates
        
        # Find detected duplicates
        detected_duplicates = set()
        for img in all_images:
            norm_path = normalize_path_for_comparison(img.path)
            if norm_path == original:
                continue
                
            similarity = calculate_similarity(
                {
                    'phash': original_record.phash,
                    'ahash': original_record.ahash,
                    'dhash': original_record.dhash
                },
                img
            )
            
            if similarity >= similarity_threshold:
                detected_duplicates.add(norm_path)

        # Calculate metrics for this image
        true_pos = len(actual_duplicates & detected_duplicates)
        false_pos = len(detected_duplicates - actual_duplicates)
        false_neg = len(actual_duplicates - detected_duplicates)
        true_neg = len(actual_non_duplicates - detected_duplicates)
        
        image_time = time.time() - image_start_time
        
        per_image_stats.append({
            'image': original,
            'found_duplicates': len(detected_duplicates),
            'total_duplicates': len(actual_duplicates),
            'detection_rate': true_pos / len(actual_duplicates) if actual_duplicates else 1.0,
            'processing_time': image_time,
            'true_positives': true_pos,
            'false_positives': false_pos,
            'false_negatives': false_neg,
            'true_negatives': true_neg
        })

        print(f"Expected duplicates: {actual_duplicates}")
        print(f"Found duplicates: {detected_duplicates}")
        print(f"True positives: {true_pos}")

        true_positives += true_pos
        false_positives += false_pos
        false_negatives += false_neg
        true_negatives += true_neg

    total_time = time.time() - total_start_time

    # Calculate final metrics
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return {
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'details': {
            'true_positives': true_positives,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'true_negatives': true_negatives
        },
        'confusion_matrix': {
            'matrix': [
                [true_positives, false_positives],
                [false_negatives, true_negatives]
            ],
            'labels': ['Predicted Positive', 'Predicted Negative'],
            'actual': ['Actual Positive', 'Actual Negative']
        },
        'timing': {
            'total_time': total_time,
            'average_time': total_time / len(ground_truth)
        },
        'per_image_stats': per_image_stats
    }