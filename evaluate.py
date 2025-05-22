from app.utils.metrics import load_ground_truth, calculate_metrics
from app.models import ImageHash
from app.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.utils.hashing import calculate_similarity
import os

def evaluate_system(ground_truth_path: str, similarity_threshold: float = 70.0):
    # Load ground truth
    ground_truth = load_ground_truth(ground_truth_path)
    
    # Connect to database
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Get all images from database
    all_images = session.query(ImageHash).all()
    
    # Generate predictions
    predictions = {}
    for image in all_images:
        relative_path = os.path.relpath(image.path, str(Config.UPLOAD_FOLDER))
        similar_images = []
        
        for other_image in all_images:
            if other_image.path != image.path:
                similarity = calculate_similarity(
                    {'phash': image.phash, 'ahash': image.ahash, 'dhash': image.dhash},
                    other_image
                )
                if similarity >= similarity_threshold:
                    other_relative_path = os.path.relpath(other_image.path, str(Config.UPLOAD_FOLDER))
                    similar_images.append(other_relative_path)
        
        predictions[relative_path] = similar_images
    
    # Calculate metrics
    metrics = calculate_metrics(predictions, ground_truth)
    
    print("\nSystem Evaluation Results:")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall: {metrics['recall']:.4f}")
    print(f"F1 Score: {metrics['f1_score']:.4f}")
    
    session.close()
    return metrics

if __name__ == "__main__":
    evaluate_system("ground-truth.json")