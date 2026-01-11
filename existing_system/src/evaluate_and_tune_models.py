import os
import joblib
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.model_selection import StratifiedKFold, cross_val_score, GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

# --------------------------------------------------------------
# 1. Evaluate Models
# --------------------------------------------------------------
def evaluate_model(model, X_test, y_test):
    """
    Evaluate a model by generating classification reports and confusion matrices.
    
    Args:
        model: The trained model (Logistic Regression, Random Forest, XGBoost, etc.).
        X_test (pd.DataFrame): Test features.
        y_test (pd.Series): Test labels.
    
    Returns:
        None
    """
    y_pred = model.predict(X_test)
    
    print(f"Model Evaluation for {model.__class__.__name__}")
    print("Classification Report:")
    print(classification_report(y_test, y_pred))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    print("\n")

# --------------------------------------------------------------
# 2. Cross-Validation and Hyperparameter Tuning
# --------------------------------------------------------------
def cross_validate_and_tune(models, X_train, y_train):
    """
    Perform cross-validation and hyperparameter tuning for models.

    Args:
        models (dict): Dictionary of models to tune.
        X_train (pd.DataFrame): Training feature set.
        y_train (pd.Series): Training labels.

    Returns:
        None
    """
    skf = StratifiedKFold(n_splits=5)
    
    for name, model in models.items():
        print(f"\nCross-validating {name}...")

        # Perform 5-fold cross-validation
        cv_scores = cross_val_score(model, X_train, y_train, cv=skf, scoring='f1_macro')
        print(f"{name} Cross-Validation Scores: {cv_scores}")
        print(f"{name} Average CV Score: {cv_scores.mean():.4f}\n")
        
        # Example of Hyperparameter Tuning for Random Forest
        if isinstance(model, RandomForestClassifier):
            print("Tuning Random Forest Hyperparameters...")
            param_grid_rf = {
                'n_estimators': [200, 300, 400],
                'max_depth': [20, 30, 40],
                'min_samples_split': [2, 5, 10]
            }
            grid_search_rf = GridSearchCV(estimator=model, param_grid=param_grid_rf, cv=skf, scoring='f1_macro', n_jobs=-1)
            grid_search_rf.fit(X_train, y_train)

            print("Best parameters for Random Forest:", grid_search_rf.best_params_)
            print("Best score for Random Forest:", grid_search_rf.best_score_)
        
        # Example of Hyperparameter Tuning for XGBoost
        if isinstance(model, XGBClassifier):
            print("Tuning XGBoost Hyperparameters...")
            param_grid_xgb = {
                'learning_rate': [0.01, 0.1],
                'max_depth': [3, 6, 10],
                'n_estimators': [100, 300],
                'subsample': [0.7, 0.8, 1.0]
            }
            grid_search_xgb = GridSearchCV(estimator=model, param_grid=param_grid_xgb, cv=skf, scoring='f1_macro', n_jobs=-1)
            grid_search_xgb.fit(X_train, y_train)

            print("Best parameters for XGBoost:", grid_search_xgb.best_params_)
            print("Best score for XGBoost:", grid_search_xgb.best_score_)

# --------------------------------------------------------------
# 3. Plot Feature Importance (for Random Forest and XGBoost)
# --------------------------------------------------------------
def plot_feature_importance(models, features_list):
    """
    Plot feature importance for the Random Forest and XGBoost models.

    Args:
        models (dict): Trained models.
        features_list (list): List of feature names.

    Returns:
        None
    """
    rf_model = models.get('Random Forest')
    if rf_model:
        importance_rf = rf_model.feature_importances_
        plt.figure(figsize=(10, 6))
        sns.barplot(x=importance_rf, y=features_list)
        plt.title("Random Forest Feature Importance")
        plt.show()

    xgb_model = models.get('XGBoost')
    if xgb_model:
        importance_xgb = xgb_model.feature_importances_
        plt.figure(figsize=(10, 6))
        sns.barplot(x=importance_xgb, y=features_list)
        plt.title("XGBoost Feature Importance")
        plt.show()

# --------------------------------------------------------------
# Main Execution: Evaluate, Tune, and Plot Importance
# --------------------------------------------------------------
if __name__ == "__main__":
    # Load preprocessed DataFrame (or from saved CSV)
    df = pd.read_csv('SpanishLaliga_Eng.csv')  # Or another preprocessed CSV
    
    # Load pre-trained models from the 'models' folder
    models = {
        'Logistic Regression': joblib.load('models/Logistic_Regression.pkl'),
        'Random Forest': joblib.load('models/Random_Forest.pkl'),
        'XGBoost': joblib.load('models/XGBoost.pkl')
    }
    
    # Assume features and target have already been selected
    X = df.drop(columns=['Result_Numeric'])
    y = df['Result_Numeric']
    
    # Split data (adjust as needed)
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Evaluate each model
    for model_name, model in models.items():
        evaluate_model(model, X_test, y_test)

    # Perform cross-validation and hyperparameter tuning
    cross_validate_and_tune(models, X_train, y_train)
    
    # Plot feature importance (for tree-based models)
    plot_feature_importance(models, X.columns)
