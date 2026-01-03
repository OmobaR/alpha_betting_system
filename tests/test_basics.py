# simple_phase1.py - Fixed for SQLAlchemy 2.0
import sys
print("=" * 60)
print("PHASE 1: SIMPLE TEST (FIXED FOR SQLALCHEMY 2.0)")
print("=" * 60)

# Test imports
try:
    import requests
    import pandas as pd
    from sqlalchemy import create_engine, text
    from tenacity import retry, stop_after_attempt
    print("✅ All core imports successful!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Create a simple database
engine = create_engine('sqlite:///data/test_phase1.db')

# Create a simple table using text() for raw SQL
with engine.connect() as conn:
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS test_fixtures (
            id INTEGER PRIMARY KEY,
            home_team TEXT,
            away_team TEXT,
            match_date TEXT
        )
    '''))
    conn.commit()
    print("✅ Database table created")

# Insert some test data
with engine.connect() as conn:
    conn.execute(text("INSERT INTO test_fixtures (home_team, away_team, match_date) VALUES ('Arsenal', 'Chelsea', '2024-01-15')"))
    conn.execute(text("INSERT INTO test_fixtures (home_team, away_team, match_date) VALUES ('Liverpool', 'Man City', '2024-01-16')"))
    conn.commit()
    print("✅ Test data inserted")

# Read back data
df = pd.read_sql_query("SELECT * FROM test_fixtures", engine)
print(f"✅ Data retrieved: {len(df)} rows")
print("\nData preview:")
print(df)

# Test retry decorator
@retry(stop=stop_after_attempt(3))
def test_function():
    print("✅ Retry decorator works!")
    return True

test_function()

print("\n" + "=" * 60)
print("🎉 PHASE 1 CORE FUNCTIONALITY VERIFIED!")
print("=" * 60)
print("\nWhat works:")
print("  ✅ Database operations (SQLAlchemy 2.0)")
print("  ✅ Data manipulation (pandas)")
print("  ✅ Retry logic (tenacity)")
print("  ✅ Basic structure")
print("\nYou are ready for Phase 1 implementation!")
