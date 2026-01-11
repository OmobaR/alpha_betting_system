import os
import joblib  # For saving models
import pandas as pd
from imblearn.combine import SMOTETomek  # Import SMOTETomek for balancing data
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix
import numpy as np

# --------------------------------------------------------------
# 1. Handle Sparse Data
# --------------------------------------------------------------
def handle_sparse_data(X_train, X_test):
    # Convert Pandas DataFrames to dense if any sparse columns exist
    if isinstance(X_train, pd.DataFrame):
        if any(isinstance(dtype, pd.SparseDtype) for dtype in X_train.dtypes):
            X_train = X_train.sparse.to_dense()
    if isinstance(X_test, pd.DataFrame):
        if any(isinstance(dtype, pd.SparseDtype) for dtype in X_test.dtypes):
            X_test = X_test.sparse.to_dense()

    # Ensure NumPy arrays are dense (if applicable)
    X_train = np.asarray(X_train) if isinstance(X_train, np.ndarray) else X_train
    X_test = np.asarray(X_test) if isinstance(X_test, np.ndarray) else X_test

    return X_train, X_test


# --------------------------------------------------------------
# 2. Target Encoding
# --------------------------------------------------------------
def encode_target(df):
    df['Result_Numeric'] = df['Result'].map({'H': 0, 'D': 1, 'A': 2})
    return df

# --------------------------------------------------------------
# 3. Label Encoding for Team Names
# --------------------------------------------------------------
def encode_teams(df):
    label_encoder = LabelEncoder()
    df['Home Team'] = label_encoder.fit_transform(df['Home Team'])
    df['Away Team'] = label_encoder.transform(df['Away Team'])
    return df

# --------------------------------------------------------------
# 4. Date Feature Transformation
# --------------------------------------------------------------
def transform_dates(df):
    df['days_since_reference'] = (df['Date'] - pd.Timestamp('1970-01-01')).dt.days
    df = df.drop(columns=['Date'])
    return df

# --------------------------------------------------------------
# 5. Feature Selection: Dropping Redundant Features
# --------------------------------------------------------------
def select_features(df):
    drop_columns = ['HG', 'AG', 'home_win', 'away_loss', 'away_win', 'home_loss', 'Result', 'Result_Numeric']
    return df.drop(columns=drop_columns)

# --------------------------------------------------------------
# 6. Train-Test Split
# --------------------------------------------------------------
def split_data(df_clean, df):
    X = df_clean  # Features
    y = df['Result_Numeric']  # Target
    return train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# --------------------------------------------------------------
# 7. Feature Scaling (StandardScaler)
# --------------------------------------------------------------
def scale_features(X_train, X_test):
    scaler = StandardScaler()
    return scaler.fit_transform(X_train), scaler.transform(X_test), scaler

# --------------------------------------------------------------
# 8. Handling Class Imbalance with SMOTETomek
# --------------------------------------------------------------
def apply_smote_tomek(X_train, y_train):
    smt = SMOTETomek(random_state=42)
    return smt.fit_resample(X_train, y_train)

# --------------------------------------------------------------
# 9. Hyperparameter Tuning Function (with GridSearchCV)
# --------------------------------------------------------------
def hyperparameter_tuning(model, param_grid, X_train, y_train):
    grid_search = GridSearchCV(model, param_grid, cv=5, scoring='f1_macro', n_jobs=-1)
    grid_search.fit(X_train, y_train)
    return grid_search.best_estimator_

# --------------------------------------------------------------
# 10. Train Multiple Classifiers with Hyperparameter Tuning
# --------------------------------------------------------------
def train_models(X_train_smote, y_train_smote, config):
    log_reg_params = config['model_training']['models']['Logistic_Regression']
    rf_params = config['model_training']['models']['Random_Forest']
    xgb_params = config['model_training']['models']['XGBoost']

    models = {
        'Logistic_Regression': LogisticRegression(),
        'Random_Forest': RandomForestClassifier(random_state=config['project']['random_state']),
        'XGBoost': XGBClassifier(random_state=config['project']['random_state'])
    }

    param_grids = {
        'Random_Forest': {
            'n_estimators': [100, 200, 300],
            'max_depth': [10, 20, 30],
            'min_samples_split': [2, 5, 10]
        },
        'XGBoost': {
            'n_estimators': [100, 200, 300],
            'max_depth': [3, 6, 9],
            'learning_rate': [0.01, 0.1, 0.2]
        }
    }

    models['Logistic_Regression'] = LogisticRegression(
        max_iter=log_reg_params['max_iter'],
        class_weight=log_reg_params['class_weight'],
        solver=log_reg_params['solver']
    ).fit(X_train_smote, y_train_smote)

    print("\nHyperparameter tuning for Random Forest...")
    models['Random_Forest'] = hyperparameter_tuning(models['Random_Forest'], param_grids['Random_Forest'], X_train_smote, y_train_smote)

    print("\nHyperparameter tuning for XGBoost...")
    # --- Conversion of sparse data to dense (if applicable) ---
    if isinstance(X_train_smote, pd.DataFrame):
        X_train_smote = X_train_smote.sparse.to_dense() if isinstance(X_train_smote.dtypes, pd.SparseDtype) else X_train_smote
    elif isinstance(X_train_smote, np.ndarray):
        X_train_smote = np.asarray(X_train_smote)
        
    models['XGBoost'] = hyperparameter_tuning(models['XGBoost'], param_grids['XGBoost'], X_train_smote, y_train_smote)

    return models

# --------------------------------------------------------------
# 11. Save Models as .pkl Files
# --------------------------------------------------------------
def save_models(models, config):
    folder_path = config['paths']['models_folder']
    os.makedirs(folder_path, exist_ok=True)
    
    for name, model in models.items():
        file_path = os.path.join(folder_path, f"{name}.pkl")
        joblib.dump(model, file_path)
        print(f"Saved {name} model to {file_path}")

# --------------------------------------------------------------
# 12. Main Execution - Training and Saving Models
# --------------------------------------------------------------
if __name__ == "__main__":
    # Load preprocessed DataFrame (from feature engineering)
    df = pd.read_csv('SpanishLaliga_Eng.csv')

    # Handle Sparse Data - Convert to dense if necessary
    df = handle_sparse_data(df)
    
    # Run all preprocessing steps
    df = encode_target(df)
    df = encode_teams(df)
    df = transform_dates(df)
    
    # Select features and perform train-test split
    df_clean = select_features(df)
    X_train, X_test, y_train, y_test = split_data(df_clean, df)
    
    # Scale features
    X_train_scaled, X_test_scaled, scaler = scale_features(X_train, X_test)
    
    # Handle class imbalance with SMOTETomek
    X_train_smote, y_train_smote = apply_smote_tomek(X_train_scaled, y_train)
    
    # Train models
    models = train_models(X_train_smote, y_train_smote, config)
    
    # Save trained models as .pkl files
    save_models(models, config)
