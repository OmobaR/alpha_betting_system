-- ========== CORE RAW TABLES WITH ANTI-BIAS TIMESTAMPS ==========

-- Leagues table
CREATE TABLE raw.leagues (
    league_id SERIAL PRIMARY KEY,
    external_id INTEGER UNIQUE NOT NULL,
    source_system VARCHAR(50) NOT NULL DEFAULT 'football-data.co.uk',
    name VARCHAR(100) NOT NULL,
    country VARCHAR(50),
    tier INTEGER,
    division VARCHAR(50),
    data_quality_score DECIMAL(3,2) DEFAULT 1.0,
    
    -- ANTI-BIAS TIMESTAMPS (CRITICAL)
    available_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT check_available_before_ingested CHECK (available_at <= ingested_at),
    INDEX idx_leagues_source_external (source_system, external_id)
);

-- Teams table with canonical normalization
CREATE TABLE raw.teams (
    team_id SERIAL PRIMARY KEY,
    external_id INTEGER UNIQUE NOT NULL,
    source_system VARCHAR(50) NOT NULL DEFAULT 'football-data.co.uk',
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(50),
    normalized_name VARCHAR(100),
    canonical_name VARCHAR(100),
    country VARCHAR(50),
    founded_year INTEGER,
    stadium_name VARCHAR(100),
    stadium_capacity INTEGER,
    
    -- Cross-source matching metadata
    matching_confidence DECIMAL(3,2) DEFAULT 1.0,
    matched_team_id INTEGER REFERENCES raw.teams(team_id),
    
    -- ANTI-BIAS TIMESTAMPS
    available_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_teams_normalized (normalized_name),
    INDEX idx_teams_canonical (canonical_name)
);

-- Bookmakers (for odds tracking)
CREATE TABLE raw.bookmakers (
    bookmaker_id SERIAL PRIMARY KEY,
    external_id INTEGER UNIQUE,
    name VARCHAR(50) NOT NULL,
    category VARCHAR(20) NOT NULL DEFAULT 'soft', -- 'sharp', 'soft', 'exchange'
    country VARCHAR(50),
    margin DECIMAL(5,3) DEFAULT 1.05,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- ANTI-BIAS TIMESTAMPS
    available_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Fixtures - MAIN TABLE (Hypertable for TimescaleDB)
CREATE TABLE raw.fixtures (
    fixture_id BIGSERIAL PRIMARY KEY,
    external_id BIGINT UNIQUE NOT NULL,
    league_id INTEGER REFERENCES raw.leagues(league_id),
    home_team_id INTEGER REFERENCES raw.teams(team_id),
    away_team_id INTEGER REFERENCES raw.teams(team_id),
    season VARCHAR(20) NOT NULL,
    match_date DATE NOT NULL,
    match_time TIME,
    matchday INTEGER,
    
    -- Match metadata
    status VARCHAR(20) DEFAULT 'scheduled',
    venue VARCHAR(100),
    attendance INTEGER,
    referee VARCHAR(100),
    
    -- Results (populated post-match)
    home_goals INTEGER,
    away_goals INTEGER,
    home_goals_ht INTEGER,
    away_goals_ht INTEGER,
    
    -- ANTI-BIAS TIMESTAMPS (MOST CRITICAL)
    announced_at TIMESTAMP WITH TIME ZONE,
    kickoff_at TIMESTAMP WITH TIME ZONE NOT NULL,
    final_whistle_at TIMESTAMP WITH TIME ZONE,
    result_available_at TIMESTAMP WITH TIME ZONE,
    odds_closing_at TIMESTAMP WITH TIME ZONE,
    
    -- Point-in-time query anchor
    available_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Performance indexes
    INDEX idx_fixtures_league_season (league_id, season),
    INDEX idx_fixtures_teams (home_team_id, away_team_id),
    INDEX idx_fixtures_kickoff (kickoff_at),
    INDEX idx_fixtures_available (available_at) -- FOR POINT-IN-TIME QUERIES
);

-- Convert to TimescaleDB hypertable for time-series optimization
SELECT create_hypertable('raw.fixtures', 'kickoff_at', 
    chunk_time_interval => INTERVAL '30 days',
    if_not_exists => TRUE);

-- Odds Snapshots (Hypertable for time-series)
CREATE TABLE raw.odds_snapshots (
    odds_id BIGSERIAL,
    fixture_id BIGINT REFERENCES raw.fixtures(fixture_id),
    bookmaker_id INTEGER REFERENCES raw.bookmakers(bookmaker_id),
    market_type VARCHAR(30) NOT NULL, -- '1x2', 'asian_handicap', 'over_under'
    market_subtype VARCHAR(50), -- '-1.5', '2.5', etc
    
    -- Decimal odds (European format)
    home_odds DECIMAL(8,3),
    draw_odds DECIMAL(8,3),
    away_odds DECIMAL(8,3),
    
    -- Implied probabilities (calculated)
    home_implied DECIMAL(5,4),
    draw_implied DECIMAL(5,4),
    away_implied DECIMAL(5,4),
    overround DECIMAL(6,4),
    
    -- Market metadata
    is_opening_line BOOLEAN DEFAULT FALSE,
    is_closing_line BOOLEAN DEFAULT FALSE,
    is_live BOOLEAN DEFAULT FALSE,
    volume_estimate DECIMAL(12,2),
    
    -- SNAPSHOT TIMING
    snapshot_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- ANTI-BIAS TIMESTAMPS
    available_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Composite unique constraint
    UNIQUE(fixture_id, bookmaker_id, market_type, market_subtype, snapshot_at),
    
    PRIMARY KEY (odds_id, snapshot_at)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('raw.odds_snapshots', 'snapshot_at',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE);