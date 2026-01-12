-- ============================================================================
-- ADAPTED FEATURE VIEWS - References public.* views with anti-bias filters
-- ============================================================================
-- All rolling calculations use window of 3 matches (n=3)
-- Updated to use public.fixtures and public.teams (which include anti-bias filters)
-- ============================================================================

-- Drop existing views if they exist
DROP VIEW IF EXISTS features.match_derived CASCADE;
DROP VIEW IF EXISTS features.match_base CASCADE;
DROP VIEW IF EXISTS features.home_rolling CASCADE;
DROP VIEW IF EXISTS features.away_rolling CASCADE;
DROP VIEW IF EXISTS features.h2h CASCADE;

-- ----------------------------------------------------------------------------
-- BASE VIEW: Core match data with derived columns
-- ----------------------------------------------------------------------------
CREATE VIEW features.match_base AS
SELECT 
    f.id as internal_id,
    f.api_football_id as fixture_id,
    f.match_date,
    f.season,
    f.league_id,
    f.home_team_id,
    f.away_team_id,
    ht.name as home_team_name,
    at.name as away_team_name,
    
    -- Match results
    f.full_time_home_goals as home_goals,
    f.full_time_away_goals as away_goals,
    f.half_time_home_goals as home_goals_ht,
    f.half_time_away_goals as away_goals_ht,
    
    -- Result codes
    CASE 
        WHEN f.full_time_home_goals > f.full_time_away_goals THEN 'H'
        WHEN f.full_time_home_goals < f.full_time_away_goals THEN 'A'
        ELSE 'D'
    END as result,
    
    -- Points awarded
    CASE 
        WHEN f.full_time_home_goals > f.full_time_away_goals THEN 3
        WHEN f.full_time_home_goals = f.full_time_away_goals THEN 1
        ELSE 0
    END as home_points,
    
    CASE 
        WHEN f.full_time_home_goals < f.full_time_away_goals THEN 3
        WHEN f.full_time_home_goals = f.full_time_away_goals THEN 1
        ELSE 0
    END as away_points,
    
    -- Goal difference
    f.full_time_home_goals - f.full_time_away_goals as home_gd,
    f.full_time_away_goals - f.full_time_home_goals as away_gd
    
FROM public.fixtures f
JOIN public.teams ht ON f.home_team_id = ht.id
JOIN public.teams at ON f.away_team_id = at.id
WHERE f.full_time_home_goals IS NOT NULL 
  AND f.full_time_away_goals IS NOT NULL
ORDER BY f.match_date, f.league_id;

