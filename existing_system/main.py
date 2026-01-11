import os
import joblib
import argparse
import pandas as pd
from src.utils import load_config, setup_logger, save_model, save_models
from src.data_loader import preprocess_fixtures_data
from src.train_and_save_models import handle_sparse_data
from src.feature_engineering import generate_features
from src.train_and_save_models import train_models
from src.model_ensembling import create_stacking_ensemble, create_voting_ensemble
from src.evaluate_models import evaluate_model
from sklearn.model_selection import train_test_split
from imblearn.combine import SMOTETomek
from sklearn.preprocessing import StandardScaler
from src.download_leagues import download_and_process_all_leagues
from src.download_fixtures import download_and_save_data

# 1. Load configuration and set up logger
config = load_config('config.yaml')
logger = setup_logger(config)

# 2. Command-line argument parsing
parser = argparse.ArgumentParser(description="Train and evaluate football match outcome models.")
parser.add_argument('--single', help='Path to a single CSV file for a specific league', default=None)
parser.add_argument('--multiple', help='Use all CSV files in the data folder', action='store_true')
args = parser.parse_args()

# 3. Data Source Selection
data_source_type = config['data_source']['type']

if data_source_type == 'leagues':
    logger.info("Downloading historical data from football-data.co.uk")
    start_season = config['download_leagues']['start_season']
    end_season = config['download_leagues']['end_season']
    download_and_process_all_leagues(start_season, end_season)

elif data_source_type == 'fixtures':
    logger.info("Downloading future fixtures from football-data.org")

    # Download fixtures
    download_and_save_data(save_dir=config['paths']['fixtures_data'], historical=False)

    # Load and preprocess fixtures for prediction
    fixtures_folder = config['paths']['fixtures_data']
    df_fixtures = pd.DataFrame()

    # Prepare the team name mappings
    home_team_mapping = {}
    away_team_mapping = {}

    for league in config['football_data_org']['competitions']:
        fixtures_file = os.path.join(fixtures_folder, f"{league}_fixtures.csv")
        df_league_fixtures, league_home_team_mapping, league_away_team_mapping = preprocess_fixtures_data(pd.read_csv(fixtures_file))

        home_team_mapping.update(league_home_team_mapping)
        away_team_mapping.update(league_away_team_mapping)

        df_fixtures = pd.concat([df_fixtures, df_league_fixtures], ignore_index=True)

    df = df_fixtures

else:
    raise ValueError(f"Invalid data source type specified: {data_source_type}. Please update config.yaml.")

# 4. Save a copy of the original DataFrame before feature engineering
df_original = df.copy()

# 5. Feature Engineering
if 'Result' in df.columns and df['Result'].notna().all():
    # Apply feature engineering only for historical data (with results)
    df = generate_features(df, is_future=False)
else:
    # Future fixtures
    df = generate_features(df, is_future=True)
    logger.info("working with future fixtures iteratively generated.")

# Ensure date is numeric
if 'Date' in df.columns:
    df['days_since_reference'] = (df['Date'] - pd.Timestamp('1970-01-01')).dt.days

# 6. Encode categorical variables (already handled in preprocessing)
# Team mappings are returned from preprocessing and stored in home_team_mapping, away_team_mapping.

# 7. Target Encoding (if historical data has results)
if 'Result' in df.columns:
    df['Result_Numeric'] = df['Result'].map({'H': 0, 'D': 1, 'A': 2})
    logger.info("Encoded 'Result' into 'Result_Numeric'.")

# Separate historical and fixtures data
df_historical = df[df['Result'] != 'TBD']  # Historical data with results
df_fixtures = df[df['Result'] == 'TBD']    # Future fixtures

