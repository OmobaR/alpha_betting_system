#!/usr/bin/env python3
"""
Run full historical ETL for all leagues and seasons
"""
import sys
import os
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.abspath('src'))

# Setup logging
def setup_logging():
    """Configure logging for ETL pipeline"""
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(logs_dir, f"etl_full_{timestamp}.log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def main():
    logger = setup_logging()
    
    try:
        logger.info("=" * 60)
        logger.info("ALPHABETTING HISTORICAL DATA ETL PIPELINE")
        logger.info("=" * 60)
        logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")
        
        from etl.pipeline import ETLPipeline
        
        logger.info("Initializing ETL Pipeline...")
        pipeline = ETLPipeline()
        
        logger.info("Starting full historical ETL...")
        logger.info("Leagues: EPL, LaLiga, Bundesliga, SerieA, Ligue1")
        logger.info("Seasons: 2000-01 to 2023-24 (24 seasons)")
        logger.info("Expected: 120 files, ~45,600 fixtures")
        logger.info("")
        
        result = pipeline.run()
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("FULL ETL COMPLETE!")
        logger.info("=" * 60)
        logger.info(f"Files downloaded: {result.get('downloaded_files', 0)}")
        logger.info(f"Files processed: {result.get('processed_files', 0)}")
        logger.info(f"Fixtures loaded: {result.get('inserted_fixtures', 0):,}")
        logger.info(f"Teams loaded: {result.get('inserted_teams', 0):,}")
        logger.info(f"Odds records: {result.get('inserted_odds', 0):,}")
        
        if 'duration_seconds' in result:
            duration = result['duration_seconds']
            logger.info(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        
        # Print to console as well
        print("\n" + "=" * 60)
        print("FULL ETL COMPLETE!")
        print("=" * 60)
        print(f"Files downloaded: {result.get('downloaded_files', 0)}")
        print(f"Files processed: {result.get('processed_files', 0)}")
        print(f"Fixtures loaded: {result.get('inserted_fixtures', 0):,}")
        print(f"Teams loaded: {result.get('inserted_teams', 0):,}")
        print(f"Odds records: {result.get('inserted_odds', 0):,}")
        
        if 'duration_seconds' in result:
            duration = result['duration_seconds']
            print(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"ETL failed: {e}", exc_info=True)
        print(f"\n❌ ETL failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
