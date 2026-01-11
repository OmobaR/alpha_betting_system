# AlphaBetting: A Football Match Outcome Prediction Project

This project predicts football match outcomes (Home Win, Draw, Away Win) using machine learning models trained on various football league datasets. The models implemented include Logistic Regression, Random Forest, and XGBoost, with an option for ensembling using a Voting Classifier.

The project is modular and flexible, allowing predictions for a single league dataset or multiple leagues combined.

---

## Project Structure

```
football-prediction-project/
│
├── data/                       # Data directory
│   ├── EnglishPremierLeague.csv
│   ├── SpanishLaliga.csv
│   ├── ItalianSerieA.csv
│   └── ...                     # More CSV files for different leagues
│
├── models/                     # Directory for saving trained models
│   ├── Logistic_Regression.pkl
│   ├── Random_Forest.pkl
│   ├── XGBoost.pkl
│   └── Ensemble_Model.pkl       # Saved ensemble model
│
├── notebooks/                  # Jupyter notebooks for experimentation
│   └── football_eda.ipynb       # Notebook for exploratory data analysis
│
├── src/                        # Source code directory
│   ├── __init__.py             # Initializes the src module
│   ├── app.py                  # FastAPI/Flask app for deployment
│   ├── data_loader.py          # Handles data loading and preprocessing
│   ├── download_leagues.py     # Downloads historical data from football-data.co.uk
│   ├── download_fixtures.py    # Downloads historical & fixture data from football-data.org
│   ├── evaluate_models.py      # Script for model evaluation
│   ├── feature_engineering.py  # Handles feature engineering
│   ├── model_ensembling.py     # Script for creating the ensemble model
│   ├── predict.py              # Script for making predictions
│   ├── train_models.py         # Script for training and saving models
│   └── utils.py                # General utility functions
│
├── tests/                      # Testing directory
│   └── test_data_loading.py    # Unit tests for data loading
│
├── requirements.txt            # Python dependencies
├── config.yaml                 # Configuration file for paths and settings
├── README.md                   # Project documentation
└── .gitignore                  # Ignore unnecessary files in git
```

---

## Key Features

1. **Multiple Model Training**: The project supports Logistic Regression, Random Forest, and XGBoost for training match outcome prediction models.
2. **Model Ensembling**: Combines individual models using a Voting Classifier for improved prediction accuracy.
3. **Flexibility**: Supports loading and processing data from multiple leagues or just a single league.
4. **Feature Engineering**: 
   - Uses rolling windows to capture form and performance trends.
   - Incorporates historical match outcomes, refined Elo ratings.
5. **API Deployment**: Uses FastAPI (or Flask) to create an API for making predictions based on new input data.
6. **Data Visualization**: Jupyter notebooks provide visual insights and exploratory data analysis (EDA).
7. **Model Evaluation**: Provides functionality for cross-validation and detailed evaluation metrics like F1-score, classification reports, and confusion matrices.

---

## Requirements

Install the required libraries by running:

```bash
pip install -r requirements.txt
```

- Python 3.8+
- Pandas, NumPy for data manipulation
- Scikit-learn for model training and evaluation
- XGBoost for gradient boosting
- Imbalanced-learn for handling class imbalance (SMOTE)
- Matplotlib, Seaborn for data visualization
- FastAPI/Flask for API deployment
- Joblib for model saving/loading
- PyArrow (optional) for faster data handling
- JupyterLab for notebook-based development

---

## Steps to Run the Program

### 1. Set Up the Project

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/football-prediction-project.git
   ```
2. Set up a Python virtual environment and activate it:
   ```bash
   python -m venv AlphaBet
   source AlphaBet/Scripts/activate  # For Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 2. Configure Data Source

The project supports two types of data sources:

- **Historical data only** (via football-data.co.uk)
- **Historical + Fixture data** (via football-data.org)

You can specify which data source to use in the `config.yaml` under the `data_source` section:

