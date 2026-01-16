"""
CSV Downloader for football-data.co.uk
"""
import requests
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
from tenacity import retry, stop_after_attempt, wait_exponential   
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class CSVDownloader:
    """Download CSV files from football-data.co.uk to HDD"""

    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def download_season(self, league_name: str, season: str) -> Optional[Path]:
        """
        Download a single season for a league
        
        Args:
            league_name: Name of the league (EPL, LaLiga, etc.)
            season: Season string (e.g., '2023-24')
        
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Get league config
            etl_config = self.config['etl']
            league_config = etl_config.leagues.get(league_name)
            
            if not league_config:
                logger.error(f"League {league_name} not found in config")
                return None
            
            # Create directory if it doesn't exist
            league_dir = etl_config.raw_data_path / league_name
            league_dir.mkdir(parents=True, exist_ok=True)
            
            # Build download URL
            url = etl_config.get_league_url(league_config.code, season)
            
            # Download file
            logger.info(f"Downloading {league_name} {season} from {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Save file
            file_path = league_dir / f"{season}.csv"
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded {file_path} ({len(response.content)} bytes)")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to download {league_name} {season}: {e}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def download_with_retry(self, league_name: str, season: str) -> Optional[Path]:
        """Download with retry logic"""
        return self.download_season(league_name, season)

    def download_all(self, leagues: Optional[List[str]] = None, seasons: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Download multiple leagues and seasons
        
        Args:
            leagues: List of league names to download (if None, download all)
            seasons: List of seasons to download (if None, use all from config)
        
        Returns:
            Dictionary with download statistics
        """
        stats = {
            'total_files': 0,
            'downloaded_files': 0,
            'failed_files': 0,
            'downloaded_paths': []
        }
        
        try:
            # Get ETL config
            etl_config = self.config['etl']
            
            # Use all leagues if not specified
            if leagues is None:
                leagues = list(etl_config.leagues.keys())
            
            # Use all seasons if not specified
            if seasons is None:
                seasons = etl_config.seasons
            
            logger.info(f"Starting download for {len(leagues)} leagues and {len(seasons)} seasons")
            
            # Download each league and season
            for league_name in leagues:
                logger.info(f"Downloading {league_name}...")
                
                for season in seasons:
                    stats['total_files'] += 1
                    
                    file_path = self.download_with_retry(league_name, season)
                    
                    if file_path and file_path.exists():
                        stats['downloaded_files'] += 1
                        stats['downloaded_paths'].append(str(file_path))
                        logger.debug(f"Successfully downloaded {league_name} {season}")
                    else:
                        stats['failed_files'] += 1
                        logger.warning(f"Failed to download {league_name} {season}")
            
            logger.info(f"Download completed: {stats['downloaded_files']}/{stats['total_files']} files downloaded")
            return stats
            
        except Exception as e:
            logger.error(f"Error in download_all: {e}")
            return stats
