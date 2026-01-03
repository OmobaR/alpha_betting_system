# verify_phase1.py
import sqlite3
import pandas as pd
from pathlib import Path
import json

print("=" * 60)
print("PHASE 1 VERIFICATION REPORT")
print("=" * 60)

# Check database
db_path = "data/football_phase1.db"
if Path(db_path).exists():
    conn = sqlite3.connect(db_path)
    
    # Get table info
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"✅ Database: {db_path}")
    print(f"   Tables: {', '.join(tables)}")
    print()
    
    for table in tables:
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        print(f"{table.upper()}:")
        print(f"  Records: {len(df)}")
        print(f"  Columns: {list(df.columns)}")
        if not df.empty:
            print(f"  First record ID: {df.iloc[0][df.columns[0]]}")
        print()
    
    conn.close()
else:
    print(f"❌ Database not found: {db_path}")

# Check CSV files
csv_files = list(Path("data").glob("fixtures_*.csv"))
if csv_files:
    print(f"✅ CSV Files: {len(csv_files)} found")
    for csv in csv_files:
        df = pd.read_csv(csv)
        print(f"  {csv.name}: {len(df)} rows")
else:
    print("❌ No CSV files found")

print("=" * 60)
if Path(db_path).exists() and csv_files:
    print("🎉 PHASE 1 SUCCESSFULLY COMPLETED!")
    print("You can now proceed to Phase 2.")
else:
    print("⚠️  Some components missing")
print("=" * 60)
