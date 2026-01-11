import joblib
from sklearn.ensemble import StackingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression

# --------------------------------------------------------------
# 1. Create Stacking Ensemble
# --------------------------------------------------------------
def create_stacking_ensemble(models, X_train, y_train):
    """
    Create and train a Stacking Classifier with base models.
    Args:
        models: Dictionary containing trained models.
        X_train, y_train: Training data and target.
    Returns:
        Trained StackingClassifier.
    """
    estimators = [
        ('lr', models['Logistic_Regression']),
        ('rf', models['Random_Forest']),
        ('xgb', models['XGBoost'])
    ]
    stacking_clf = StackingClassifier(estimators=estimators, final_estimator=LogisticRegression(), cv=5)
    print("\nTraining Stacking Ensemble model...")
    stacking_clf.fit(X_train, y_train)
    return stacking_clf

# --------------------------------------------------------------
# 2. Create Voting Ensemble
# --------------------------------------------------------------
def create_voting_ensemble(models, voting_type='soft'):
    """
    Create a Voting Classifier using the base models.
    Args:
        models: Dictionary containing trained models.
        voting_type (str): Voting type ('soft' or 'hard').
    Returns:
        VotingClassifier: Voting ensemble model.
    """
    estimators = [
        ('lr', models['Logistic_Regression']),
        ('rf', models['Random_Forest']),
        ('xgb', models['XGBoost'])
    ]
    voting_clf = VotingClassifier(estimators=estimators, voting=voting_type)
    return voting_clf

# --------------------------------------------------------------
# 3. Train and Evaluate Ensemble (Stacking or Voting)
# --------------------------------------------------------------
def train_and_evaluate_ensemble(ensemble_model, X_train, X_test, y_train, y_test):
    """
    Train and evaluate the ensemble model on test data.
    Args:
        ensemble_model (VotingClassifier or StackingClassifier): Ensemble model.
        X_train (pd.DataFrame): Training feature set.
        X_test (pd.DataFrame): Test feature set.
        y_train (pd.Series): Training target set.
        y_test (pd.Series): Test target set.
    """
    print("Fitting ensemble model...")
    ensemble_model.fit(X_train, y_train)
    print("\nEvaluating ensemble model...")
    evaluate_model(ensemble_model, X_test, y_test)

# --------------------------------------------------------------
# 4. Load Saved Models
# --------------------------------------------------------------
def load_models():
    """
    Load trained models from pickle files (Logistic Regression, Random Forest, XGBoost).
    Returns:
        dict: A dictionary of loaded models.
    """
    models = {
        'Logistic_Regression': joblib.load('models/Logistic_Regression.pkl'),
        'Random_Forest': joblib.load('models/Random_Forest.pkl'),
        'XGBoost': joblib.load('models/XGBoost.pkl')
    }
    return models

# --------------------------------------------------------------
# 5. Evaluate a Model
# --------------------------------------------------------------
def evaluate_model(model, X_test, y_test):
    """
    Evaluate a model using the test data.
    Args:
        model: The trained model to evaluate.
        X_test (pd.DataFrame): Test feature set.
        y_test (pd.Series): Test target set.
    """
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
    y_pred = model.predict(X_test)
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print("Classification Report:")
    print(classification_report(y_test, y_pred))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
