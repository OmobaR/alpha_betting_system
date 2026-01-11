"""
src/pipeline/MultiSourceOddsCollector.py
Primary Code & Script Generator - TA_1
2026-01-06
Implements the approved multi-source fallback system for odds data.
"""

import os
import sys
import requests
import psycopg2
import logging
import argparse
from datetime import datetime, timedelta
from psycopg2.extras import execute_values
from typing import Optional, Dict, List, Tuple, Any
import random
import time

# ==================== CONFIGURATION & LOGGING ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.FileHandler('odds_collection.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('OddsCollector')

# ==================== MULTI-SOURCE ODDS COLLECTOR ====================

class MultiSourceOddsCollector:
    """
    Implements the fallback strategy:
    1. Primary: Football-Data.org (existing key)
    2. Secondary: Mock odds generator (for testing)
    3. Tertiary: The Odds API (commented out, for future use)
    """

    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.conn = None
        self.cursor = None
        self.football_data_key = os.environ.get('FOOTBALL_DATA_KEY')
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'AlphaBettingSystem/1.0'})

    # -------------------- CORE PUBLIC INTERFACE --------------------

    def collect_odds(self, source: str, days: int = 7, use_all_fixtures: bool = False) -> Dict[str, int]:
        """
        Main entry point. Collects odds based on the specified source.
        """
        logger.info(f"Starting odds collection with source: '{source}', days: {days}")

        if not self._connect_db():
            return {"status": "error", "message": "Database connection failed"}

        try:
            fixture_ids = self._get_target_fixtures(days, use_all_fixtures)

            if not fixture_ids:
                logger.warning("No target fixtures found.")
                return {"total": 0, "success": 0, "failed": 0}

            stats = {"total": len(fixture_ids), "success": 0, "failed": 0}

            for i, fixture_id in enumerate(fixture_ids, 1):
                logger.info(f"Processing {i}/{len(fixture_ids)}: Fixture ID {fixture_id}")
                success = self._process_single_fixture(fixture_id, source)
                if success:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1

                # Basic rate limiting/courtesy delay between calls
                if source == 'football_data' and i < len(fixture_ids):
                    time.sleep(0.5)

            logger.info(f"Collection complete. {stats}")
            return stats

        except Exception as e:
            logger.error(f"Fatal error during collection: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
        finally:
            self._close_db()

    # -------------------- SOURCE 1: FOOTBALL-DATA.ORG --------------------

    def _try_football_data(self, fixture_id: int) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Attempts to fetch odds from Football-Data.org.
        Official endpoint: /v4/matches/{id}/odds [citation:2][citation:3]
        """
        if not self.football_data_key:
            logger.error("FOOTBALL_DATA_KEY environment variable not set.")
            return None, None, None

        url = f"https://api.football-data.org/v4/matches/{fixture_id}/odds"
        headers = {'X-Auth-Token': self.football_data_key}

        try:
            logger.debug(f"Calling Football-Data.org: {url}")
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)

            data = response.json()
            return self._parse_football_data_odds(data)

        except requests.exceptions.HTTPError as e:
            # Handle specific API error codes [citation:7][citation:9]
            if e.response.status_code == 429:
                logger.warning("Rate limit hit for Football-Data.org. Implement backoff.")
            elif e.response.status_code == 404:
                logger.debug(f"Odds not found for fixture {fixture_id} on Football-Data.org.")
            else:
                logger.error(f"HTTP error from Football-Data.org: {e.response.status_code}")
            return None, None, None
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error contacting Football-Data.org: {e}")
            return None, None, None
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse Football-Data.org response: {e}")
            return None, None, None

    def _parse_football_data_odds(self, data: Dict) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Parses the odds from the Football-Data.org API response."""
        try:
            # The structure may contain an 'odds' list with bookmaker data
            if 'odds' not in data:
                return None, None, None

            for bookmaker in data['odds']:
                # Prioritize common bookmakers; accept any available for fallback.
                bookmaker_name = bookmaker.get('bookmaker', '').lower()
                if 'bet365' in bookmaker_name or 'pinnacle' in bookmaker_name or 'william hill' in bookmaker_name:
                    for market in bookmaker.get('markets', []):
                        if market.get('name', '').lower() == 'match winner' or market.get('key', '').lower() == '1x2':
                            for outcome in market.get('outcomes', []):
                                if outcome['name'] == 'Home':
                                    home_odds = float(outcome['price'])
                                elif outcome['name'] == 'Draw':
                                    draw_odds = float(outcome['price'])
                                elif outcome['name'] == 'Away':
                                    away_odds = float(outcome['price'])
                            # Return the first matching market for this bookmaker
                            if 'home_odds' in locals() and 'draw_odds' in locals() and 'away_odds' in locals():
                                logger.debug(f"Found odds: H={home_odds}, D={draw_odds}, A={away_odds}")
                                return home_odds, draw_odds, away_odds
            logger.debug("No suitable 1X2 market found in the response.")
            return None, None, None
        except Exception as e:
            logger.error(f"Error in parsing logic: {e}")
            return None, None, None

    # -------------------- SOURCE 2: MOCK ODDS GENERATOR --------------------

    def _generate_mock_odds(self, fixture_id: int) -> Tuple[float, float, float]:
        """
        Generates realistic decimal odds based on team form.
        Uses a simple model: inverts implied probability from team form and adds a 5% margin[citation:4].
        """
        try:
            # Fetch basic team form for this fixture from the feature views
            query = """
                SELECT
                    COALESCE(home_win_pct_3, 50) as home_win_pct,
                    COALESCE(away_win_pct_3, 50) as away_win_pct,
                    COALESCE(home_unbeaten_pct_3, 50) as home_unbeaten_pct
                FROM features.match_derived
                WHERE fixture_id = %s
            """
            self.cursor.execute(query, (fixture_id,))
            result = self.cursor.fetchone()

            if result:
                home_win_pct, away_win_pct, home_unbeaten_pct = result
                # Simple model: Use win percentages to derive baseline probability
                total_power = home_win_pct + away_win_pct + (100 - home_unbeaten_pct)
                if total_power <= 0:
                    home_win_pct, away_win_pct = 50, 50  # Default to equal chance

                home_prob = home_win_pct / 100.0
                away_prob = away_win_pct / 100.0
                draw_prob = max(0.05, 1.0 - (home_prob + away_prob))  # Ensure at least 5% draw chance

                # Normalize probabilities to sum to 1
                prob_sum = home_prob + draw_prob + away_prob
                home_prob /= prob_sum
                draw_prob /= prob_sum
                away_prob /= prob_sum

                # Add a 5% bookmaker margin[citation:4]
                margin = 0.05
                home_odds = round(1 / (home_prob * (1 - margin)), 2)
                draw_odds = round(1 / (draw_prob * (1 - margin)), 2)
                away_odds = round(1 / (away_prob * (1 - margin)), 2)

                # Clamp odds to a realistic range (1.50 - 5.00)
                home_odds = max(1.50, min(5.00, home_odds))
                draw_odds = max(1.50, min(5.00, draw_odds))
                away_odds = max(1.50, min(5.00, away_odds))

            else:
                # If no features exist, generate plausible random odds
                logger.warning(f"No feature data for fixture {fixture_id}, generating random odds.")
                home_odds = round(random.uniform(1.80, 2.50), 2)
                draw_odds = round(random.uniform(3.00, 3.80), 2)
                away_odds = round(random.uniform(3.50, 5.00), 2)

            logger.debug(f"Generated mock odds: H={home_odds}, D={draw_odds}, A={away_odds}")
            return home_odds, draw_odds, away_odds

        except Exception as e:
            logger.error(f"Error generating mock odds: {e}")
            # Fallback to very generic odds
            return 2.00, 3.40, 3.80

    # -------------------- SOURCE 3: THE ODDS API (COMMENTED OUT) --------------------
    """
    def _try_the_odds_api(self, fixture_id: int):
        # Placeholder for future integration.
        # Requires THE_ODDS_API_KEY environment variable.
        pass
    """

    # -------------------- DATABASE & PIPELINE LOGIC --------------------

    def _connect_db(self) -> bool:
        """Establishes connection to the PostgreSQL database on port 5433."""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.cursor = self.conn.cursor()
            logger.info("Database connection established.")
            return True
        except Exception as e:
            logger.error(f"Could not connect to database: {e}")
            return False

    def _close_db(self):
        """Closes the database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed.")

    def _get_target_fixtures(self, days_back: int, use_all: bool) -> List[int]:
        """Fetches fixture IDs based on the command-line criteria."""
        try:
            if use_all:
                # Get all historical fixtures that have results but no odds
                query = """
                    SELECT DISTINCT f.api_football_id
                    FROM fixtures f
                    LEFT JOIN odds_snapshots o ON f.api_football_id = o.fixture_id
                    WHERE f.api_football_id IS NOT NULL
                      AND f.full_time_home_goals IS NOT NULL
                      AND o.fixture_id IS NULL
                    ORDER BY f.match_date DESC
                """
                self.cursor.execute(query)
            else:
                # Get recent fixtures (last N days) without odds
                query = """
                    SELECT DISTINCT f.api_football_id
                    FROM fixtures f
                    LEFT JOIN odds_snapshots o ON f.api_football_id = o.fixture_id
                    WHERE f.api_football_id IS NOT NULL
                      AND f.match_date >= NOW() - INTERVAL '%s days'
                      AND o.fixture_id IS NULL
                    ORDER BY f.match_date DESC
                """
                self.cursor.execute(query, (days_back,))

            results = self.cursor.fetchall()
            fixture_ids = [r[0] for r in results if r[0] is not None]
            logger.info(f"Found {len(fixture_ids)} target fixtures.")
            return fixture_ids

        except Exception as e:
            logger.error(f"Error fetching target fixtures: {e}")
            return []

    def _process_single_fixture(self, fixture_id: int, source: str) -> bool:
        """Orchestrates fetching and storing odds for a single fixture using the selected source."""
        home_odds, draw_odds, away_odds = None, None, None

        if source == 'football_data':
            home_odds, draw_odds, away_odds = self._try_football_data(fixture_id)
        elif source == 'mock':
            home_odds, draw_odds, away_odds = self._generate_mock_odds(fixture_id)
        # elif source == 'the_odds_api':
        #   home_odds, draw_odds, away_odds = self._try_the_odds_api(fixture_id)

        if None in (home_odds, draw_odds, away_odds):
            logger.warning(f"Could not get valid odds for fixture {fixture_id} from source '{source}'.")
            return False

        return self._store_odds_snapshot(fixture_id, home_odds, draw_odds, away_odds, source)

    def _store_odds_snapshot(self, fixture_id: int, home: float, draw: float, away: float, source: str) -> bool:
        """Stores the odds snapshot in the database."""
        try:
            # The odds_snapshots table schema includes a 'data_source' field
            insert_sql = """
                INSERT INTO odds_snapshots 
                (fixture_id, bookmaker_id, market_type, home_odds, draw_odds, away_odds, data_source, snapshot_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fixture_id, bookmaker_id, snapshot_at) 
                DO UPDATE SET 
                    home_odds = EXCLUDED.home_odds,
                    draw_odds = EXCLUDED.draw_odds,
                    away_odds = EXCLUDED.away_odds,
                    data_source = EXCLUDED.data_source
            """
            # Use bookmaker_id = 999 for mock/data sources, or map real ones
            bookmaker_id = 999 if source == 'mock' else 1  # 1 could represent a generic "consensus"
            self.cursor.execute(insert_sql, (
                fixture_id, bookmaker_id, '1X2', home, draw, away, source, datetime.now()
            ))
            self.conn.commit()
            logger.info(f"Stored odds for fixture {fixture_id} from source '{source}'.")
            return True
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to store odds for fixture {fixture_id}: {e}")
            return False

# ==================== COMMAND-LINE EXECUTION ====================

def main():
    """Parses arguments and runs the collector."""
    parser = argparse.ArgumentParser(description='AlphaBetting Multi-Source Odds Collector')
    parser.add_argument('--source', type=str, required=True,
                        choices=['football_data', 'mock'],  # 'the_odds_api' commented out
                        help='Source for odds data.')
    parser.add_argument('--days', type=int, default=7,
                        help='For real sources, fetch fixtures from the last N days.')
    parser.add_argument('--all', action='store_true',
                        help='If using mock source, generate odds for ALL historical fixtures.')

    args = parser.parse_args()

    # Database configuration - uses port 5433 as mandated
    db_config = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': os.environ.get('DB_PORT', '5433'),
        'database': os.environ.get('DB_NAME', 'football_betting'),
        'user': os.environ.get('DB_USER', 'betting_user'),
        'password': os.environ.get('DB_PASSWORD', 'betting_password')
    }

    # Validate environment variable for football_data source
    if args.source == 'football_data' and not os.environ.get('FOOTBALL_DATA_KEY'):
        logger.critical("FOOTBALL_DATA_KEY environment variable not set but required for 'football_data' source.")
        sys.exit(1)

    collector = MultiSourceOddsCollector(db_config)
    stats = collector.collect_odds(args.source, args.days, args.all)

    print("\n" + "="*60)
    print("ODDS COLLECTION RUN COMPLETE")
    print("="*60)
    if isinstance(stats, dict) and "status" in stats and stats["status"] == "error":
        print(f"❌ ERROR: {stats.get('message')}")
        sys.exit(1)
    else:
        print(f"📊 Total fixtures processed: {stats.get('total', 0)}")
        print(f"✅ Successfully stored: {stats.get('success', 0)}")
        print(f"❌ Failed: {stats.get('failed', 0)}")
        print("="*60)

if __name__ == '__main__':
    main()