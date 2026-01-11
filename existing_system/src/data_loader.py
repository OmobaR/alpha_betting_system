import os
import pandas as pd

def preprocess_fixtures_data(df):
    """
    Preprocess the fixtures data to align it with the model requirements.
    
    Args:
        df (pd.DataFrame): DataFrame containing the fixtures data.
    
    Returns:
        pd.DataFrame: Processed DataFrame ready for feature engineering and predictions.
    """
    # Ensure 'Date' is in the correct format
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

    # Drop rows with invalid dates (e.g., NaT)
    df = df.dropna(subset=['Date'])

    # Extract year, month, and day if needed
    df['year'] = df['Date'].dt.year
    df['month'] = df['Date'].dt.month
    df['day'] = df['Date'].dt.day

    # Encode 'Home Team' and 'Away Team' as categorical codes
    home_team_mapping = dict(enumerate(df['Home Team'].astype('category').cat.categories))
    away_team_mapping = dict(enumerate(df['Away Team'].astype('category').cat.categories))
    df['Home Team'] = df['Home Team'].astype('category').cat.codes
    df['Away Team'] = df['Away Team'].astype('category').cat.codes
    
    # Add additional preprocessing steps if necessary
    # For example, handle missing values or standardize column names

    return df, home_team_mapping, away_team_mapping  # Return mappings

def load_and_preprocess_data(file_path):
    """
    Load a CSV file and preprocess it by converting date formats and selecting relevant columns.
    
    Args:
        file_path (str): Path to the CSV file.
        
    Returns:
        pd.DataFrame: Preprocessed DataFrame.
    """
    # Load the dataset
    data = pd.read_csv(file_path)
    
    # Convert 'Date' to proper datetime format
    data['Date'] = pd.to_datetime(data['Date'], format='%d/%m/%Y')

    # Select relevant columns for analysis
    columns = ['Date', 'Season', 'Home Team', 'Away Team', 'HG', 'AG', 'Result']
    df = data[columns]

    return df


def load_all_leagues(data_folder):
    """
    Load CSV files from a folder, preprocess each one, combine them into a single DataFrame,
    and add a 'League' column to differentiate datasets.
    
    Args:
        data_folder (str): Path to the folder containing the CSV files.
        
    Returns:
        pd.DataFrame: Combined DataFrame with a 'League' column for each dataset.
    """
    all_files = [f for f in os.listdir(data_folder) if f.endswith('.csv')]
    df_list = []
    
    for file_name in all_files:
        # Load and preprocess each CSV
        df = load_and_preprocess_data(os.path.join(data_folder, file_name))
        league_name = file_name.replace('.csv', '')  # Extract league name from filename
        df['League'] = league_name  # Add a new column for league
        df_list.append(df)
    
    # Combine all DataFrames into one
    combined_df = pd.concat(df_list, ignore_index=True)
    return combined_df

# Example Usage
# data_folder = '../data/'
# combined_df = load_all_leagues(data_folder)
# print(combined_df.head())
