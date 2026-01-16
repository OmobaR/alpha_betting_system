from datetime import datetime
#!/usr/bin/env python3
"""
AlphaBetting ETL Pipeline - Main Entry Point
"""
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from etl.pipeline import ETLPipeline
from etl.config import ConfigManager

def setup_logging():
    """Setup comprehensive logging"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"etl_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Suppress noisy logs
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('psycopg2').setLevel(logging.WARNING)

def main():
    """Main entry point for ETL pipeline"""
    from datetime import datetime
    
    print("=" * 60)
    print("ALPHABETTING HISTORICAL DATA ETL PIPELINE")
    print("=" * 60)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = ConfigManager().config
        
        # Show configuration
        print("CONFIGURATION:")
        print(f"  Database: {config['database'].host}:{config['database'].port}")
        print(f"  Raw Data Path: {config['etl'].raw_data_path}")
        print(f"  Leagues: {', '.join(config['etl'].leagues.keys())}")
        print(f"  Seasons: {config['etl'].seasons[0]} to {config['etl'].seasons[-1]}")
        print()
        
        # Confirm with user
        print("This will:")
        print("  1. Download CSV files from football-data.co.uk")
        print("  2. Parse and load match data into PostgreSQL")
        print("  3. Extract and load betting odds")
        print("  4. Update feature views automatically")
        print()
        
        response = input("Continue? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("ETL cancelled.")
            return
        
        # Run ETL pipeline
        print("\n" + "=" * 60)
        print("STARTING ETL PROCESS...")
        print("=" * 60)
        
        pipeline = ETLPipeline(config)
        stats = pipeline.run()
        
        # Show results
        print("\n" + "=" * 60)
        print("ETL RESULTS")
        print("=" * 60)
        print(f"Duration: {stats.get('duration', 'N/A')} seconds")
        print(f"Files processed: {stats.get('processed_files', 0)}/{stats.get('total_files', 0)}")
        print(f"Matches loaded: {stats.get('loaded_matches', 0)}")
        print(f"Odds snapshots loaded: {stats.get('loaded_odds', 0)}")
        print(f"Failed files: {stats.get('failed_files', 0)}")
        
        # Validate results
        print("\n" + "=" * 60)
        print("VALIDATING RESULTS...")
        print("=" * 60)
        
        validation = pipeline.validate_etl_results()
        if 'error' in validation:
            print(f"Validation error: {validation['error']}")
        else:
            print(f"Fixtures in database: {validation.get('fixtures', 0)}")
            print(f"Teams in database: {validation.get('teams', 0)}")
            print(f"Leagues in database: {validation.get('leagues', 0)}")
            print(f"Odds snapshots: {validation.get('odds_snapshots', 0)}")
            print(f"Feature view matches: {validation.get('feature_matches', 0)}")
        
        print("\n" + "=" * 60)
        print(f"ETL COMPLETE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Next steps
        print("\nNEXT STEPS:")
        print("  1. Check feature views: SELECT * FROM features.match_derived LIMIT 10")
        print("  2. Test Dixon-Coles feature calculation")
        print("  3. Run model training with historical data")
        
    except KeyboardInterrupt:
        print("\n\nETL interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"ETL pipeline failed: {e}", exc_info=True)
        print(f"\nERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
