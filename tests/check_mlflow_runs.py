import mlflow
import os
import sys

# --- Configuration ---
# Add the project root to the Python path to allow imports from other directories
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Set the MLflow tracking URI to the project's root mlruns directory
MLFLOW_TRACKING_URI = "file://" + os.path.join(project_root, "mlruns")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

def check_mlflow_runs():
    """
    Connects to the local MLflow tracking server and verifies the number of runs.
    """
    print(f"Connecting to MLflow at: {MLFLOW_TRACKING_URI}")

    try:
        # Get all experiments
        experiments = mlflow.search_experiments()
        if not experiments:
            print("❌ Test Failed: No MLflow experiments found.")
            print("   Please ensure you have run the training notebook/script first.")
            return False

        # In this project, all runs are likely in one experiment.
        # We will search across all experiments to be safe.
        experiment_ids = [exp.experiment_id for exp in experiments]
        
        # Search for all runs
        runs = mlflow.search_runs(experiment_ids=experiment_ids)
        num_runs = len(runs)

        print(f"🔍 Found a total of {num_runs} runs across all experiments.")

        # The requirement is at least 2 runs (baseline and ML model)
        # Your project actually has 3, which is even better.
        if num_runs >= 2:
            print(f"✅ Test Passed: Found {num_runs} runs (>= 2 required).")
            
            # Display the names of the runs found
            if "tags.mlflow.runName" in runs.columns:
                print("\n--- Run Names Found ---")
                for run_name in runs["tags.mlflow.runName"]:
                    print(f"- {run_name}")
                print("-----------------------")
            return True
        else:
            print(f"❌ Test Failed: Expected at least 2 runs, but found {num_runs}.")
            return False

    except Exception as e:
        print(f"An error occurred while trying to connect to MLflow: {e}")
        print("Please ensure that MLflow is configured correctly and that the `mlruns` directory exists.")
        return False

if __name__ == "__main__":
    check_mlflow_runs()
