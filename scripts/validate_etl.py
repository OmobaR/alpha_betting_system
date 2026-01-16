#!/usr/bin/env python3
"""
Validate ETL Results
"""
import sys
import psycopg2
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from etl.config import ConfigManager

def validate_etl():
    """Validate ETL results"""
    print("=" * 60)
    print("VALIDATING ETL RESULTS")
    print("=" * 60)
    
    config = ConfigManager().config
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=config['database'].host,
            port=config['database'].port,
            database=config['database'].name,
            user=config['database'].user,
            password=config['database'].password or 'betting_password'
        )
        cursor = conn.cursor()
        
        print("‚úÖ Connected to database")
        
        # Run validation queries
        validation_queries = [
            ("Total fixtures", "SELECT COUNT(*) FROM raw.fixtures"),
            ("Total teams", "SELECT COUNT(*) FROM raw.teams"),
            ("Total leagues", "SELECT COUNT(*) FROM raw.leagues"),
            ("Total odds snapshots", "SELECT COUNT(*) FROM raw.odds_snapshots"),
            ("Feature view matches", "SELECT COUNT(*) FROM features.match_derived"),
            ("Recent fixtures", "SELECT COUNT(*) FROM raw.fixtures WHERE match_date >= '2023-01-01'"),
            ("Fixtures with odds", """
                SELECT COUNT(DISTINCT f.fixture_id) 
                FROM raw.fixtures f 
                JOIN raw.odds_snapshots o ON f.fixture_id = o.fixture_id
            """),
            ("Pipeline checkpoints", "SELECT COUNT(*) FROM monitoring.pipeline_checkpoints"),
            ("ETL statistics", "SELECT COUNT(*) FROM monitoring.etl_statistics"),
        ]
        
        results = {}
        for name, query in validation_queries:
            cursor.execute(query)
            count = cursor.fetchone()[0]
            results[name] = count
            print(f"  {name}: {count}")
        
        # Check data quality
        print("\nÌ≥ä DATA QUALITY CHECKS:")
        
        # Check for NULL goals
        cursor.execute("""
            SELECT COUNT(*) FROM raw.fixtures 
            WHERE home_goals IS NULL OR away_goals IS NULL
        """)
        null_goals = cursor.fetchone()[0]
        print(f"  Fixtures with NULL goals: {null_goals}")
        
        # Check for duplicate fixtures
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT external_id, source_system, COUNT(*)
                FROM raw.fixtures 
                GROUP BY external_id, source_system 
                HAVING COUNT(*) > 1
            ) as duplicates
        """)
        duplicates = cursor.fetchone()[0]
        print(f"  Duplicate fixtures: {duplicates}")
        
        # Check feature view completeness
        if results['Feature view matches'] > 0:
            completeness = (results['Feature view matches'] / results['Total fixtures']) * 100
            print(f"  Feature view completeness: {completeness:.1f}%")
        
        print("\n" + "=" * 60)
        print("VALIDATION COMPLETE")
        print("=" * 60)
        
        if null_goals == 0 and duplicates == 0:
            print("‚úÖ All checks passed!")
        else:
            print("‚ö†Ô∏è  Some issues found (see above)")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"‚ùå Validation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    validate_etl()
