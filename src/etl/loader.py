"""
Database Loader for ETL Pipeline
"""
import psycopg2
import logging
from typing import List, Dict, Any, Optional
from psycopg2.extras import execute_batch
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)

class DatabaseLoader:
    """Load parsed data into PostgreSQL database"""
    
    def __init__(self, config):
        self.config = config
        self.connection = None
        
    def connect(self):
        """Establish database connection"""
        try:
            # Use dictionary access for config
            db_config = self.config['database']
            
            # Build connection string
            if hasattr(db_config, 'connection_string'):
                conn_str = db_config.connection_string
            else:
                # Fallback to building connection string
                password = db_config.password or 'betting_password'
                conn_str = f"postgresql://{db_config.user}:{password}@{db_config.host}:{db_config.port}/{db_config.name}"
            
            self.connection = psycopg2.connect(conn_str)
            logger.info("[OK] Database connection established")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.debug("Database connection closed")
    
    def load_fixtures(self, fixtures: List[Dict]) -> int:
        """Load fixtures into raw.fixtures table"""
        if not fixtures:
            return 0
        
        if not self.connection and not self.connect():
            return 0
        
        try:
            cursor = self.connection.cursor()
            
            # Insert or update fixtures
            insert_query = """
            INSERT INTO raw.fixtures (
                external_id, source_system, league_external_code, league_name, 
                season, home_team_name, away_team_name, match_date, home_goals, 
                away_goals, result, home_goals_ht, away_goals_ht, referee, 
                attendance, matchday, available_at, ingested_at
            ) VALUES (
                %(external_id)s, %(source_system)s, %(league_external_code)s, %(league_name)s,
                %(season)s, %(home_team_name)s, %(away_team_name)s, %(match_date)s, %(home_goals)s,
                %(away_goals)s, %(result)s, %(home_goals_ht)s, %(away_goals_ht)s, %(referee)s,
                %(attendance)s, %(matchday)s, %(available_at)s, %(ingested_at)s
            )
            ON CONFLICT (external_id) DO UPDATE SET
                home_goals = EXCLUDED.home_goals,
                away_goals = EXCLUDED.away_goals,
                result = EXCLUDED.result,
                home_goals_ht = EXCLUDED.home_goals_ht,
                away_goals_ht = EXCLUDED.away_goals_ht,
                referee = EXCLUDED.referee,
                attendance = EXCLUDED.attendance,
                matchday = EXCLUDED.matchday,
                updated_at = CURRENT_TIMESTAMP
            """
            
            execute_batch(cursor, insert_query, fixtures)
            self.connection.commit()
            
            loaded_count = len(fixtures)
            logger.info(f"Loaded {loaded_count} fixtures into database")
            
            cursor.close()
            return loaded_count
            
        except Exception as e:
            logger.error(f"Error loading fixtures: {e}")
            self.connection.rollback()
            return 0
    
    def load_odds(self, odds_snapshots: Dict[str, List]) -> int:
        """Load odds snapshots into raw.odds_snapshots table"""
        if not odds_snapshots:
            return 0
        
        if not self.connection and not self.connect():
            return 0
        
        try:
            cursor = self.connection.cursor()
            
            # Flatten the odds snapshots dictionary
            odds_records = []
            for snapshot_key, odds_data in odds_snapshots.items():
                if isinstance(odds_data, dict):
                    odds_records.append(odds_data)
                elif isinstance(odds_data, list):
                    odds_records.extend(odds_data)
            
            if not odds_records:
                return 0
            
            insert_query = """
            INSERT INTO raw.odds_snapshots (
                fixture_external_id, bookmaker_name, market_type,
                home_odds, draw_odds, away_odds,
                snapshot_at, is_closing_line, available_at
            ) VALUES (
                %(fixture_external_id)s, %(bookmaker_name)s, %(market_type)s,
                %(home_odds)s, %(draw_odds)s, %(away_odds)s,
                %(snapshot_at)s, %(is_closing_line)s, %(available_at)s
            )
            ON CONFLICT (fixture_external_id, bookmaker_name, market_type, snapshot_at) 
            DO NOTHING
            """
            
            execute_batch(cursor, insert_query, odds_records)
            self.connection.commit()
            
            loaded_count = len(odds_records)
            logger.info(f"Loaded {loaded_count} odds records into database")
            
            cursor.close()
            return loaded_count
            
        except Exception as e:
            logger.error(f"Error loading odds: {e}")
            self.connection.rollback()
            return 0
    
    def load_teams(self, team_names: List[str]) -> int:
        """Load unique team names into raw.teams table"""
        if not team_names:
            return 0

        if not self.connection and not self.connect():
            return 0

        try:
            cursor = self.connection.cursor()

            # Team name normalization mapping
            team_normalization = {
                'Man Utd': 'Manchester United',
                'Man City': 'Manchester City', 
                'Spurs': 'Tottenham Hotspur',
                'Man United': 'Manchester United',
                'West Brom': 'West Bromwich Albion',
                'Wolves': 'Wolverhampton Wanderers',
                'Sheff Utd': 'Sheffield United',
                'Sheff Wed': 'Sheffield Wednesday',
                'MK Dons': 'Milton Keynes Dons',
                "Nott'm Forest": 'Nottingham Forest',
                'Brighton': 'Brighton & Hove Albion',
                'Leicester': 'Leicester City',
                'Newcastle': 'Newcastle United',
            }

            # Create team records with normalized names
            team_records = []
            for team_name in set(team_names):  # Deduplicate       
                if team_name:
                    # Normalize team name
                    normalized_name = team_normalization.get(team_name, team_name)
                    external_id = f"team_{normalized_name.lower().replace(' ', '_')}"
                    team_records.append({
                        'external_id': external_id,
                        'team_name': normalized_name,
                        'source_system': 'football-data.co.uk',    
                        'available_at': datetime.now().isoformat(),
                        'ingested_at': datetime.now().isoformat()  
                    })

            # Simple INSERT query
            insert_query = """
                INSERT INTO raw.teams (external_id, team_name, source_system, available_at, ingested_at)
                VALUES (%(external_id)s, %(team_name)s, %(source_system)s, %(available_at)s, %(ingested_at)s)
                ON CONFLICT (external_id) DO NOTHING
            """

            cursor.executemany(insert_query, team_records)
            self.connection.commit()

            logger.info(f"Loaded {cursor.rowcount} teams into database")
            return cursor.rowcount

        except Exception as e:
            logger.error(f"Error loading teams: {e}")
            self.connection.rollback()
            raise
    def check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database"""
        if not self.connection and not self.connect():
            return False
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'raw' 
                    AND table_name = %s
                )
            """, (table_name,))
            
            exists = cursor.fetchone()[0]
            cursor.close()
            
            return exists
            
        except Exception as e:
            logger.error(f"Error checking table {table_name}: {e}")
            return False
