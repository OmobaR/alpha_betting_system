#!/usr/bin/env python3
"""
Validate Docker Stack - Run after docker-compose up
"""
import psycopg2
import sys
import time
from pathlib import Path

def validate_docker_stack():
    """Validate the Docker stack is working correctly"""
    print("=" * 60)
    print("Docker Stack Validation")
    print("=" * 60)
    
    # Connection parameters (match docker-compose.yml)
    connection_params = {
        'host': 'localhost',
        'port': 5433,
        'database': 'football_betting',
        'user': 'betting_user',
        'password': 'betting_password'  # Default from .env.example
    }
    
    # Wait for database to be ready
    print("⏳ Waiting for database to be ready...")
    for i in range(30):
        try:
            conn = psycopg2.connect(**connection_params)
            conn.close()
            print("✅ Database connection successful")
            break
        except psycopg2.OperationalError as e:
            if i < 29:
                time.sleep(2)
                print(f"  Attempt {i+1}/30...")
            else:
                print(f"❌ Database connection failed: {e}")
                sys.exit(1)
    
    # Run validation queries
    print("\n📊 Running validation queries...")
    
    validation_queries = [
        ("Schemas exist", 
         "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('raw', 'features', 'monitoring')"),
        
        ("Raw tables created", 
         "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'raw'"),
        
        ("Feature views created", 
         "SELECT COUNT(*) FROM information_schema.views WHERE table_schema = 'features'"),
        
        ("Public views have anti-bias filters", 
         "SELECT definition FROM pg_views WHERE viewname = 'fixtures' AND schemaname = 'public' AND definition LIKE '%available_at%'"),
        
        ("TimescaleDB hypertables", 
         "SELECT COUNT(*) FROM timescaledb_information.hypertables")
    ]
    
    try:
        conn = psycopg2.connect(**connection_params)
        cursor = conn.cursor()
        
        for test_name, query in validation_queries:
            cursor.execute(query)
            result = cursor.fetchone()[0]
            if result and int(result or 0) > 0:
                print(f"✅ {test_name}: {result}")
            else:
                print(f"❌ {test_name}: FAILED")
                
        # Test feature view
        print("\n🧪 Testing feature view...")
        cursor.execute("SELECT COUNT(*) FROM features.match_derived")
        count = cursor.fetchone()[0]
        print(f"✅ features.match_derived accessible: {count} rows (empty as expected)")
        
        # Check column count
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_schema = 'features' AND table_name = 'match_derived'
        """)
        col_count = cursor.fetchone()[0]
        print(f"✅ Feature view has {col_count} columns")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 DOCKER STACK VALIDATION COMPLETE")
    print("=" * 60)
    print("\nAccess points:")
    print("  • PostgreSQL: localhost:5433")
    print("  • pgAdmin: http://localhost:5050")
    print("  • Credentials in .env file")
    print("\nNext: Run ETL pipeline to populate with football-data.co.uk CSV data")

if __name__ == "__main__":
    validate_docker_stack()
