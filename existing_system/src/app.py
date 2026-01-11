# app.py
from flask import Flask, request, jsonify
import pandas as pd
from predict import predict_new_data
import joblib
from src.feature_engineering import engineer_features

# Initialize Flask app
app = Flask(__name__)

# Load the pre-trained models into memory
rf_model = joblib.load('models/Random_Forest.pkl')
xgb_model = joblib.load('models/XGBoost.pkl')
lr_model = joblib.load('models/Logistic_Regression.pkl')
voting_ensemble = joblib.load('models/voting_ensemble.pkl')

@app.route('/predict', methods=['POST'])
def predict():
    """
    Predict the match outcome given the input data.
    
    Example input (JSON):
    {
        "Home Team": "TeamA",
        "Away Team": "TeamB",
        "1": 2.0,
        "X": 3.5,
        "2": 1.8
    }
    """
    try:
        # Get JSON data from the request
        data = request.get_json()

        # Convert JSON data to DataFrame (for prediction)
        new_data = pd.DataFrame([data])

        # Perform feature engineering on the new data
        new_data = engineer_features(new_data)

        # Make predictions using individual models
        rf_prediction = predict_new_data(rf_model, new_data)
        xgb_prediction = predict_new_data(xgb_model, new_data)
        lr_prediction = predict_new_data(lr_model, new_data)

        # Make prediction using the ensemble model
        ensemble_prediction = predict_new_data(voting_ensemble, new_data)

        # Return predictions as a JSON response
        return jsonify({
            'Random_Forest_Prediction': rf_prediction.tolist(),
            'XGBoost_Prediction': xgb_prediction.tolist(),
            'Logistic_Regression_Prediction': lr_prediction.tolist(),
            'Ensemble_Prediction': ensemble_prediction.tolist()
        })

    except Exception as e:
        return jsonify({'error': str(e)})

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
