# predict.py
import joblib
import pandas as pd
from data_loader import load_and_preprocess_data  # Load data loading function
from feature_engineering import apply_feature_engineering  # Load feature engineering function

def load_model(model_path):
    """Load the trained model from a .pkl file."""
    return joblib.load(model_path)

def make_prediction(model, match_data):
    """
    Make predictions using the trained model.
    
    Args:
        model: The trained machine learning model (e.g., Random Forest, XGBoost)
        match_data: Processed feature data for the match to predict
        
    Returns:
        Prediction result (e.g., Home win, Draw, Away win)
    """
    # Model expects a 2D array, even for a single sample
    prediction = model.predict(match_data)
    
    # You may need to map numeric prediction back to the original result (e.g., H=0, D=1, A=2)
    result_mapping = {0: 'Home Win', 1: 'Draw', 2: 'Away Win'}
    return result_mapping[prediction[0]]

def process_match_for_prediction(df, match_info):
    """
    Process a single match for prediction by applying feature engineering steps.
    
    Args:
        df: DataFrame with the historical data
        match_info: Dictionary containing match details (teams, date, odds, etc.)
        
    Returns:
        match_data: Processed features for the match
    """
    # Add new match info to historical data for feature engineering
    df = df.append(match_info, ignore_index=True)
    
    # Apply the same feature engineering used during training
    df = apply_feature_engineering(df)
    
    # Extract features for the new match (last row in DataFrame)
    match_data = df.iloc[[-1]].drop(columns=['Result', 'Date', 'Season'])  # Drop unnecessary columns
    
    return match_data

def predict_next_match(model_path, historical_data_path, new_match_info):
    """
    Make a prediction for an upcoming match.
    
    Args:
        model_path: Path to the trained model (.pkl file)
        historical_data_path: Path to the CSV file with historical match data
        new_match_info: Dictionary with details of the new match to predict
        
    Returns:
        Prediction result (Home Win, Draw, Away Win)
    """
    # Load historical data
    historical_data = load_and_preprocess_data(historical_data_path)
    
    # Load the trained model
    model = load_model(model_path)
    
    # Process the match for prediction (apply feature engineering)
    match_data = process_match_for_prediction(historical_data, new_match_info)
    
    # Make the prediction
    result = make_prediction(model, match_data)
    
    return result

# Example usage
if __name__ == "__main__":
    model_path = "models/Random_Forest.pkl"
    historical_data_path = "data/SpanishLaliga.csv"
    
    # New match information (example)
    new_match_info = {
        'Date': '2024-09-24',
        'Season': '2024/2025',
        'Home Team': 'Barcelona',
        'Away Team': 'Real Madrid',
        'HG': None,  # Home goals (to be predicted)
        'AG': None,  # Away goals (to be predicted)
        'Result': None  # Result (to be predicted)
    }
    
    # Make the prediction
    prediction = predict_next_match(model_path, historical_data_path, new_match_info)
    print(f"Prediction for the match: {prediction}")
