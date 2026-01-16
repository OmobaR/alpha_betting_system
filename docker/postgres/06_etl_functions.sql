-- ========== ETL SUPPORT FUNCTIONS ==========

-- Function to get or create team ID
CREATE OR REPLACE FUNCTION raw.get_or_create_team(
    p_team_name VARCHAR(100),
    p_source_system VARCHAR(50) DEFAULT 'football-data.co.uk'
) RETURNS INTEGER AS $$
DECLARE
    v_team_id INTEGER;
    v_normalized_name VARCHAR(100);
BEGIN
    -- Normalize team name
    v_normalized_name = LOWER(REPLACE(p_team_name, ' ', '_'));
    
    -- Try to find existing team
    SELECT team_id INTO v_team_id
    FROM raw.teams
    WHERE normalized_name = v_normalized_name
        AND source_system = p_source_system;
    
    -- If not found, create new team
    IF v_team_id IS NULL THEN
        INSERT INTO raw.teams (
            external_id,
            source_system,
            name,
            normalized_name,
            available_at,
            ingested_at
        ) VALUES (
            MD5(v_normalized_name)::VARCHAR(32),
            p_source_system,
            p_team_name,
            v_normalized_name,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        RETURNING team_id INTO v_team_id;
    END IF;
    
    RETURN v_team_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get or create league ID
CREATE OR REPLACE FUNCTION raw.get_or_create_league(
    p_external_code VARCHAR(10),
    p_league_name VARCHAR(100),
    p_country VARCHAR(50),
    p_tier INTEGER,
    p_source_system VARCHAR(50) DEFAULT 'football-data.co.uk'
) RETURNS INTEGER AS $$
DECLARE
    v_league_id INTEGER;
BEGIN
    -- Try to find existing league
    SELECT league_id INTO v_league_id
    FROM raw.leagues
    WHERE external_id = p_external_code
        AND source_system = p_source_system;
    
    -- If not found, create new league
    IF v_league_id IS NULL THEN
        INSERT INTO raw.leagues (
            external_id,
            source_system,
            name,
            country,
            tier,
            available_at,
            ingested_at
        ) VALUES (
            p_external_code,
            p_source_system,
            p_league_name,
            p_country,
            p_tier,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        RETURNING league_id INTO v_league_id;
    END IF;
    
    RETURN v_league_id;
END;
$$ LANGUAGE plpgsql;

-- Function to check if fixture already exists
CREATE OR REPLACE FUNCTION raw.fixture_exists(
    p_external_id VARCHAR(32),
    p_source_system VARCHAR(50)
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM raw.fixtures 
        WHERE external_id = p_external_id 
        AND source_system = p_source_system
    );
END;
$$ LANGUAGE plpgsql;

-- Function to calculate implied probabilities from odds
CREATE OR REPLACE FUNCTION raw.calculate_implied_probabilities(
    p_home_odds DECIMAL,
    p_draw_odds DECIMAL,
    p_away_odds DECIMAL
) RETURNS TABLE (
    home_implied DECIMAL,
    draw_implied DECIMAL,
    away_implied DECIMAL,
    overround DECIMAL
) AS $$
DECLARE
    v_total_implied DECIMAL;
BEGIN
    home_implied := 1.0 / NULLIF(p_home_odds, 0);
    draw_implied := 1.0 / NULLIF(p_draw_odds, 0);
    away_implied := 1.0 / NULLIF(p_away_odds, 0);
    
    v_total_implied := COALESCE(home_implied, 0) + 
                      COALESCE(draw_implied, 0) + 
                      COALESCE(away_implied, 0);
    
    overround := (v_total_implied - 1.0) * 100.0;
    
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- View for ETL progress monitoring
CREATE OR REPLACE VIEW monitoring.etl_progress AS
SELECT 
    pc.pipeline_name,
    pc.source_system,
    pc.league_external_id,
    l.name as league_name,
    pc.last_successful_run,
    pc.watermark_timestamp,
    pc.records_processed,
    pc.success_rate,
    pc.retry_count,
    pc.is_active,
    pc.created_at,
    pc.updated_at,
    CASE 
        WHEN pc.is_active THEN 'RUNNING'
        WHEN pc.last_successful_run IS NULL THEN 'FAILED'
        WHEN AGE(NOW(), pc.last_successful_run) < INTERVAL '1 day' THEN 'RECENT'
        ELSE 'STALE'
    END as status
FROM monitoring.pipeline_checkpoints pc
LEFT JOIN raw.leagues l ON pc.league_external_id = l.external_id 
    AND pc.source_system = l.source_system
ORDER BY pc.updated_at DESC;

-- Materialized view for ETL statistics (refreshed daily)
CREATE MATERIALIZED VIEW IF NOT EXISTS monitoring.etl_statistics AS
SELECT 
    DATE(ingested_at) as ingest_date,
    source_system,
    COUNT(*) as fixtures_ingested,
    COUNT(DISTINCT league_id) as leagues_ingested,
    COUNT(DISTINCT home_team_id) + COUNT(DISTINCT away_team_id) as teams_ingested,
    MIN(match_date) as earliest_match,
    MAX(match_date) as latest_match
FROM raw.fixtures
WHERE ingested_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(ingested_at), source_system
ORDER BY ingest_date DESC;

-- Refresh function for materialized view
CREATE OR REPLACE FUNCTION monitoring.refresh_etl_statistics()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW monitoring.etl_statistics;
END;
$$ LANGUAGE plpgsql;

-- Create indexes for ETL performance
CREATE INDEX IF NOT EXISTS idx_fixtures_external_source 
ON raw.fixtures(external_id, source_system);

CREATE INDEX IF NOT EXISTS idx_teams_normalized_source 
ON raw.teams(normalized_name, source_system);

CREATE INDEX IF NOT EXISTS idx_leagues_external_source 
ON raw.leagues(external_id, source_system);

-- Grant permissions for ETL user
GRANT USAGE ON SCHEMA raw TO betting_user;
GRANT USAGE ON SCHEMA features TO betting_user;
GRANT USAGE ON SCHEMA monitoring TO betting_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA raw TO betting_user;
GRANT SELECT ON ALL TABLES IN SCHEMA features TO betting_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA monitoring TO betting_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA raw TO betting_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA monitoring TO betting_user;
