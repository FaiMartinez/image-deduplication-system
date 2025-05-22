from typing import Dict, List, Set
import json
from pathlib import Path

def load_ground_truth(ground_truth_path: str) -> Dict[str, List[str]]:
    """Load ground truth data from JSON file."""
    with open(ground_truth_path, 'r') as f:
        return json.load(f)

def calculate_metrics(predictions: Dict[str, List[str]], ground_truth: Dict[str, List[str]]) -> Dict[str, float]:
    """
    Calculate precision, recall, and F1 score.
    
    Args:
        predictions: Dict mapping image paths to lists of predicted similar images
        ground_truth: Dict mapping image paths to lists of actual similar images
    """
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    
    for image, predicted_matches in predictions.items():
        if image not in ground_truth:
            continue
            
        true_matches = set(ground_truth[image])
        predicted_set = set(predicted_matches)
        
        # Calculate metrics components
        true_positives += len(true_matches.intersection(predicted_set))
        false_positives += len(predicted_set - true_matches)
        false_negatives += len(true_matches - predicted_set)
    
    # Calculate final metrics
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score
    }