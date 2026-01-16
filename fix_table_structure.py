#!/usr/bin/env python3
"""
FIX TABLE STRUCTURE FOR PHASE 3
Update match_features table to include all Dixon-Coles parameters
"""

import psycopg2
import sys

def fix_table_structure():
    print("=" * 70)
    print("FIXING TABLE STRUCTURE FOR PHASE 3")
    print("=" * 70)
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5433,
            database='football_betting',
            user='betting_user',
            password='betting_password'
        )
        conn.autocommit = True  # Avoid transaction issues
        cursor = conn.cursor()
        
        print("[1/6] Connected to database")
        
        # Check current structure
        print("\n[2/6] Checking current table structure...")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'features' 
            AND table_name = 'match_features'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        print("Current columns:")
        for col in columns:
            print(f"  {col[0]} ({col[1]})")
        
        # Drop existing table
        print("\n[3/6] Dropping existing table...")
        cursor.execute("DROP TABLE IF EXISTS features.match_features;")
        print("Table dropped")
        
        # Create new table with all required columns
        print("\n[4/6] Creating new table with full schema...")
        cursor.execute("""
            CREATE TABLE features.match_features (
                fixture_id VARCHAR(255) PRIMARY KEY,
                dc_home_prob DECIMAL(5,4),
                dc_draw_prob DECIMAL(5,4),
                dc_away_prob DECIMAL(5,4),
                dc_attack_home DECIMAL(8,6),
                dc_attack_away DECIMAL(8,6),
                dc_defense_home DECIMAL(8,6),
                dc_defense_away DECIMAL(8,6),
                dc_rho_parameter DECIMAL(8,6),
                dc_xi_parameter DECIMAL(8,6),
                dc_home_advantage DECIMAL(8,6),
                dc_expected_home_goals DECIMAL(8,6),
                dc_expected_away_goals DECIMAL(8,6),
                calculated_at TIMESTAMP DEFAULT NOW()
            );
        """)
        print("New table created with all columns")
        
        # Verify creation
        print("\n[5/6] Verifying new structure...")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'features' 
            AND table_name = 'match_features'
            ORDER BY ordinal_position;
        """)
        new_columns = cursor.fetchall()
        print(f"New table has {len(new_columns)} columns:")
        for col in new_columns:
            print(f"  {col[0]} ({col[1]})")
        
        # Test insert
        print("\n[6/6] Testing insert...")
        cursor.execute("""
            INSERT INTO features.match_features 
            (fixture_id, dc_home_prob, dc_draw_prob, dc_away_prob,
             dc_attack_home, dc_attack_away, dc_defense_home, dc_defense_away,
             dc_rho_parameter, dc_xi_parameter, dc_home_advantage,
             dc_expected_home_goals, dc_expected_away_goals)
            VALUES ('test_001', 0.45, 0.30, 0.25, 
                    1.2, 0.8, 0.9, 1.1, 
                    -0.13, 0.0065, 0.3, 
                    1.5, 1.2);
        """)
        print("Test insert successful")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        print("TABLE STRUCTURE FIX COMPLETE!")
        print("=" * 70)
        print("\nThe match_features table now has all required columns.")
        print("You can now run phase3_dixon_coles.py again.")
        
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        return False

if __name__ == "__main__":
    success = fix_table_structure()
    sys.exit(0 if success else 1)
