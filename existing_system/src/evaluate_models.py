import joblib
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from src.utils import load_model  # Use the load_model from utils for consistency

def evaluate_model(model_path, X_test, y_test):
    """
    Evaluate the loaded model on the test data.

    Args:
        model_path (str): Path to the saved model file.
        X_test (pd.DataFrame): Test features.
        y_test (pd.Series): True labels for the test set.

    Returns:
        tuple: (y_pred, y_test) - Predicted and actual labels.
    """
    # Load the model from the provided path
    model = load_model(model_path)
    
    # Check if the model was successfully loaded
    if model is None:
        print(f"Error: Model could not be loaded from {model_path}")
        return None, None

    # Make predictions on the test set
    y_pred = model.predict(X_test)

    # Calculate and print evaluation metrics
    print(f"Model Evaluation Metrics for {model_path}:")
    print("----------------------------")
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print("Classification Report:\n", classification_report(y_test, y_pred))
    print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred))

    # Return predictions and actuals for further analysis
    return y_pred, y_test


# Example usage for testing the script directly
if __name__ == "__main__":
    # Example: You should load or prepare X_test and y_test before calling evaluate_model
    # X_test, y_test = load_test_data() # Example loading/placeholder function
    # evaluate_model("models/Random_Forest.pkl", X_test, y_test)
    
    print("Run this module from the main script for proper test data input.")