-- ----------------------------------------------------------------------------
-- HOME ROLLING VIEW: Home team statistics (n=3 window)
-- ----------------------------------------------------------------------------
CREATE VIEW features.home_rolling AS
WITH home_matches AS (
    SELECT 
        fixture_id,
        home_team_id,
        match_date,
        home_goals,
        away_goals,
        result,
        home_points,
        home_gd,
        
        -- Window functions for rolling stats (n=3)
        ROW_NUMBER() OVER (
            PARTITION BY home_team_id 
            ORDER BY match_date DESC
        ) as match_seq,
        
        -- Rolling counts
        COUNT(*) OVER (
            PARTITION BY home_team_id 
            ORDER BY match_date 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as matches_count_3,
        
        -- Rolling sums
        SUM(home_points) OVER (
            PARTITION BY home_team_id 
            ORDER BY match_date 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as points_sum_3,
        
        SUM(home_goals) OVER (
            PARTITION BY home_team_id 
            ORDER BY match_date 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as goals_for_3,
        
        SUM(away_goals) OVER (
            PARTITION BY home_team_id 
            ORDER BY match_date 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as goals_against_3,
        
        SUM(home_gd) OVER (
            PARTITION BY home_team_id 
            ORDER BY match_date 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as gd_sum_3,
        
        -- Rolling win/loss/draw counts
        SUM(CASE WHEN result = 'H' THEN 1 ELSE 0 END) OVER (
            PARTITION BY home_team_id 
            ORDER BY match_date 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as wins_3,
        
        SUM(CASE WHEN result = 'A' THEN 1 ELSE 0 END) OVER (
            PARTITION BY home_team_id 
            ORDER BY match_date 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as losses_3,
        
        SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END) OVER (
            PARTITION BY home_team_id 
            ORDER BY match_date 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as draws_3
        
    FROM features.match_base
)
SELECT 
    fixture_id,
    home_team_id,
    match_date,
    matches_count_3,
    
    -- Win/Loss/Draw statistics (n=3)
    wins_3 as home_wins_3,
    losses_3 as home_losses_3,
    draws_3 as home_draws_3,
    
    -- Goal statistics (n=3)
    goals_for_3 as home_goals_for_3,
    goals_against_3 as home_goals_against_3,
    gd_sum_3 as home_gd_3,
    
    -- Averages (n=3)
    CASE 
        WHEN matches_count_3 > 0 
        THEN ROUND(goals_for_3::DECIMAL / matches_count_3, 2)
        ELSE 0 
    END as home_avg_goals_for_3,
    
    CASE 
        WHEN matches_count_3 > 0 
        THEN ROUND(goals_against_3::DECIMAL / matches_count_3, 2)
        ELSE 0 
    END as home_avg_goals_against_3,
    
    -- Form points (n=3)
    points_sum_3 as home_points_3,
    
    -- Percentages (n=3)
    CASE 
        WHEN matches_count_3 > 0 
        THEN ROUND(wins_3::DECIMAL * 100.0 / matches_count_3, 1)
        ELSE 0 
    END as home_win_pct_3,
    
    CASE 
        WHEN matches_count_3 > 0 
        THEN ROUND((wins_3 + draws_3)::DECIMAL * 100.0 / matches_count_3, 1)
        ELSE 0 
    END as home_unbeaten_pct_3
    
FROM home_matches
WHERE match_seq > 1  -- Exclude first match (no history)
ORDER BY home_team_id, match_date DESC;

-- ----------------------------------------------------------------------------
-- AWAY ROLLING VIEW: Away team statistics (n=3 window)
-- ----------------------------------------------------------------------------
CREATE VIEW features.away_rolling AS
WITH away_matches AS (
    SELECT 
        fixture_id,
        away_team_id,
        match_date,
        home_goals,
        away_goals,
        result,
        away_points,
        away_gd,
        
        -- Window functions for rolling stats (n=3)
        ROW_NUMBER() OVER (
            PARTITION BY away_team_id 
            ORDER BY match_date DESC
        ) as match_seq,
        
        -- Rolling counts
        COUNT(*) OVER (
            PARTITION BY away_team_id 
            ORDER BY match_date 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as matches_count_3,
        
        -- Rolling sums
        SUM(away_points) OVER (
            PARTITION BY away_team_id 
            ORDER BY match_date 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as points_sum_3,
        
        SUM(away_goals) OVER (
            PARTITION BY away_team_id 
            ORDER BY match_date 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as goals_for_3,
        
        SUM(home_goals) OVER (
            PARTITION BY away_team_id 
            ORDER BY match_date 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as goals_against_3,
        
        SUM(away_gd) OVER (
            PARTITION BY away_team_id 
            ORDER BY match_date 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as gd_sum_3,
        
        -- Rolling win/loss/draw counts
        SUM(CASE WHEN result = 'A' THEN 1 ELSE 0 END) OVER (
            PARTITION BY away_team_id 
            ORDER BY match_date 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as wins_3,
        
        SUM(CASE WHEN result = 'H' THEN 1 ELSE 0 END) OVER (
            PARTITION BY away_team_id 
            ORDER BY match_date 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as losses_3,
        
        SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END) OVER (
            PARTITION BY away_team_id 
            ORDER BY match_date 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as draws_3
        
    FROM features.match_base
)
SELECT 
    fixture_id,
    away_team_id,
    match_date,
    matches_count_3,
    
    -- Win/Loss/Draw statistics (n=3)
    wins_3 as away_wins_3,
    losses_3 as away_losses_3,
    draws_3 as away_draws_3,
    
    -- Goal statistics (n=3)
    goals_for_3 as away_goals_for_3,
    goals_against_3 as away_goals_against_3,
    gd_sum_3 as away_gd_3,
    
    -- Averages (n=3)
    CASE 
        WHEN matches_count_3 > 0 
        THEN ROUND(goals_for_3::DECIMAL / matches_count_3, 2)
        ELSE 0 
    END as away_avg_goals_for_3,
    
    CASE 
        WHEN matches_count_3 > 0 
        THEN ROUND(goals_against_3::DECIMAL / matches_count_3, 2)
        ELSE 0 
    END as away_avg_goals_against_3,
    
    -- Form points (n=3)
    points_sum_3 as away_points_3,
    
    -- Percentages (n=3)
    CASE 
        WHEN matches_count_3 > 0 
        THEN ROUND(wins_3::DECIMAL * 100.0 / matches_count_3, 1)
        ELSE 0 
    END as away_win_pct_3,
    
    CASE 
        WHEN matches_count_3 > 0 
        THEN ROUND((wins_3 + draws_3)::DECIMAL * 100.0 / matches_count_3, 1)
        ELSE 0 
    END as away_unbeaten_pct_3
    
FROM away_matches
WHERE match_seq > 1  -- Exclude first match (no history)
ORDER BY away_team_id, match_date DESC;

-- ----------------------------------------------------------------------------
-- FINAL DERIVED VIEW: Complete feature matrix for modeling
-- ----------------------------------------------------------------------------
CREATE VIEW features.match_derived AS
SELECT 
    -- Core identifiers
    mb.fixture_id,
    mb.internal_id,
    mb.match_date,
    mb.season,
    mb.league_id,
    mb.home_team_id,
    mb.away_team_id,
    mb.home_team_name,
    mb.away_team_name,
    
    -- Match results
    mb.home_goals,
    mb.away_goals,
    mb.result,
    
    -- Home team features (n=3)
    COALESCE(hr.home_wins_3, 0) as home_wins_3,
    COALESCE(hr.home_losses_3, 0) as home_losses_3,
    COALESCE(hr.home_draws_3, 0) as home_draws_3,
    COALESCE(hr.home_goals_for_3, 0) as home_goals_for_3,
    COALESCE(hr.home_goals_against_3, 0) as home_goals_against_3,
    COALESCE(hr.home_gd_3, 0) as home_gd_3,
    COALESCE(hr.home_avg_goals_for_3, 0) as home_avg_goals_for_3,
    COALESCE(hr.home_avg_goals_against_3, 0) as home_avg_goals_against_3,
    COALESCE(hr.home_points_3, 0) as home_points_3,
    COALESCE(hr.home_win_pct_3, 0) as home_win_pct_3,
    COALESCE(hr.home_unbeaten_pct_3, 0) as home_unbeaten_pct_3,
    
    -- Away team features (n=3)
    COALESCE(ar.away_wins_3, 0) as away_wins_3,
    COALESCE(ar.away_losses_3, 0) as away_losses_3,
    COALESCE(ar.away_draws_3, 0) as away_draws_3,
    COALESCE(ar.away_goals_for_3, 0) as away_goals_for_3,
    COALESCE(ar.away_goals_against_3, 0) as away_goals_against_3,
    COALESCE(ar.away_gd_3, 0) as away_gd_3,
    COALESCE(ar.away_avg_goals_for_3, 0) as away_avg_goals_for_3,
    COALESCE(ar.away_avg_goals_against_3, 0) as away_avg_goals_against_3,
    COALESCE(ar.away_points_3, 0) as away_points_3,
    COALESCE(ar.away_win_pct_3, 0) as away_win_pct_3,
    COALESCE(ar.away_unbeaten_pct_3, 0) as away_unbeaten_pct_3,
    
    -- Derived features
    1 as is_home,  -- Constant for home team
    
    -- Form comparison
    COALESCE(hr.home_points_3, 0) - COALESCE(ar.away_points_3, 0) as form_points_diff_3,
    
    -- Goal difference comparison
    COALESCE(hr.home_gd_3, 0) - COALESCE(ar.away_gd_3, 0) as form_gd_diff_3,
    
    -- Win percentage comparison
    COALESCE(hr.home_win_pct_3, 0) - COALESCE(ar.away_win_pct_3, 0) as form_win_pct_diff_3,
    
    -- Match importance (end of season)
    CASE 
        WHEN EXTRACT(MONTH FROM mb.match_date) IN (4, 5) THEN 1
        ELSE 0 
    END as is_end_of_season,
    
    -- Recent match indicator
    CASE 
        WHEN mb.match_date >= CURRENT_DATE - INTERVAL '7 days' THEN 1
        ELSE 0 
    END as is_recent
    
FROM features.match_base mb
LEFT JOIN features.home_rolling hr ON mb.fixture_id = hr.fixture_id
LEFT JOIN features.away_rolling ar ON mb.fixture_id = ar.fixture_id
ORDER BY mb.match_date DESC, mb.league_id, mb.home_team_id;