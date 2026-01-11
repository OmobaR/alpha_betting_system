# src/download_fixtures.py
import os
import requests
import pandas as pd
from datetime import datetime
from src.utils import load_config
import time

# API Configuration
BASE_URL = "https://api.football-data.org/v4"
API_KEY = None
HEADERS = None
COMPETITIONS = []

def set_api_config(api_key, competitions):
    global API_KEY, HEADERS, COMPETITIONS
    API_KEY = api_key
    HEADERS = {"X-Auth-Token": API_KEY}
    COMPETITIONS = competitions

def process_matches(matches, historical):
    data = []
    for match in matches:
        if not historical and match['status'] != 'FINISHED':
            data.append({
                'Date': match['utcDate'],
                'Home Team': match['homeTeam']['name'],
                'Away Team': match['awayTeam']['name'],
                'Home Goals': None,
                'Away Goals': None,
                'Result': 'TBD'
            })
        elif historical and match['status'] == 'FINISHED':
            # Corrected to extract 'home' and 'away' for full-time score
            home_goals = match['score'].get('fullTime', {}).get('home', None)
            away_goals = match['score'].get('fullTime', {}).get('away', None)

            data.append({
                'Date': match['utcDate'],
                'Home Team': match['homeTeam']['name'],
                'Away Team': match['awayTeam']['name'],
                'Home Goals': home_goals,
                'Away Goals': away_goals,
                'Result': match['score']['winner']  # 'HOME_TEAM', 'AWAY_TEAM', or 'DRAW'
            })

    df = pd.DataFrame(data)
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    return df



def get_fixtures_or_historical(league_code, historical=False, start_date=None, end_date=None):
    url = f"{BASE_URL}/competitions/{league_code}/matches"
    params = {"dateFrom": start_date, "dateTo": end_date} if historical else {}

    response = requests.get(url, headers=HEADERS, params=params)
    print(f"API Response Status for {league_code}: {response.status_code}")

    if response.status_code == 200:
        matches = response.json().get('matches', [])
        print(f"Number of matches fetched for {league_code}: {len(matches)}")
        return process_matches(matches, historical)
    else:
        print(f"Error fetching data for {league_code}: {response.status_code}, {response.text}")
        return pd.DataFrame()

def download_and_save_data(save_dir, historical=False, start_season=None, end_season=None):
    """
    Download either historical data or upcoming fixtures for all specified competitions and save to CSV.
    
    Args:
        save_dir (str): Directory to save the CSV files.
        historical (bool): Set to True to download historical data, False for future fixtures.
        start_season (int): Start season year (e.g., 2023).
        end_season (int): End season year (e.g., 2024).
    """
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # Calculate start and end dates based on seasons
    if start_season and end_season:
        start_date = f"{start_season}-08-01"  # Start of season
        end_date = f"{end_season}-07-31"      # End of season

    for league_code in COMPETITIONS:
        if historical:
            df = get_fixtures_or_historical(league_code, historical=True, start_date=start_date, end_date=end_date)
            file_type = "historical"
        else:
            df = get_fixtures_or_historical(league_code, historical=False)
            file_type = "fixtures"

        if not df.empty:
            file_name = f"{league_code}_{file_type}.csv"
            save_path = os.path.join(save_dir, file_name)
            df.to_csv(save_path, index=False)
            print(f"{file_type.capitalize()} data saved to {save_path}")
        else:
            print(f"No {file_type} data found for {league_code}")

if __name__ == "__main__":
    # Load configuration
    config = load_config('config.yaml')

    # Set API configuration from config.yaml
    api_key = config['football_data_org']['api_key']
    competitions = config['football_data_org']['competitions']
    set_api_config(api_key, competitions)

    # Directories
    save_directory = config['paths']['fixtures_data']

    # Download future fixtures
    download_and_save_data(save_dir=save_directory, historical=False)

    # Optionally download historical data (with seasonal structure)
    start_season = config['fixtures_seasonal']['start_season']
    end_season = config['fixtures_seasonal']['end_season']
    download_and_save_data(save_dir=save_directory, historical=True, start_season=start_season, end_season=end_season)
