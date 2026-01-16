"""
ETL Pipeline Orchestrator
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Use this password (it matches your container)
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'betting_password')

logger = logging.getLogger(__name__)

class ETLPipeline:
    """Main ETL pipeline orchestrator"""
    
    def __init__(self):
        from .config import ConfigManager
        from .downloader import CSVDownloader
        from .parser import CSVParser
        from .loader import DatabaseLoader
        
        self.config = ConfigManager().config
        self.downloader = CSVDownloader(self.config)
        self.parser = CSVParser(self.config)
        self.loader = DatabaseLoader(self.config)
        
        logger.info("ETL Pipeline initialized")
    
    def run(self, 
            leagues: Optional[List[str]] = None, 
            seasons: Optional[List[str]] = None,
            test_mode: bool = False) -> Dict[str, Any]:
        """
        Run the complete ETL pipeline
        
        Args:
            leagues: List of league names to process (None = all)
            seasons: List of seasons to process (None = all)
            test_mode: If True, run in test mode with reduced data
        
        Returns:
            Dictionary with pipeline statistics
        """
        stats = {
            'start_time': datetime.now(),
            'end_time': None,
            'total_files': 0,
            'downloaded_files': 0,
            'processed_files': 0,
            'inserted_fixtures': 0,
            'inserted_teams': 0,
            'inserted_odds': 0,
            'skipped_files': 0,
            'failed_files': 0
        }
        
        try:
            logger.info(f"Starting ETL pipeline for leagues: {leagues}, seasons: {seasons}")
            
            # Step 1: Download data
            logger.info("Step 1: Downloading CSV files...")
            download_stats = self.downloader.download_all(leagues=leagues, seasons=seasons)
            
            # Update stats with download results
            stats['downloaded_files'] = download_stats.get('downloaded_files', 0)
            stats['failed_files'] += download_stats.get('failed_files', 0)
            stats['total_files'] = download_stats.get('total_files', 0)
            
            logger.info(f"Downloaded {stats['downloaded_files']}/{stats['total_files']} files")
            
            # If no files downloaded, return early
            if stats['downloaded_files'] == 0:
                logger.warning("No files were downloaded")
                stats['end_time'] = datetime.now()
                return stats
            
            # Step 2: Process each downloaded file
            logger.info("Step 2: Processing downloaded files...")
            
            # Get downloaded paths from download stats
            downloaded_paths = download_stats.get('downloaded_paths', [])
            
            for file_path_str in downloaded_paths:
                file_path = Path(file_path_str)
                try:
                    # Extract league and season from file path
                    # Path format: {raw_data_path}/{league}/{season}.csv
                    league_name = file_path.parent.name
                    season = file_path.stem  # Removes .csv extension
                    
                    logger.info(f"Processing {league_name} {season}")
                    
                    # Parse the file
                    matches, odds_snapshots = self.parser.parse_file(file_path, league_name, season)
                    
                    if not matches:
                        logger.warning(f"No matches found in {file_path}")
                        stats['skipped_files'] += 1
                        continue
                    
                    # Load data into database
                    if self.loader.connect():
                        # Load fixtures
                        fixtures_loaded = self.loader.load_fixtures(matches)
                        stats['inserted_fixtures'] += fixtures_loaded
                        
                        # Extract team names and load teams
                        team_names = []
                        for match in matches:
                            team_names.append(match.get('home_team_name'))
                            team_names.append(match.get('away_team_name'))
                        
                        teams_loaded = self.loader.load_teams(team_names)
                        stats['inserted_teams'] += teams_loaded
                        
                        # Load odds
                        if odds_snapshots:
                            odds_loaded = self.loader.load_odds(odds_snapshots)
                            stats['inserted_odds'] += odds_loaded
                        
                        self.loader.disconnect()
                    
                    stats['processed_files'] += 1
                    logger.info(f"Processed {league_name} {season}: {len(matches)} matches")
                    
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    stats['failed_files'] += 1
                    continue
            
            logger.info(f"ETL completed: {stats['processed_files']} files processed")
            
        except Exception as e:
            logger.error(f"ETL pipeline failed: {e}", exc_info=True)
            stats['failed_files'] += 1
        
        finally:
            # Always set end time
            stats['end_time'] = datetime.now()
            
            # Calculate duration if both times are set
            if stats['start_time'] and stats['end_time']:
                stats['duration_seconds'] = (stats['end_time'] - stats['start_time']).total_seconds()
                logger.info(f"ETL duration: {stats['duration_seconds']:.2f} seconds")
        
        return stats
    
    def validate_data_quality(self, leagues: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Validate data quality after ETL
        """
        validation_results = {
            'total_fixtures': 0,
            'fixtures_with_odds': 0,
            'fixtures_without_odds': 0,
            'completed_fixtures': 0,
            'future_fixtures': 0
        }
        
        try:
            if self.loader.connect():
                cursor = self.loader.connection.cursor()
                
                # Count total fixtures
                query = "SELECT COUNT(*) FROM raw.fixtures"
                if leagues:
                    league_codes = [self.config['etl'].leagues[l].code for l in leagues if l in self.config['etl'].leagues]
                    if league_codes:
                        placeholders = ','.join(['%s'] * len(league_codes))
                        query += f" WHERE league_external_code IN ({placeholders})"
                        cursor.execute(query, league_codes)
                    else:
                        cursor.execute(query)
                else:
                    cursor.execute(query)
                
                validation_results['total_fixtures'] = cursor.fetchone()[0]
                
                # Count fixtures with odds
                query = """
                SELECT COUNT(DISTINCT f.external_id)
                FROM raw.fixtures f
                JOIN raw.odds_snapshots o ON f.external_id = o.fixture_external_id
                """
                if leagues and league_codes:
                    placeholders = ','.join(['%s'] * len(league_codes))
                    query += f" WHERE f.league_external_code IN ({placeholders})"
                    cursor.execute(query, league_codes)
                else:
                    cursor.execute(query)
                
                validation_results['fixtures_with_odds'] = cursor.fetchone()[0]
                validation_results['fixtures_without_odds'] = (
                    validation_results['total_fixtures'] - validation_results['fixtures_with_odds']
                )
                
                cursor.close()
                self.loader.disconnect()
        
        except Exception as e:
            logger.error(f"Data quality validation failed: {e}")
        
        return validation_results
