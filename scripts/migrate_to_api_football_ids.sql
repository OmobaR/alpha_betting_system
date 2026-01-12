-- ============================================================================
-- MIGRATION SCRIPT: Standardize on API-Football fixture_id system
-- ============================================================================
-- This script migrates the database to use API-Football's numeric fixture_id
-- as the primary identifier for matches.
--
-- IMPORTANT: Run this in the football_betting database on port 5433
-- ============================================================================

-- ----------------------------------------------------------------------------
-- STEP 1: Add API-Football ID column to fixtures table
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    -- Check if column already exists
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'fixtures' 
        AND column_name = 'api_football_id'
    ) THEN
        -- Add the column
        ALTER TABLE fixtures ADD COLUMN api_football_id INTEGER;
        
        -- Add index for performance
        CREATE INDEX idx_fixtures_api_football_id ON fixtures(api_football_id);
        
        RAISE NOTICE 'Added api_football_id column and index';
    ELSE
        RAISE NOTICE 'api_football_id column already exists';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- STEP 2: Create temporary mapping table
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS temp_fixture_mapping;
CREATE TEMP TABLE temp_fixture_mapping (
    legacy_match_id VARCHAR(100) PRIMARY KEY,
    api_football_id INTEGER,
    match_date DATE,
    home_team_name VARCHAR(100),
    away_team_name VARCHAR(100),
    match_found BOOLEAN DEFAULT FALSE
);

-- ----------------------------------------------------------------------------
-- STEP 3: Populate mapping table with existing fixtures
-- ----------------------------------------------------------------------------
INSERT INTO temp_fixture_mapping (legacy_match_id, match_date, home_team_name, away_team_name)
SELECT 
    f.match_id,
    f.match_date,
    ht.name as home_team_name,
    at.name as away_team_name
FROM fixtures f
JOIN teams ht ON f.home_team_id = ht.id
JOIN teams at ON f.away_team_id = at.id
WHERE f.api_football_id IS NULL;

RAISE NOTICE 'Populated temp mapping table with % fixtures', (SELECT COUNT(*) FROM temp_fixture_mapping);

-- ----------------------------------------------------------------------------
-- STEP 4: Manual backfill instructions for Project Owner
-- ----------------------------------------------------------------------------
/*
MANUAL BACKFILL PROCESS:

You need to run a Python script to fetch API-Football fixture IDs for existing matches.
The script should:

1. For each row in temp_fixture_mapping, search API-Football for matches:
   - On the same date (±1 day)
   - With similar team names (use fuzzy matching)

2. Use this API endpoint:
   GET https://v3.football.api-sports.io/fixtures
   Parameters: date=YYYY-MM-DD, league=[league_id], season=YYYY

3. Update temp_fixture_mapping with found api_football_id

Example Python code:

import requests
import psycopg2
from fuzzywuzzy import fuzz
from datetime import datetime

# Connect to database
conn = psycopg2.connect(host="localhost", port=5433, database="football_betting", 
                       user="betting_user", password="your_password")
cursor = conn.cursor()

# Get unmapped fixtures
cursor.execute("SELECT * FROM temp_fixture_mapping WHERE NOT match_found")
rows = cursor.fetchall()

for row in rows:
    legacy_id, match_date, home_team, away_team = row[0], row[2], row[3], row[4]
    
    # Search API-Football
    response = requests.get(
        "https://v3.football.api-sports.io/fixtures",
        headers={"x-apisports-key": "YOUR_API_KEY"},
        params={
            "date": match_date.strftime("%Y-%m-%d"),
            "league": 39,  # Premier League (adjust per league)
            "season": match_date.year
        }
    )
    
    if response.status_code == 200:
        fixtures = response.json().get("response", [])
        
        for fixture in fixtures:
            api_home = fixture["teams"]["home"]["name"]
            api_away = fixture["teams"]["away"]["name"]
            
            # Fuzzy match team names
            home_score = fuzz.ratio(home_team.lower(), api_home.lower())
            away_score = fuzz.ratio(away_team.lower(), api_away.lower())
            
            if home_score > 80 and away_score > 80:
                api_fixture_id = fixture["fixture"]["id"]
                
                # Update mapping
                cursor.execute("""
                    UPDATE temp_fixture_mapping 
                    SET api_football_id = %s, match_found = TRUE
                    WHERE legacy_match_id = %s
                """, (api_fixture_id, legacy_id))
                
                conn.commit()
                break

cursor.close()
conn.close()
*/

-- ----------------------------------------------------------------------------
-- STEP 5: Update fixtures table with mapped IDs
-- ----------------------------------------------------------------------------
/*
-- AFTER running the Python backfill script, run this:
UPDATE fixtures f
SET api_football_id = m.api_football_id
FROM temp_fixture_mapping m
WHERE f.match_id = m.legacy_match_id
AND m.api_football_id IS NOT NULL;

-- Verify the update
SELECT COUNT(*) as updated_count 
FROM fixtures 
WHERE api_football_id IS NOT NULL;

-- Set api_football_id as NOT NULL for new fixtures going forward
ALTER TABLE fixtures ALTER COLUMN api_football_id SET NOT NULL;
*/

-- ----------------------------------------------------------------------------
-- STEP 6: Create foreign key from odds_snapshots to fixtures
-- ----------------------------------------------------------------------------
/*
-- After migration, add foreign key constraint
ALTER TABLE odds_snapshots 
ADD CONSTRAINT fk_odds_snapshots_fixtures 
FOREIGN KEY (fixture_id) 
REFERENCES fixtures(api_football_id);

-- Update odds_snapshots to use api_football_id if using different IDs
-- (This assumes odds_snapshots already uses API-Football fixture IDs)
*/

-- ----------------------------------------------------------------------------
-- STEP 7: Migration verification queries
-- ----------------------------------------------------------------------------
-- Check migration status
SELECT 
    COUNT(*) as total_fixtures,
    COUNT(api_football_id) as mapped_fixtures,
    ROUND(COUNT(api_football_id) * 100.0 / COUNT(*), 2) as percent_mapped
FROM fixtures;

-- Sample of unmapped fixtures
SELECT 
    f.match_id,
    f.match_date,
    ht.name as home_team,
    at.name as away_team,
    f.league_id
FROM fixtures f
JOIN teams ht ON f.home_team_id = ht.id
JOIN teams at ON f.away_team_id = at.id
WHERE f.api_football_id IS NULL
LIMIT 10;

RAISE NOTICE 'Migration script completed. Please run the Python backfill and then execute the UPDATE statements in STEP 5.';