import streamlit as st
import pandas as pd
import sqlite3
import os
import matplotlib.pyplot as plt
from difflib import SequenceMatcher

# Paths (adjust if needed based on repo structure)
SQLITE_DB_PATH = 'data/football_final.db'
ALPHABETTING_SAMPLE_CSV = 'existing_system/data/EnglishPremierLeague.csv'  # Example sample from submodule
DEBUG_REPORT_PATH = 'logs/debug_report.csv'

# Schema mapping from project docs
SCHEMA_MAPPING = {
    'home_team': 'fixtures.home_team',      # Direct from fixtures table
    'away_team': 'fixtures.away_team',
    'date': 'fixtures.match_date',
    'FTHG': 'fixtures.home_score',
    'FTAG': 'fixtures.away_score',
    'B365H': 'NOT IN CURRENT DB - NEED ODDS PIPELINE',
    # Additional available fields
    'league': 'fixtures.league',
    'season': 'fixtures.season',
    'status': 'fixtures.status'
}

@st.cache_data
def load_sqlite_data(db_path):
    """Load data from SQLite and transform to DataFrame"""
    if not os.path.exists(db_path):
        st.error(f"SQLite DB not found at {db_path}")
        return pd.DataFrame()
    
    conn = sqlite3.connect(db_path)
    
    # FIXED QUERY: Removed restrictive WHERE clause
    query = """
    SELECT 
        home_team,
        away_team,
        match_date AS date,
        home_score AS FTHG,
        away_score AS FTAG,
        NULL AS B365H,  -- Odds placeholder
        league,
        season,
        status
    FROM fixtures
    -- WHERE home_score IS NOT NULL AND away_score IS NOT NULL  <-- REMOVED
    ORDER BY match_date DESC
    LIMIT 100
    """
    
    try:
        df = pd.read_sql_query(query, conn)
        # Format date
        if not df.empty and 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        st.success(f"✅ Loaded {len(df)} records from ACTUAL schema.")
    except Exception as e:
        st.error(f"❌ Query failed: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()
    
    return df

@st.cache_data
def load_alphabetting_sample(csv_path):
    """Load sample CSV from AlphaBetting submodule with flexible column handling"""
    if not os.path.exists(csv_path):
        st.error(f"AlphaBetting sample CSV not found at {csv_path}")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(csv_path)
        
        # Show what columns are actually available for debugging
        st.sidebar.write("📋 Sample CSV Columns:", df.columns.tolist())
        
        # Define flexible column mapping (common variants)
        column_mapping = {
            'home_team': ['HomeTeam', 'Home', 'home_team', 'team_home'],
            'away_team': ['AwayTeam', 'Away', 'away_team', 'team_away'],
            'date': ['Date', 'date', 'MatchDate', 'match_date'],
            'FTHG': ['FTHG', 'home_score', 'HomeGoals', 'HG'],
            'FTAG': ['FTAG', 'away_score', 'AwayGoals', 'AG'],
            'B365H': ['B365H', 'home_odds', 'OddsH', 'H']
        }
        
        # Find and rename columns
        renamed_cols = {}
        for target_col, possible_sources in column_mapping.items():
            for source_col in possible_sources:
                if source_col in df.columns:
                    renamed_cols[source_col] = target_col
                    break  # Use first match
        
        if not renamed_cols:
            st.error("No recognizable columns found in sample CSV")
            return pd.DataFrame()
        
        # Select and rename
        df = df[list(renamed_cols.keys())].copy()
        df.rename(columns=renamed_cols, inplace=True)
        
        return df
        
    except Exception as e:
        st.error(f"Failed to load sample CSV: {e}")
        return pd.DataFrame()

def compare_dataframes(df_our, df_sample):
    """Compare DataFrames and highlight discrepancies"""
    discrepancies = {}
    
    # Column mismatches
    our_cols = set(df_our.columns)
    sample_cols = set(df_sample.columns)
    missing_in_our = sample_cols - our_cols
    extra_in_our = our_cols - sample_cols
    if missing_in_our:
        discrepancies['missing_columns'] = list(missing_in_our)
    if extra_in_our:
        discrepancies['extra_columns'] = list(extra_in_our)
    
    # Data type mismatches
    common_cols = our_cols & sample_cols
    for col in common_cols:
        if df_our[col].dtype != df_sample[col].dtype:
            discrepancies.setdefault('type_mismatches', []).append(
                f"{col}: our={df_our[col].dtype}, sample={df_sample[col].dtype}"
            )
    
    # Value similarities (sample check)
    if not df_our.empty and not df_sample.empty:
        sample_row = df_sample.iloc[0]
        our_row = df_our.iloc[0]
        for col in common_cols:
            similarity = SequenceMatcher(None, str(our_row[col]), str(sample_row[col])).ratio()
            if similarity < 0.8:
                discrepancies.setdefault('value_discrepancies', []).append(
                    f"{col}: low similarity ({similarity:.2f})"
                )
    
    return discrepancies

def visualize_comparison(df_our, df_sample):
    """Visualize data distributions"""
    fig, ax = plt.subplots()
    if 'FTHG' in df_our.columns and 'FTHG' in df_sample.columns:
        df_our['FTHG'].hist(ax=ax, alpha=0.5, label='Our Data')
        df_sample['FTHG'].hist(ax=ax, alpha=0.5, label='AlphaBetting Sample')
        ax.legend()
        ax.set_title('Home Goals Distribution Comparison')
    return fig

def export_report(discrepancies, df_our, df_sample):
    """Export debug report"""
    report_df = pd.DataFrame({
        'Category': list(discrepancies.keys()),
        'Details': [', '.join(v) if isinstance(v, list) else v for v in discrepancies.values()]
    })
    report_df.to_csv(DEBUG_REPORT_PATH, index=False)
    return DEBUG_REPORT_PATH

# Streamlit Dashboard
st.title("AlphaBetting Integration Debugging Dashboard")

# Step 1: Load Data
st.header("Step 1: Data Loading")
df_our = load_sqlite_data(SQLITE_DB_PATH)
df_sample = load_alphabetting_sample(ALPHABETTING_SAMPLE_CSV)

if not df_our.empty:
    st.subheader("Our Transformed Data Preview")
    st.dataframe(df_our.head())
else:
    st.warning("No data loaded from SQLite.")

if not df_sample.empty:
    st.subheader("AlphaBetting Sample Preview")
    st.dataframe(df_sample.head())
else:
    st.warning("No sample data from AlphaBetting.")

# Step 2: Comparison
st.header("Step 2: Data Comparison")
if not df_our.empty and not df_sample.empty:
    discrepancies = compare_dataframes(df_our, df_sample)
    if discrepancies:
        st.subheader("Discrepancies Found")
        for cat, details in discrepancies.items():
            st.write(f"**{cat.capitalize()}:** {details}")
    else:
        st.success("No discrepancies found!")
else:
    st.error("Cannot compare - data missing.")

# Step 3: Visualization
st.header("Step 3: Visual Data Flow")
if not df_our.empty and not df_sample.empty:
    fig = visualize_comparison(df_our, df_sample)
    st.pyplot(fig)

# Step 4: Export Report
st.header("Step 4: Export Debug Report")
if st.button("Generate and Export Report"):
    if not df_our.empty and not df_sample.empty:
        report_path = export_report(discrepancies, df_our, df_sample)
        st.success(f"Report exported to {report_path}")
        st.download_button("Download Report", data=open(report_path, 'rb'), file_name='debug_report.csv')
    else:
        st.error("Data required for report.")