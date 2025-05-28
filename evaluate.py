from app.utils.metrics import load_ground_truth, calculate_metrics
from app.models import ImageHash, Base
from app.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path

def evaluate_system():
    # Initialize database connection
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Load ground truth data
        ground_truth_path = os.path.join(Config.BASE_DIR, 'ground_truth.json')
        ground_truth = load_ground_truth(ground_truth_path)
        
        print(f"Loaded ground truth data with {len(ground_truth)} original images")
        print("Starting evaluation...")

        # Calculate metrics
        metrics = calculate_metrics(session, ImageHash, ground_truth)

        # Generate and save HTML report
        html_content = f"""
        <html>
        <head>
            <title>System Evaluation Results</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ padding: 12px; text-align: left; border: 1px solid #ddd; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                h2 {{ color: #333; }}
                .chart-container {{ width: 800px; height: 400px; margin: 20px auto; }}
                .confusion-matrix {{
                    border-collapse: collapse;
                    margin: 20px auto;
                }}
                .confusion-matrix td, .confusion-matrix th {{
                    border: 1px solid #ddd;
                    padding: 15px;
                    text-align: center;
                }}
                .confusion-matrix td.highlight {{
                    background-color: #e8f5e9;
                }}
            </style>
        </head>
        <body>
            <h2>System Evaluation Results</h2>
            <div class="chart-container">
                <canvas id="metricsChart"></canvas>
            </div>

            <h2>Overall Metrics</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Precision</td><td>{metrics['precision']:.4f}</td></tr>
                <tr><td>Recall</td><td>{metrics['recall']:.4f}</td></tr>
                <tr><td>F1 Score</td><td>{metrics['f1_score']:.4f}</td></tr>
                <tr><td>Total Processing Time</td><td>{metrics['timing']['total_time']:.2f} seconds</td></tr>
                <tr><td>Average Time per Image</td><td>{metrics['timing']['average_time']:.4f} seconds</td></tr>
            </table>

            <h2>Per-Image Statistics</h2>
            <table>
                <tr>
                    <th>Image</th>
                    <th>Found/Total</th>
                    <th>Detection Rate</th>
                    <th>Processing Time (s)</th>
                </tr>
                {''.join(f"<tr><td>{stat['image']}</td><td>{stat['found_duplicates']}/{stat['total_duplicates']}</td><td>{stat['detection_rate']:.2%}</td><td>{stat['processing_time']:.4f}</td></tr>" for stat in metrics['per_image_stats'])}
            </table>

            <h2>Confusion Matrix</h2>
            <table class="confusion-matrix">
                <tr>
                    <th></th>
                    <th>{metrics['confusion_matrix']['labels'][0]}</th>
                    <th>{metrics['confusion_matrix']['labels'][1]}</th>
                </tr>
                <tr>
                    <th>{metrics['confusion_matrix']['actual'][0]}</th>
                    <td class="highlight">{metrics['details']['true_positives']}</td>
                    <td>{metrics['details']['false_negatives']}</td>
                </tr>
                <tr>
                    <th>{metrics['confusion_matrix']['actual'][1]}</th>
                    <td>{metrics['details']['false_positives']}</td>
                    <td class="highlight">{metrics['details']['true_negatives']}</td>
                </tr>
            </table>

            <script>
                const ctx = document.getElementById('metricsChart');
                new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: ['Precision', 'Recall', 'F1 Score'],
                        datasets: [{{
                            label: 'Performance Metrics',
                            data: [{metrics['precision']}, {metrics['recall']}, {metrics['f1_score']}],
                            backgroundColor: ['rgba(75, 192, 192, 0.6)', 'rgba(54, 162, 235, 0.6)', 'rgba(153, 102, 255, 0.6)'],
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                max: 1
                            }}
                        }}
                    }}
                }});
            </script>
        </body>
        </html>
        """

        # Save the report
        report_path = os.path.join(Config.BASE_DIR, 'evaluation_report.html')
        with open(report_path, 'w') as f:
            f.write(html_content)

        print(f"Evaluation completed. Report saved to {report_path}")
        print(f"\nResults:")
        print(f"Precision: {metrics['precision']:.4f}")
        print(f"Recall: {metrics['recall']:.4f}")
        print(f"F1 Score: {metrics['f1_score']:.4f}")
        print(f"\nTiming Information:")
        print(f"Total processing time: {metrics['timing']['total_time']:.2f} seconds")
        print(f"Average time per image: {metrics['timing']['average_time']:.4f} seconds")

    except Exception as e:
        print(f"Error during evaluation: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    evaluate_system()