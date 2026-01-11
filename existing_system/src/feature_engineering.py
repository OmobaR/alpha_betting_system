import pandas as pd
import logging

# Set up logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

n = 3  # Number of previous matches to consider for rolling statistics

def calculate_wins_losses(row):
    """Calculate win/loss from 'Result'."""
    if row['Result'] == 'H':  # Home win
        return 1, 0
    elif row['Result'] == 'A':  # Away win
        return 0, 1
    else:  # Draw
        return 0, 0

def get_form_points(result):
    """Calculate form points based on match results: W=3, D=1, L=0."""
    if result == 'W':
        return 3
    elif result == 'D':
        return 1
    else:
        return 0

def calculate_streaks(df, team_col, result_col):
    """Calculate winning/losing streaks for a team."""
    streak = []
    current_streak = 0
    for result in df[result_col]:
        if result == 'W':
            current_streak += 1
        elif result == 'L':
            current_streak = -1 if current_streak >= 0 else current_streak - 1
        else:
            current_streak = 0
        streak.append(current_streak)
    return pd.Series(streak)

def apply_feature_engineering(df):
    """
    Apply feature engineering to the dataset, handling both single-league and multi-league cases.
    """
    group_columns = ['Home Team', 'Away Team']
    if 'League' in df.columns:
        group_columns = ['League', 'Home Team', 'Away Team']  # Adjust grouping for leagues

    # Sort by Season and Date to ensure chronological order
    if 'Season' in df.columns and 'Date' in df.columns:
        df = df.sort_values(by=['Season', 'Date'])
        df['matchday'] = df.groupby('Season').cumcount() + 1
    else:
        df = df.sort_values(by=['Date'])
        df['matchday'] = range(1, len(df) + 1)

    # Apply only if 'Result', 'HG', 'AG' columns exist
    if 'Result' in df.columns and 'HG' in df.columns and 'AG' in df.columns:
        df['home_win'], df['away_loss'] = zip(*df.apply(calculate_wins_losses, axis=1))
        df['away_win'], df['home_loss'] = zip(*df.apply(lambda row: calculate_wins_losses(
            {'Result': 'A' if row['Result'] == 'A' else 'H'}) if row['Result'] != 'D' else (0, 0), axis=1))

        # Rolling window for Home Team stats
        df['HW'] = df.groupby(group_columns[:-1])['home_win'].rolling(n, min_periods=1).sum().reset_index(0, drop=True)
        df['HL'] = df.groupby(group_columns[:-1])['home_loss'].rolling(n, min_periods=1).sum().reset_index(0, drop=True)
        df['HGF'] = df.groupby(group_columns[:-1])['HG'].rolling(n, min_periods=1).sum().reset_index(0, drop=True)
        df['HGA'] = df.groupby(group_columns[:-1])['AG'].rolling(n, min_periods=1).sum().reset_index(0, drop=True)
        df['HWGD'] = df['HGF'] - df['HGA']
        df['HLGD'] = df['HGA'] - df['HGF']

        # Rolling window for Away Team stats
        df['AW'] = df.groupby(group_columns[1:])['away_win'].rolling(n, min_periods=1).sum().reset_index(0, drop=True)
        df['AL'] = df.groupby(group_columns[1:])['away_loss'].rolling(n, min_periods=1).sum().reset_index(0, drop=True)
        df['AGF'] = df.groupby(group_columns[1:])['AG'].rolling(n, min_periods=1).sum().reset_index(0, drop=True)
        df['AGA'] = df.groupby(group_columns[1:])['HG'].rolling(n, min_periods=1).sum().reset_index(0, drop=True)
        df['AWGD'] = df['AGF'] - df['AGA']
        df['ALGD'] = df['AGA'] - df['AGF']

        # Rolling average goals
        df['home_rolling_goals'] = df.groupby(group_columns[:-1])['HG'].rolling(5, min_periods=1).mean().reset_index(0, drop=True)
        df['away_rolling_goals'] = df.groupby(group_columns[1:])['AG'].rolling(5, min_periods=1).mean().reset_index(0, drop=True)

        # Historical Form Points Features
        df['HM1_points'] = df.groupby(group_columns[:-1])['Result'].shift(1).fillna('D').apply(get_form_points)
        df['HM2_points'] = df.groupby(group_columns[:-1])['Result'].shift(2).fillna('D').apply(get_form_points)
        df['HM3_points'] = df.groupby(group_columns[:-1])['Result'].shift(3).fillna('D').apply(get_form_points)

        df['AM1_points'] = df.groupby(group_columns[1:])['Result'].shift(1).fillna('D').apply(get_form_points)
        df['AM2_points'] = df.groupby(group_columns[1:])['Result'].shift(2).fillna('D').apply(get_form_points)
        df['AM3_points'] = df.groupby(group_columns[1:])['Result'].shift(3).fillna('D').apply(get_form_points)

        # Win percentages
        df['HW%'] = df['HW'] / (df['HW'] + df['HL'])
        df['HL%'] = df['HL'] / (df['HW'] + df['HL'])
        df['AW%'] = df['AW'] / (df['AW'] + df['AL'])
        df['AL%'] = df['AL'] / (df['AW'] + df['AL'])

        # Streaks
        df['Home_Streak'] = df.groupby(group_columns[:-1])['Result'].apply(lambda x: calculate_streaks(df, 'Home Team', 'Result')).reset_index(drop=True)
        df['Away_Streak'] = df.groupby(group_columns[1:])['Result'].apply(lambda x: calculate_streaks(df, 'Away Team', 'Result')).reset_index(drop=True)

        # Contextual Factors
        df['Matchday_Importance'] = df['matchday'].apply(lambda x: 1 if x >= 35 else 0)

        # Short-term and long-term form
        df['HGF_3'] = df.groupby(group_columns[:-1])['HG'].rolling(3, min_periods=1).sum().reset_index(0, drop=True)
        df['HGF_10'] = df.groupby(group_columns[:-1])['HG'].rolling(10, min_periods=1).sum().reset_index(0, drop=True)
        df['AGF_3'] = df.groupby(group_columns[1:])['AG'].rolling(3, min_periods=1).sum().reset_index(0, drop=True)
        df['AGF_10'] = df.groupby(group_columns[1:])['AG'].rolling(10, min_periods=1).sum().reset_index(0, drop=True)
    else:
        logger.info("Skipping goal-based features since future fixtures do not have goal data.")
    
    return df

