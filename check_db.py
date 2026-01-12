import psycopg2

try:
    conn = psycopg2.connect(
        host='localhost',
        port=5433,
        dbname='football_betting',
        user='betting_user',
        password='betting_password'
    )
    cur = conn.cursor()
    
    print('=' * 50)
    print('Checking Database Structure')
    print('=' * 50)
    
    # Check ALL schemas
    cur.execute("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name")
    print('\nAll schemas:')
    for schema in cur.fetchall():
        print(f'  - {schema[0]}')
    
    # Check ALL tables
    cur.execute("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema') 
        ORDER BY table_schema, table_name
    """)
    
    print('\nTables by schema:')
    current_schema = None
    for schema, table in cur.fetchall():
        if schema != current_schema:
            print(f'\nSchema: {schema}')
            current_schema = schema
        print(f'  - {table}')
    
    # Check TimescaleDB
    print('\n' + '-' * 30)
    try:
        cur.execute("SELECT extname FROM pg_extension WHERE extname = 'timescaledb'")
        result = cur.fetchone()
        if result:
            print('✅ TimescaleDB extension is loaded')
            
            # Check hypertables
            cur.execute("SELECT hypertable_name FROM timescaledb_information.hypertables")
            hypertables = cur.fetchall()
            print(f'Hypertables found: {len(hypertables)}')
            for ht in hypertables:
                print(f'  - {ht[0]}')
        else:
            print('⚠ TimescaleDB extension not found')
    except Exception as e:
        print(f'⚠ Could not check TimescaleDB: {e}')
    
    cur.close()
    conn.close()
    
    print('\n' + '=' * 50)
    print('Database check complete!')
    print('=' * 50)
    
except Exception as e:
    print(f'❌ Error: {e}')
