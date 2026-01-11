# src/pipeline/odds_collector_v2.py
"""
Odds Collector for API-Football (Bet365)
Standardized on API-Football's numeric fixture_id
"""

import os
import sys
import requests
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta
import time
import logging
from typing import Optional, Dict, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "https://v3.football.api-sports.io"
BOOKMAKER_ID = 8  # Bet365 in API-Football
MARKET_TYPE = "1x2"

class OddsCollector:
    def __init__(self, api_key: str, db_config: Dict):
        """
        Initialize Odds Collector
        
        Args:
            api_key: API-Football API key
            db_config: PostgreSQL connection parameters
        """
        self.api_key = api_key
        self.headers = {"x-apisports-key": self.api_key}
        self.db_config = db_config
        self.conn = None
        self.cursor = None
        
    def connect_db(self) -> bool:
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.cursor = self.conn.cursor()
            logger.info("Connected to PostgreSQL on port 5433")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def close_db(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def fetch_fixture_odds(self, fixture_id: int) -> Optional[Dict]:
        """
        Fetch odds for a specific fixture from API-Football
        
        Args:
            fixture_id: API-Football fixture ID
            
        Returns:
            Dictionary with odds data or None if failed
        """
        endpoint = f"{API_BASE_URL}/odds"
        params = {
            "fixture": fixture_id,
            "bookmaker": BOOKMAKER_ID
        }
        
        try:
            logger.info(f"Fetching odds for fixture {fixture_id}")
            response = requests.get(
                endpoint,
                params=params,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check API response
                if data.get("errors"):
                    logger.error(f"API error: {data['errors']}")
                    return None
                
                if data.get("response"):
                    return data["response"]
                else:
                    logger.warning(f"No odds data for fixture {fixture_id}")
                    return None
                    
            elif response.status_code == 429:
                logger.warning("Rate limit reached. Sleeping for 60 seconds.")
                time.sleep(60)
                return self.fetch_fixture_odds(fixture_id)
                
            else:
                logger.error(f"HTTP {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def parse_bet365_odds(self, odds_data: List) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Parse Bet365 1X2 odds from API response
        
        Args:
            odds_data: API response data for a fixture
            
        Returns:
            Tuple of (home_odds, draw_odds, away_odds)
        """
        if not odds_data:
            return None, None, None
        
        try:
            # API-Football returns list of bookmakers
            for bookmaker in odds_data:
                if bookmaker.get("bookmaker", {}).get("id") == BOOKMAKER_ID:
                    for bet in bookmaker.get("bets", []):
                        if bet.get("name", "").lower() == MARKET_TYPE:
                            home_odds = draw_odds = away_odds = None
                            
                            for value in bet.get("values", []):
                                if value["value"] == "Home":
                                    home_odds = float(value["odd"])
                                elif value["value"] == "Draw":
                                    draw_odds = float(value["odd"])
                                elif value["value"] == "Away":
                                    away_odds = float(value["odd"])
                            
                            return home_odds, draw_odds, away_odds
            
            logger.warning("Bet365 1X2 market not found in response")
            return None, None, None
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing odds: {e}")
            return None, None, None
    
    def validate_odds(self, home: float, draw: float, away: float) -> bool:
        """
        Validate odds are within reasonable ranges
        
        Args:
            home: Home win odds
            draw: Draw odds
            away: Away win odds
            
        Returns:
            True if odds are valid
        """
        if not all([home, draw, away]):
            return False
        
        # Check decimal odds range
        if not (1.01 <= home <= 1000.0):
            logger.warning(f"Home odds {home} out of range")
            return False
        if not (1.01 <= draw <= 1000.0):
            logger.warning(f"Draw odds {draw} out of range")
            return False
        if not (1.01 <= away <= 1000.0):
            logger.warning(f"Away odds {away} out of range")
            return False
        
        # Check for arbitrage (optional)
        implied_prob = (1/home + 1/draw + 1/away)
        if implied_prob < 0.95 or implied_prob > 1.05:
            logger.warning(f"Suspicious implied probability: {implied_prob:.3f}")
        
        return True
    
    def store_odds_snapshot(self, fixture_id: int, home_odds: float, 
                           draw_odds: float, away_odds: float) -> bool:
        """
        Store odds snapshot in PostgreSQL
        
        Args:
            fixture_id: API-Football fixture ID
            home_odds: Home win odds
            draw_odds: Draw odds
            away_odds: Away win odds
            
        Returns:
            True if successful
        """
        if not self.validate_odds(home_odds, draw_odds, away_odds):
            return False
        
        try:
            insert_query = """
            INSERT INTO odds_snapshots 
            (fixture_id, bookmaker_id, market_type, home_odds, draw_odds, away_odds, snapshot_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (fixture_id, bookmaker_id, snapshot_at) 
            DO UPDATE SET 
                home_odds = EXCLUDED.home_odds,
                draw_odds = EXCLUDED.draw_odds,
                away_odds = EXCLUDED.away_odds,
                updated_at = CURRENT_TIMESTAMP
            """
            
            self.cursor.execute(insert_query, (
                fixture_id,
                BOOKMAKER_ID,
                MARKET_TYPE,
                home_odds,
                draw_odds,
                away_odds,
                datetime.now()
            ))
            
            self.conn.commit()
            logger.info(f"Stored odds for fixture {fixture_id}: H={home_odds}, D={draw_odds}, A={away_odds}")
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to store odds for fixture {fixture_id}: {e}")
            return False
    
    def process_fixture(self, fixture_id: int) -> bool:
        """
        Complete pipeline for a single fixture
        
        Args:
            fixture_id: API-Football fixture ID
            
        Returns:
            True if odds were successfully stored
        """
        odds_data = self.fetch_fixture_odds(fixture_id)
        if not odds_data:
            return False
        
        home_odds, draw_odds, away_odds = self.parse_bet365_odds(odds_data)
        if not all([home_odds, draw_odds, away_odds]):
            return False
        
        return self.store_odds_snapshot(fixture_id, home_odds, draw_odds, away_odds)
    
    def collect_odds_for_fixtures(self, fixture_ids: List[int], 
                                  batch_size: int = 10) -> Dict[str, int]:
        """
        Collect odds for multiple fixtures with rate limiting
        
        Args:
            fixture_ids: List of API-Football fixture IDs
            batch_size: Number of requests before sleep
            
        Returns:
            Statistics dict
        """
        stats = {
            "total": len(fixture_ids),
            "success": 0,
            "failed": 0,
            "skipped": 0
        }
        
        if not self.connect_db():
            return stats
        
        try:
            for i, fixture_id in enumerate(fixture_ids, 1):
                logger.info(f"Processing fixture {fixture_id} ({i}/{len(fixture_ids)})")
                
                # Check if odds already exist (within last 24 hours)
                check_query = """
                SELECT COUNT(*) FROM odds_snapshots 
                WHERE fixture_id = %s 
                AND bookmaker_id = %s 
                AND snapshot_at > NOW() - INTERVAL '24 hours'
                """
                self.cursor.execute(check_query, (fixture_id, BOOKMAKER_ID))
                if self.cursor.fetchone()[0] > 0:
                    logger.info(f"Odds for fixture {fixture_id} already exist (recent)")
                    stats["skipped"] += 1
                    continue
                
                # Process fixture
                if self.process_fixture(fixture_id):
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
                
                # Rate limiting (API-Football free tier: ~10 req/minute)
                if i % batch_size == 0 and i < len(fixture_ids):
                    logger.info(f"Batch completed. Sleeping for 60 seconds...")
                    time.sleep(60)
                    
        except Exception as e:
            logger.error(f"Error processing fixtures: {e}")
            
        finally:
            self.close_db()
        
        return stats
    
    def get_fixtures_without_odds(self, days_back: int = 7, 
                                  limit: int = 100) -> List[int]:
        """
        Get fixture IDs that don't have recent odds
        
        Args:
            days_back: Look for fixtures from last N days
            limit: Maximum number of fixtures to return
            
        Returns:
            List of fixture IDs
        """
        if not self.connect_db():
            return []
        
        try:
            query = """
            SELECT DISTINCT f.api_football_id 
            FROM fixtures f
            LEFT JOIN odds_snapshots o ON f.api_football_id = o.fixture_id 
                AND o.bookmaker_id = %s 
                AND o.snapshot_at > NOW() - INTERVAL '24 hours'
            WHERE f.api_football_id IS NOT NULL 
              AND f.match_date >= NOW() - INTERVAL '%s days'
              AND o.fixture_id IS NULL
            ORDER BY f.match_date DESC
            LIMIT %s
            """
            
            self.cursor.execute(query, (BOOKMAKER_ID, days_back, limit))
            results = self.cursor.fetchall()
            
            return [row[0] for row in results if row[0]]
            
        except Exception as e:
            logger.error(f"Error fetching fixtures without odds: {e}")
            return []
            
        finally:
            self.close_db()


def main():
    """Main execution function"""
    # Configuration
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        logger.error("API_FOOTBALL_KEY environment variable not set")
        sys.exit(1)
    
    db_config = {
        "host": "localhost",
        "port": 5433,
        "database": "football_betting",
        "user": "betting_user",
        "password": os.environ.get("DB_PASSWORD", "betting_password")
    }
    
    # Initialize collector
    collector = OddsCollector(api_key, db_config)
    
    # Get fixtures without odds
    logger.info("Finding fixtures without recent odds...")
    fixture_ids = collector.get_fixtures_without_odds(days_back=30, limit=50)
    
    if not fixture_ids:
        logger.info("No fixtures found without odds in the last 30 days.")
        return
    
    logger.info(f"Found {len(fixture_ids)} fixtures without odds. Collecting...")
    
    # Collect odds
    stats = collector.collect_odds_for_fixtures(fixture_ids, batch_size=10)
    
    # Report statistics
    logger.info("\n" + "="*50)
    logger.info("ODDS COLLECTION COMPLETE")
    logger.info("="*50)
    logger.info(f"Total fixtures: {stats['total']}")
    logger.info(f"Successfully collected: {stats['success']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Skipped (already exist): {stats['skipped']}")
    logger.info("="*50)


if __name__ == "__main__":
    main()