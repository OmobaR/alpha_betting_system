#!/usr/bin/env python3
"""
Initialize database schema for football betting system
"""
import psycopg2
import sys

def main():
    # Connection parameters - match your docker-compose settings
    connection_params = {
        'host': 'localhost',
        'port': 5433,
        'database': 'football_betting',
        'user': 'betting_user',
        'password': 'betting_password'
    }
    
    # SQL statements to create the raw schema and tables
    sql_statements = [
        # Create raw schema
        "CREATE SCHEMA IF NOT EXISTS raw;",
        
        # Create raw.fixtures table
        """
        CREATE TABLE IF NOT EXISTS raw.fixtures (
            external_id VARCHAR(100) PRIMARY KEY,
            source_system VARCHAR(50) NOT NULL,
            league_external_code VARCHAR(10) NOT NULL,
            league_name VARCHAR(100),
            season VARCHAR(10),
            home_team_name VARCHAR(100) NOT NULL,
            away_team_name VARCHAR(100) NOT NULL,
            match_date DATE,
            home_goals INTEGER,
            away_goals INTEGER,
            result CHAR(1),
            home_goals_ht INTEGER,
            away_goals_ht INTEGER,
            referee VARCHAR(100),
            attendance INTEGER,
            matchday INTEGER,
            available_at TIMESTAMP,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        
        # Create raw.teams table
        """
        CREATE TABLE IF NOT EXISTS raw.teams (
            external_id VARCHAR(100) PRIMARY KEY,
            team_name VARCHAR(100) NOT NULL,
            source_system VARCHAR(50),
            available_at TIMESTAMP,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        
        # Create raw.leagues table
        """
        CREATE TABLE IF NOT EXISTS raw.leagues (
            external_id VARCHAR(10) PRIMARY KEY,
            league_name VARCHAR(100) NOT NULL,
            country VARCHAR(100),
            tier INTEGER,
            source_system VARCHAR(50),
            available_at TIMESTAMP,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        
        # Create raw.odds_snapshots table
        """
        CREATE TABLE IF NOT EXISTS raw.odds_snapshots (
            id SERIAL PRIMARY KEY,
            fixture_external_id VARCHAR(100) NOT NULL,
            bookmaker_name VARCHAR(50) NOT NULL,
            market_type VARCHAR(20) NOT NULL,
            home_odds DECIMAL(8,3),
            draw_odds DECIMAL(8,3),
            away_odds DECIMAL(8,3),
            snapshot_at TIMESTAMP NOT NULL,
            is_closing_line BOOLEAN DEFAULT FALSE,
            available_at TIMESTAMP,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (fixture_external_id, bookmaker_name, market_type, snapshot_at)
        );
        """,
        
        # Create indexes for performance
        "CREATE INDEX IF NOT EXISTS idx_fixtures_league_season ON raw.fixtures(league_external_code, season);",
        "CREATE INDEX IF NOT EXISTS idx_fixtures_match_date ON raw.fixtures(match_date);",
        "CREATE INDEX IF NOT EXISTS idx_odds_fixture_id ON raw.odds_snapshots(fixture_external_id);",
        "CREATE INDEX IF NOT EXISTS idx_odds_bookmaker ON raw.odds_snapshots(bookmaker_name);",
    ]
    
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(**connection_params)
        conn.autocommit = True  # Enable autocommit for DDL statements
        cursor = conn.cursor()
        
        print("Creating database schema...")
        
        # Execute all SQL statements
        for i, sql in enumerate(sql_statements, 1):
            print(f"  Executing statement {i}/{len(sql_statements)}...")
            try:
                cursor.execute(sql)
            except Exception as e:
                print(f"    Warning: {e}")
                continue
        
        # Insert default leagues (Big 5 European leagues)
        print("\nInserting default leagues...")
        leagues = [
            ('E0', 'English Premier League', 'England', 1, 'football-data.co.uk'),
            ('SP1', 'Spanish La Liga', 'Spain', 1, 'football-data.co.uk'),
            ('D1', 'German Bundesliga', 'Germany', 1, 'football-data.co.uk'),
            ('I1', 'Italian Serie A', 'Italy', 1, 'football-data.co.uk'),
            ('F1', 'French Ligue 1', 'France', 1, 'football-data.co.uk'),
        ]
        
        for league in leagues:
            cursor.execute("""
                INSERT INTO raw.leagues (external_id, league_name, country, tier, source_system, available_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (external_id) DO NOTHING
            """, league)
        
        print(f"Inserted {len(leagues)} leagues")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Database schema initialized successfully!")
        return 0
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