# 8. Train-Test Split for historical data
if not df_historical.empty:
    y = df_historical['Result_Numeric']
    X = df_historical.drop(columns=['HG', 'AG', 'Result', 'Result_Numeric'], errors='ignore')

    # 9. Train-Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=config['model_training']['train_test_split']['test_size'], random_state=config['project']['random_state'], stratify=y)
    X_test_unscaled = X_test.copy()

    # 10. Handle Sparse Data
    X_train, X_test = handle_sparse_data(X_train, X_test)

    # 11. Apply SMOTE with Tomek Links for Class Imbalance
    if config['model_training']['smote']:
        logger.info("Applying SMOTETomek for class imbalance...")
        smote_tomek = SMOTETomek(random_state=config['project']['random_state'])
        X_train, y_train = smote_tomek.fit_resample(X_train, y_train)

    # 12. Scale Features
    scaler = StandardScaler()
    if config['model_training']['scaling']:
        logger.info("Scaling features...")
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)

    # 13. Train Models
    models = train_models(X_train, y_train, config)
    save_models(models, config)

    # 14. Evaluate Models
    logger.info("Evaluating models...")
    for model_name in models:
        model_file = os.path.join(config['paths']['models_folder'], f"{model_name}.pkl")
        evaluate_model(model_file, X_test, y_test)

    # 15. Ensemble Voting/Stacking
    if config['model_ensembling']['type'] == 'voting':
        logger.info("Creating Voting Ensemble model...")
        ensemble_model = create_voting_ensemble(models, config['model_ensembling']['voting_type'])
    elif config['model_ensembling']['type'] == 'stacking':
        logger.info("Creating Stacking Ensemble model...")
        ensemble_model = create_stacking_ensemble(models)
    else:
        raise ValueError("Invalid ensemble type specified.")

    ensemble_model.fit(X_train, y_train)
    save_model(ensemble_model, os.path.join(config['paths']['models_folder'], 'ensemble_model.pkl'))

else:
    logger.warning("No historical data found to train models.")

    # Load pre-trained ensemble model if no historical data is available
    ensemble_model_path = os.path.join(config['paths']['models_folder'], 'ensemble_model.pkl')
    if os.path.exists(ensemble_model_path):
        logger.info("Loading pre-trained ensemble model for predictions...")
        ensemble_model = joblib.load(ensemble_model_path)
    else:
        raise ValueError("No pre-trained model found, and no historical data to train a new one.")

# 16. Generate Predictions for Fixtures
if not df_fixtures.empty:
    logger.info("Generating predictions for future fixtures...")

    for league in config['football_data_org']['competitions']:
        logger.info(f"Processing predictions for {league}")

        # Load the fixtures data for the current league
        fixtures_file = os.path.join(fixtures_folder, f"{league}_fixtures.csv")
        league_fixtures = pd.read_csv(fixtures_file)

        if league_fixtures.empty:
            logger.warning(f"No fixtures found for {league}, skipping...")
            continue

        # Ensure fixture dates are handled
        league_fixtures['Date'] = pd.to_datetime(league_fixtures['Date'], errors='coerce')

        # Generate fresh mappings from the specific league fixtures' categorical encoding
        league_fixtures['Home Team'] = league_fixtures['Home Team'].astype('category')
        league_fixtures['Away Team'] = league_fixtures['Away Team'].astype('category')
        home_team_mapping = dict(enumerate(league_fixtures['Home Team'].cat.categories))
        away_team_mapping = dict(enumerate(league_fixtures['Away Team'].cat.categories))

        # Apply mappings to decode team names in the fixture data
        league_fixtures['Home Team'] = league_fixtures['Home Team'].cat.codes.map(home_team_mapping)
        league_fixtures['Away Team'] = league_fixtures['Away Team'].cat.codes.map(away_team_mapping)

        # Log mappings and team values to verify correctness
        logger.info(f"Home Team Mapping Sample for {league}: {list(home_team_mapping.items())[:5]}")
        logger.info(f"Away Team Mapping Sample for {league}: {list(away_team_mapping.items())[:5]}")
        logger.info(f"Home Team values after mapping: {league_fixtures['Home Team'].head()}")

        # Prepare features by dropping unnecessary columns and scaling
        X_fixtures = league_fixtures.drop(columns=['Result'], errors='ignore')
        model_columns = ensemble_model.estimators_[0].n_features_in_
        X_fixtures = X_fixtures.reindex(columns=range(model_columns), fill_value=0)
        
        # Initialize scaler and transform the fixture data
        scaler = StandardScaler()
        X_fixtures_scaled = scaler.fit_transform(X_fixtures)

        # Perform predictions
        predictions = ensemble_model.predict(X_fixtures_scaled)
        probabilities = ensemble_model.predict_proba(X_fixtures_scaled)

        # Prepare output DataFrame with readable team names and prediction details
        df_readable = league_fixtures[['Date', 'Home Team', 'Away Team']].copy()
        df_readable['Predictions'] = pd.Series(predictions).map({0: 'Home Win', 1: 'Draw', 2: 'Away Win'})
        df_readable['Home_Win_Prob'] = probabilities[:, 0]
        df_readable['Draw_Prob'] = probabilities[:, 1]
        df_readable['Away_Win_Prob'] = probabilities[:, 2]

        # Save predictions for each league to CSV
        output_dir = config['paths']['predictions_output']
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f'predictions_{league}.csv')
        df_readable.to_csv(output_file, index=False)
        logger.info(f"Predictions saved to {output_file}")
else:
    logger.warning("No future fixtures found for predictions.")