def calculate_elo_ratings(df, k=20, home_advantage=100):
    """
    Adjust SPI-like (Elo) ratings dynamically based on match results.
    
    Args:
        df (pd.DataFrame): Input DataFrame.
        k (int): K-factor for Elo rating adjustment.
        home_advantage (int): Points added to the home team rating to account for home-field advantage.
    """
    if 'HG' not in df.columns or 'AG' not in df.columns:
        logger.warning("Skipping Elo rating calculation because 'HG' or 'AG' columns are missing.")
        return df

    teams = pd.concat([df['Home Team'], df['Away Team']]).unique()
    ratings = {team: {'offensive': 1500, 'defensive': 1500} for team in teams}

    def update_ratings(home_off, home_def, away_off, away_def, home_goals, away_goals, k, home_advantage):
        expected_home_goals = (home_off / (away_def + home_advantage)) * 1.5
        expected_away_goals = (away_off / home_def) * 1.5

        new_home_off = home_off + k * (home_goals - expected_home_goals)
        new_away_off = away_off + k * (away_goals - expected_away_goals)

        new_home_def = home_def + k * (expected_away_goals - away_goals)
        new_away_def = away_def + k * (expected_home_goals - home_goals)

        return new_home_off, new_home_def, new_away_off, new_away_def

    for index, row in df.iterrows():
        home_team = row['Home Team']
        away_team = row['Away Team']
        home_goals = row['HG']
        away_goals = row['AG']

        home_off = ratings[home_team]['offensive']
        home_def = ratings[home_team]['defensive']
        away_off = ratings[away_team]['offensive']
        away_def = ratings[away_team]['defensive']

        new_home_off, new_home_def, new_away_off, new_away_def = update_ratings(
            home_off, home_def, away_off, away_def, home_goals, away_goals, k, home_advantage
        )

        ratings[home_team]['offensive'], ratings[home_team]['defensive'] = new_home_off, new_home_def
        ratings[away_team]['offensive'], ratings[away_team]['defensive'] = new_away_off, new_away_def

        df.loc[index, 'Home_Offensive_Elo'] = new_home_off
        df.loc[index, 'Home_Defensive_Elo'] = new_home_def
        df.loc[index, 'Away_Offensive_Elo'] = new_away_off
        df.loc[index, 'Away_Defensive_Elo'] = new_away_def

    return df


def generate_features(df, is_future=False):
    """
    Generate features for both historical and future fixtures.
    
    Args:
        df (pd.DataFrame): Input DataFrame with match data.
        is_future (bool): If True, the data is for future fixtures without goal data.
    
    Returns:
        pd.DataFrame: DataFrame with engineered features.
    """
    # Handle sparse data - Convert to dense if any columns are sparse
    if any(pd.api.types.is_sparse(dtype) for dtype in df.dtypes):
        df = df.sparse.to_dense()
        logger.info("Converted sparse DataFrame to dense format.")

    if is_future:
        logger.info("Skipping goal-based feature engineering for future fixtures...")
        # Future fixtures: skip goal-based features and Elo calculations
        df = apply_feature_engineering(df)
    else:
        logger.info("Applying goal-based feature engineering for historical data...")
        # Historical data: includes goals, apply full feature engineering and Elo ratings
        df = apply_feature_engineering(df)
        df = calculate_elo_ratings(df)

    return df


