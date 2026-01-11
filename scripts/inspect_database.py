import sqlite3
import sys
import os

def main():
    # Define the path to your SQLite database
    db_path = 'data/football_final.db'
    
    if not os.path.exists(db_path):
        print(f"❌ ERROR: Database file not found at {db_path}")
        print("Please check the path or ensure the Git LFS files are pulled.")
        sys.exit(1)
    
    print(f"🔍 Inspecting database: {db_path}\n")
    print("=" * 50)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. LIST ALL TABLES
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = cursor.fetchall()
    
    print(f"Found {len(tables)} tables:\n")
    
    for table_info in tables:
        table_name = table_info[0]
        print(f"📁 TABLE: '{table_name}'")
        
        # 2. LIST COLUMNS FOR EACH TABLE
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        # column info: (id, name, type, notnull, default_value, primary_key)
        for col in columns:
            col_name, col_type = col[1], col[2]
            print(f"    ├── {col_name} ({col_type})")
        
        # 3. (Optional) Show row count for context
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"    └── Rows: ~{count}")
        except:
            print(f"    └── Could not count rows")
        print()
    
    # 4. Check for views or indexes
    cursor.execute("SELECT name, type FROM sqlite_master WHERE type IN ('view', 'index');")
    other_objects = cursor.fetchall()
    if other_objects:
        print("Other objects (views, indexes):")
        for obj_name, obj_type in other_objects:
            print(f"  - {obj_name} ({obj_type})")
    
    conn.close()
    print("=" * 50)
    print("✅ Inspection complete.")

if __name__ == "__main__":
    main()