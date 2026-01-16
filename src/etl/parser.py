"""
CSV Parser for football-data.co.uk files
"""
import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import hashlib
import re

logger = logging.getLogger(__name__)

class CSVParser:
    """Parse football-data.co.uk CSV files into structured data"""
    
    def __init__(self, config):
        # config is a dict with 'etl' key containing ETLConfig OBJECT
        self.config = config
        # Use OBJECT ATTRIBUTE access, not dict access
        self.schema_mapping = config['etl'].schema_mapping['csv_to_raw_mapping']
        self.odds_columns = config['etl'].schema_mapping.get('odds_columns', [])
    
    def parse_file(self, file_path: Path, league_name: str, season: str) -> Tuple[List[Dict], Dict]:
        """
        Parse a CSV file and extract matches and odds
        
        Returns:
            Tuple of (matches, odds_snapshots) where:
            - matches: List of match dictionaries
            - odds_snapshots: Dictionary of odds data by bookmaker
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return [], {}
        
        try:
            # Try multiple encodings
            for encoding in ['utf-8', 'latin-1', 'iso-8859-1']:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    logger.debug(f"Successfully read {file_path} with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue
            else:
                logger.error(f"Could not read {file_path} with any encoding")
                return [], {}
        
        except Exception as e:
            logger.error(f"Error reading CSV file {file_path}: {e}")
            return [], {}
        
        # Standardize column names
        df.columns = [col.strip() for col in df.columns]
        
        # Filter out rows with missing essential data
        required_cols = ['Date', 'HomeTeam', 'AwayTeam']
        df = df.dropna(subset=required_cols, how='any')
        
        if df.empty:
            logger.warning(f"No valid data in {file_path}")
            return [], {}
        
        matches = []
        all_odds_snapshots = {}
        all_odds = {}
        
        for idx, row in df.iterrows():
            try:
                # Parse match data
                match_data = self._parse_match_row(row, league_name, season)
                if match_data:
                    matches.append(match_data)
                # Collect odds snapshots
                if "odds_snapshots" in match_data:
                    all_odds_snapshots.update(match_data["odds_snapshots"])
                
                # Parse odds data
                odds_data = self._parse_odds_row(row, match_data['external_id'] if match_data else None)
                if odds_data:
                    all_odds.update(odds_data)
                    
            except Exception as e:
                logger.warning(f"Error parsing row {idx} in {file_path}: {e}")
                continue
        
        logger.info(f"Parsed {len(matches)} matches from {file_path}")
        return matches, {**all_odds_snapshots, **all_odds}
    
    def _parse_match_row(self, row: pd.Series, league_name: str, season: str) -> Optional[Dict]:
        """Parse a single row into match data"""
        try:
            # Parse date
            date_str = str(row.get('Date', '')).strip()
            if not date_str or date_str.lower() == 'nan':
                return None
            
            match_date = self._parse_date(date_str)
            if not match_date:
                return None
            
            # Get league config - use OBJECT attribute access
            etl_config = self.config['etl']  # This is ETLConfig object
            league_config = etl_config.leagues.get(league_name)  # Returns LeagueConfig object
            
            if not league_config:
                logger.error(f"League {league_name} not in config")
                return None
            
            # Clean team names
            home_team = self._clean_team_name(str(row.get('HomeTeam', '')).strip())
            away_team = self._clean_team_name(str(row.get('AwayTeam', '')).strip())
            
            if not home_team or not away_team:
                return None
            
            # Generate unique external ID
            match_key = f"{league_config.code}_{season}_{home_team}_{away_team}_{match_date}"
            external_id = hashlib.md5(match_key.encode()).hexdigest()
            
            # Parse goals
            home_goals = self._parse_int(row.get('FTHG'))
            away_goals = self._parse_int(row.get('FTAG'))
            
            # Parse result
            result = self._parse_result(row.get('FTR'))
            
            # Parse half-time data
            home_goals_ht = self._parse_int(row.get('HTHG'))
            away_goals_ht = self._parse_int(row.get('HTAG'))
            
            # Build match dictionary
            match_data = {
                'external_id': external_id,
                'source_system': 'football-data.co.uk',
                'league_external_code': league_config.code,  # OBJECT attribute
                'league_name': league_name,
                'season': season,
                'home_team_name': home_team,
                'away_team_name': away_team,
                'match_date': match_date,
                'home_goals': home_goals,
                'away_goals': away_goals,
                'result': result,
                'home_goals_ht': home_goals_ht,
                'away_goals_ht': away_goals_ht,
                'referee': str(row.get('Referee', '')).strip() or None,
                'attendance': self._parse_int(row.get('Attendance')),
                'matchday': self._parse_int(row.get('Matchday')),
                'available_at': datetime.now().isoformat(),
                'ingested_at': datetime.now().isoformat()
            }
            
            return match_data
            
        except Exception as e:
            logger.warning(f"Error parsing match row: {e}")
            return None
    
    # Rest of the methods remain the same...
    def _parse_odds_row(self, row: pd.Series, fixture_external_id: Optional[str]) -> Dict[str, List]:
        """Parse odds data from a row"""
        if not fixture_external_id:
            return {}
        
        odds_snapshots = {}
        
        # Bookmaker mapping
        bookmaker_codes = {
            'B365': 'Bet365', 'BW': 'BetWin', 'IW': 'Interwetten',
            'LB': 'Ladbrokes', 'PS': 'Pinnacle', 'SO': 'SportingOdds',
            'SB': 'Sportingbet', 'SJ': 'StanJames', 'SY': 'SkyBet',
            'VC': 'BetVictor', 'WH': 'WilliamHill'
        }
        
        for odds_prefix, bookmaker_name in bookmaker_codes.items():
            home_col = f"{odds_prefix}H"
            draw_col = f"{odds_prefix}D"
            away_col = f"{odds_prefix}A"
            
            home_odds = self._parse_float(row.get(home_col))
            draw_odds = self._parse_float(row.get(draw_col))
            away_odds = self._parse_float(row.get(away_col))
            
            if home_odds and draw_odds and away_odds:
                snapshot_key = f"{bookmaker_name}_1x2"
                
                odds_data = {
                    'fixture_external_id': fixture_external_id,
                    'bookmaker_name': bookmaker_name,
                    'market_type': '1x2',
                    'home_odds': home_odds,
                    'draw_odds': draw_odds,
                    'away_odds': away_odds,
                    'snapshot_at': datetime.now().isoformat(),
                    'is_closing_line': True,
                    'available_at': datetime.now().isoformat()
                }
                
                odds_snapshots[snapshot_key] = odds_data
        
        return odds_snapshots
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date from various formats"""
        try:
            formats = ['%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d', '%d.%m.%Y']
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.date().isoformat()
                except ValueError:
                    continue
            logger.warning(f"Could not parse date: {date_str}")
            return None
        except Exception:
            return None
    
    def _clean_team_name(self, team_name: str) -> str:
        """Clean and standardize team names"""
        if not team_name or team_name.lower() == 'nan':
            return ''
        
        team_name = re.sub(r'\s+', ' ', team_name.strip())
        
        replacements = {
            'Man Utd': 'Manchester United',
            'Man City': 'Manchester City',
            'Spurs': 'Tottenham Hotspur',
            'Sheff Utd': 'Sheffield United',
            'Sheff Wed': 'Sheffield Wednesday',
            'West Ham': 'West Ham United',
            'Newcastle': 'Newcastle United',
            'Wolves': 'Wolverhampton Wanderers',
            'Brighton': 'Brighton & Hove Albion',
            'Huddersfield': 'Huddersfield Town',
            'Leeds': 'Leeds United',
            'Leicester': 'Leicester City',
            'Norwich': 'Norwich City',
            'QPR': 'Queens Park Rangers',
        }
        
        return replacements.get(team_name, team_name)
    
    def _parse_int(self, value) -> Optional[int]:
        """Parse integer value"""
        try:
            if pd.isna(value):
                return None
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _parse_float(self, value) -> Optional[float]:
        """Parse float value"""
        try:
            if pd.isna(value):
                return None
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _parse_result(self, value) -> Optional[str]:
        """Parse result value (H, D, A)"""
        if pd.isna(value):
            return None
        
        result = str(value).strip().upper()
        if result in ['H', 'D', 'A']:
            return result
        
        return None
