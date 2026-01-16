#!/usr/bin/env python3
"""
VERIFY PHASE 3 IMPLEMENTATION
Check database and model functionality
"""

import psycopg2
import sys

def verify_database():
    """Verify database connection and schema"""
    print("=" * 70)
    print("PHASE 3 VERIFICATION")
    print("=" * 70)
    
    checks_passed = 0
    total_checks = 4
    
    try:
        # Check 1: Database connection
        print("\n[1/4] Testing database connection...")
        conn = psycopg2.connect(
            host='localhost',
            port=5433,
            database='football_betting',
            user='betting_user',
            password='betting_password'
        )
        cursor = conn.cursor()
        print("   PASS: Database connection successful")
        checks_passed += 1
        
        # Check 2: Raw fixtures table exists
        print("\n[2/4] Checking raw fixtures table...")
        cursor.execute("SELECT COUNT(*) FROM raw.fixtures;")
        fixture_count = cursor.fetchone()[0]
        if fixture_count > 0:
            print(f"   PASS: {fixture_count:,} fixtures found")
            checks_passed += 1
        else:
            print("   FAIL: No fixtures found")
        
        # Check 3: Features schema exists
        print("\n[3/4] Checking features schema...")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.schemata 
                WHERE schema_name = 'features'
            );
        """)
        features_exists = cursor.fetchone()[0]
        if features_exists:
            print("   PASS: Features schema exists")
            checks_passed += 1
        else:
            print("   FAIL: Features schema missing")
        
        # Check 4: Match features table exists
        print("\n[4/4] Checking match_features table...")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'features' 
                AND table_name = 'match_features'
            );
        """)
        table_exists = cursor.fetchone()[0]
        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM features.match_features;")
            pred_count = cursor.fetchone()[0]
            print(f"   PASS: match_features table exists with {pred_count} predictions")
            checks_passed += 1
        else:
            print("   FAIL: match_features table missing")
        
        # Show sample data if available
        if table_exists:
            cursor.execute("SELECT * FROM features.match_features LIMIT 3;")
            samples = cursor.fetchall()
            if samples:
                print("\nSample predictions:")
                for sample in samples:
                    print(f"   Fixture: {sample[0]}, Home: {sample[1]:.3f}, Draw: {sample[2]:.3f}, Away: {sample[3]:.3f}")
        
        # Clean up
        cursor.close()
        conn.close()
        
        # Final result
        print("\n" + "=" * 70)
        print(f"VERIFICATION RESULT: {checks_passed}/{total_checks} checks passed")
        
        if checks_passed == total_checks:
            print("STATUS: Phase 3 READY")
            return True
        else:
            print("STATUS: Phase 3 needs setup")
            return False
            
    except Exception as e:
        print(f"\nERROR: {e}")
        return False

def show_next_steps():
    """Show next steps based on verification"""
    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("\n1. Run Phase 3 implementation:")
    print("   python phase3_dixon_coles.py")
    print("\n2. If successful, proceed to Week 2:")
    print("   - Implement feature calculator engine")
    print("   - Add more sophisticated features")
    print("   - Scale training to 10,000+ matches")
    print("\n3. Database queries for verification:")
    print("   SELECT COUNT(*) FROM features.match_features;")
    print("   SELECT * FROM features.match_features LIMIT 5;")
    print("\n" + "=" * 70)

if __name__ == "__main__":
    success = verify_database()
    if success:
        print("\nAll systems ready for Phase 3 execution!")
    else:
        print("\nSome issues need to be resolved before proceeding.")
    
    show_next_steps()
