-- ========== PUBLIC VIEWS WITH ANTI-BIAS FILTERS ==========

-- Public fixtures view (FOR BACKWARD COMPATIBILITY)
CREATE OR REPLACE VIEW public.fixtures AS
SELECT 
    fixture_id AS id,
    external_id AS api_football_id,
    league_id,
    home_team_id,
    away_team_id,
    season,
    match_date,
    
    -- Goals (aliased to match existing feature SQL)
    home_goals AS full_time_home_goals,
    away_goals AS full_time_away_goals,
    home_goals_ht AS half_time_home_goals,
    away_goals_ht AS half_time_away_goals,
    
    -- Result (calculated)
    CASE 
        WHEN home_goals > away_goals THEN 'H'
        WHEN home_goals < away_goals THEN 'A'
        ELSE 'D'
    END AS result,
    
    -- Other fields
    kickoff_at,
    status,
    matchday,
    venue,
    referee
    
FROM raw.fixtures
-- CRITICAL ANTI-BIAS FILTER
WHERE available_at <= CURRENT_TIMESTAMP;

-- Public teams view (FOR BACKWARD COMPATIBILITY)
CREATE OR REPLACE VIEW public.teams AS
SELECT 
    team_id AS id,
    external_id,
    name,
    normalized_name,
    country,
    short_name
    
FROM raw.teams
-- CRITICAL ANTI-BIAS FILTER
WHERE available_at <= CURRENT_TIMESTAMP;

-- Public leagues view
CREATE OR REPLACE VIEW public.leagues AS
SELECT 
    league_id,
    external_id,
    name,
    country,
    tier,
    division
    
FROM raw.leagues
WHERE available_at <= CURRENT_TIMESTAMP;