```yaml
data_source:
  type: "leagues"  # Use "leagues" for football-data.co.uk OR "fixtures" for football-data.org
```

#### Update config.yaml with your API key for football-data.org:

```yaml
download_fixtures:
  api_key: "YOUR_API_KEY"  # Your API key for football-data.org
  leagues: ["PL", "BL1", "SA", "FL1", "PD"]  # List of league codes to fetch fixtures for
```

### 3. Running the Program

To run the program, follow these steps:

1. **Run the main pipeline**:
   You can execute the `main.py` file, which automatically downloads the data (based on the configured data source), processes it, trains the models, evaluates them, and makes predictions.
   
   ```bash
   python main.py --multiple  # Use all leagues
   python main.py --single data/SpanishLaliga.csv  # Use a single league
   ```

2. **Switch between data sources**:
   If you want to switch between historical data (`download_leagues.py`) and fixtures data (`download_fixtures.py`), update the `config.yaml` file accordingly (under `data_source`).

### 4. Output CSV with Predictions

The predictions (including engineered features) will be saved as a CSV file in the path specified in the `config.yaml` under `predictions_output`. The CSV will include a column for the predictions (Home Win, Draw, Away Win):

```yaml
paths:
  predictions_output: "outputs/"
```

You will find the predictions saved as:

```
outputs/predictions_with_features.csv
```

---

## Step-by-Step Workflow

### 1. Data Loading

Load data from individual CSV files or combine multiple league datasets.

```python
from src.data_loader import load_and_preprocess_data, load_all_leagues

# Single league
df = load_and_preprocess_data('data/SpanishLaliga.csv')

# Multiple leagues
combined_df = load_all_leagues('data/')
```

### 2. Feature Engineering

Generate key features such as form points, rolling averages, and Elo ratings.

```python
from src.feature_engineering import generate_features

df = generate_features(df)
```

### 3. Model Training

Train models and save them as `.pkl` files.

```python
from src.train_models import train_and_save_models

train_and_save_models(X_train, y_train)
```

### 4. Model Evaluation

Evaluate the trained models on the test dataset.

```python
from src.evaluate_models import evaluate_model

evaluate_model('models/Random_Forest.pkl', X_test, y_test)
```

### 5. Model Ensembling

Combine models using the Voting Classifier and evaluate the ensemble.

```python
from src.model_ensembling import create_voting_ensemble

voting_clf = create_voting_ensemble(X_train, y_train, model_files)
```

### 6. Predict Outcomes

Make predictions on new data using the trained models.

```python
from src.predict import predict_new_data

predictions = predict_new_data(model, new_data)
```

---

## API Deployment (Optional)

Run the API server using FastAPI or Flask for real-time predictions:

```bash
python src/app.py
```

### API Endpoint

- **POST** `/predict`
  - Example input (JSON):
    ```json
    {
      "Home Team": "Real Madrid",
      "Away Team": "Barcelona",
      "1": 1.80,
      "X": 3.50,
      "2": 2.00
    }
    ```
  - Example response:
    ```json
    {
      "predictions": [0]
    }
    ```

---

## Unit Testing

To run the unit tests (located in the `tests/` directory), execute:

```bash
python -m unittest discover tests/
```

---

## Configuration

The project uses a configuration file (`config.yaml`) to define paths and parameters:

```yaml
data_path: "data/"
model_path: "models/"
test_size: 0.2
random_state: 42
```

---

## Jupyter Notebooks

Explore the data and experiment with feature engineering and modeling using the notebooks in the `notebooks/` folder.

---

## Future Enhancements

- **Hyperparameter Tuning**: Use `Optuna` or `GridSearchCV` for advanced hyperparameter tuning.
- **Additional Features**: Include player-level data or more advanced team statistics.
- **More Models**: Experiment with other models like LightGBM or neural networks.
- **Automated CI/CD**: Set up automated deployment pipelines using Docker and GitHub Actions.

---

## Contributors

- [Anthony O. Arotolu](https://github.com/OmobaR)
