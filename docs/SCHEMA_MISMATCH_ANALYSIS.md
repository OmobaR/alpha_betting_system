# CRITICAL: Schema Mismatch Analysis
**Date**: [Current Date]  
**Analyst**: TA_2 (Debugging Specialist)  
**Priority**: HIGH - Blocks Integration Bridge

## 🔍 Discovery
Our Phase 1 `football_final.db` has a **FLATTENED** schema (2 tables), while the integration bridge expected a **NORMALIZED** schema (4+ tables with joins).

## 📊 Actual Schema vs Expected Schema

### ✅ ACTUAL SCHEMA (What we HAVE)
**Table: `fixtures`** - Contains ALL match data
- `home_team` (VARCHAR) - Team name as string
- `away_team` (VARCHAR) - Team name as string  
- `match_date` (DATETIME) - Game date/time
- `home_score` (INTEGER) - Final home goals
- `away_score` (INTEGER) - Final away goals
- `league` (VARCHAR) - League code
- `season` (INTEGER) - Season year
- `status` (VARCHAR) - Match status

### ❌ EXPECTED SCHEMA (What bridge wanted)
**Normalized structure requiring JOINS:**
- `teams` table with team details
- `fixtures` table with only team IDs
- `odds_snapshots` table with betting odds
- Multiple joins needed: `fixtures` → `teams` ×2 → `odds_snapshots`

## 🚨 Critical Missing Data
1. **NO ODDS DATA**: No `B365H`, `B365D`, `B365A` columns (essential for betting predictions)
2. **NO SEPARATE TEAMS TABLE**: Team names are strings, not foreign keys
3. **LIMITED HISTORICAL DATA**: Only ~45 matches in database

## 🔧 Immediate Fixes Applied
1. **Debug Dashboard**: Updated query to use actual schema
2. **Bridge.py**: Must be updated similarly (see below)

## 📋 Required Bridge Modifications
The `src/integration/bridge.py` needs these changes:

```python
# OLD (Broken) - Expected normalized schema
query = """
SELECT t1.full_name AS home_team, f.kickoff_time AS date,
       f.home_score AS FTHG, f.away_score AS FTAG,
       o.home_odds AS B365H
FROM fixtures f
JOIN teams t1 ON f.home_team_id = t1.id
JOIN teams t2 ON f.away_team_id = t2.id
JOIN odds_snapshots o ON f.id = o.fixture_id
"""

# NEW (Working) - Uses actual flattened schema
query = """
SELECT 
    home_team,
    away_team, 
    match_date AS date,
    home_score AS FTHG,
    away_score AS FTAG,
    -- NOTE: Odds not available in current DB
    NULL AS B365H,
    NULL AS B365D, 
    NULL AS B365A,
    league,
    season
FROM fixtures
WHERE home_score IS NOT NULL 
  AND away_score IS NOT NULL
"""