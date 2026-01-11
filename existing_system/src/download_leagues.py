import os
import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup

# Dynamically get available leagues from both 'main' and 'extra' leagues
def get_league_codes():
    base_url = 'https://www.football-data.co.uk'
    main_countries = ['england', 'scotland', 'germany', 'italy', 'spain', 'france', 'netherlands', 'belgium', 'portugal', 'turkey', 'greece']
    extra_countries = ['argentina', 'austria', 'brazil', 'denmark', 'finland', 'ireland', 'mexico', 'norway', 'poland', 'russia', 'sweden']
    league_codes = {}

    # Fetch main leagues using {country}m.php
    for country in main_countries:
        country_url = f'{base_url}/{country}m.php'
        response = requests.get(country_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find leagues and their CSV files
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'mmz4281' in href and href.endswith('.csv'):
                league_code = href.split('/')[-1].replace('.csv', '').upper()
                league_name = a.text.strip()
                full_league_name = f"{country.capitalize()}_{league_name.replace(' ', '_')}"
                if full_league_name not in league_codes:
                    league_codes[full_league_name] = league_code

    # Fetch extra leagues using {country}.php
    for country in extra_countries:
        country_url = f'{base_url}/{country}.php'
        response = requests.get(country_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find leagues and their CSV files
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'mmz4281' in href and href.endswith('.csv'):
                league_code = href.split('/')[-1].replace('.csv', '').upper()
                league_name = a.text.strip()
                full_league_name = f"{country.capitalize()}_{league_name.replace(' ', '_')}"
                if full_league_name not in league_codes:
                    league_codes[full_league_name] = league_code

    return league_codes

# Columns to keep and rename
COLUMNS_TO_KEEP = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']
COLUMN_RENAMES = {
    'HomeTeam': 'Home Team',
    'AwayTeam': 'Away Team',
    'FTHG': 'HG',
    'FTAG': 'AG',
    'FTR': 'Result'
}

# Function to download and save the data
def download_league_data(season, league_code, league_name, save_dir):
    base_url = f"https://www.football-data.co.uk/mmz4281/{season}/{league_code}.csv"
    save_path = os.path.join(save_dir, f"{league_name}_{season}.csv")

    try:
        response = requests.get(base_url)
        response.raise_for_status()

        with open(save_path, 'wb') as f:
            f.write(response.content)
        print(f"Successfully downloaded {league_name} ({season}) data to {save_path}")

        return save_path  # Return saved path for concatenation

    except requests.exceptions.HTTPError as err:
        print(f"Failed to download {league_name} ({season}): {err}")
        return None

def process_and_concatenate_league_data(file_paths, league_name, final_save_dir):
    all_seasons = []
    
    # Check if final CSV for this league already exists
    final_save_path = os.path.join(final_save_dir, f"{league_name}_all_seasons.csv")
    if os.path.exists(final_save_path):
        existing_data = pd.read_csv(final_save_path)
    else:
        existing_data = pd.DataFrame()

    for file_path in file_paths:
        try:
            df = pd.read_csv(file_path)

            # Keep only relevant columns and rename them
            df = df[COLUMNS_TO_KEEP]
            df.rename(columns=COLUMN_RENAMES, inplace=True)

            # Concatenate new data with existing data if available
            all_seasons.append(df)

        except Exception as e:
            print(f"Error processing file {file_path}: {e}")

    # Concatenate all new DataFrames for the league
    if all_seasons:
        new_data = pd.concat(all_seasons, ignore_index=True)

        # Filter out duplicate matches (already present in the existing CSV)
        if not existing_data.empty:
            # Merge and filter out existing matches
            merged_data = pd.merge(new_data, existing_data[['Date', 'Home Team', 'Away Team']], 
                                   on=['Date', 'Home Team', 'Away Team'], how='left', indicator=True)
            new_data = merged_data[merged_data['_merge'] == 'left_only'].drop(columns=['_merge'])
            print(f"New matches found for {league_name}: {len(new_data)}")

        # Concatenate new data with existing data
        final_data = pd.concat([existing_data, new_data], ignore_index=True)

        # Save the final concatenated DataFrame to CSV
        final_data.to_csv(final_save_path, index=False)
        print(f"Updated CSV saved to {final_save_path}")

        # Delete individual season CSV files
        for file_path in file_paths:
            if os.path.exists(file_path):
                os.remove(file_path)  # Remove the file
                print(f"Deleted {file_path}")


def download_and_process_all_leagues(start_season, end_season, save_dir='/content/league_data', final_save_dir='/content/league_data/final'):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    if not os.path.exists(final_save_dir):
        os.makedirs(final_save_dir)

    # Fetch dynamic league codes from the website
    league_codes = get_league_codes()

    # Loop over each league and download data for the specified seasons
    for league_name, league_code in league_codes.items():
        file_paths = []
        
        # Download historical seasons
        for season in range(start_season, end_season):
            season_str = f"{str(season)[-2:]}{str(season + 1)[-2:]}"  # Format season as '2324'
            file_path = download_league_data(season_str, league_code, league_name, save_dir)
            if file_path:
                file_paths.append(file_path)

        # Handle current season
        current_season_str = f"{str(end_season)[-2:]}{str(end_season + 1)[-2:]}"
        file_path = download_league_data(current_season_str, league_code, league_name, save_dir)
        if file_path:
            file_paths.append(file_path)

        # Concatenate all season files for the league and delete individual season CSVs
        process_and_concatenate_league_data(file_paths, league_name, final_save_dir)

if __name__ == "__main__":
    current_year = datetime.now().year
    start_season = 2015  # Starting from 2015/2016 season
    end_season = current_year  # End at the current season (2024/2025)

    # Download, process, and concatenate data for all leagues from 2023 to the current season (2024/2025)
    download_and_process_all_leagues(start_season, end_season)
