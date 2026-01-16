"""
Pipeline Checkpoint Management
"""
import logging
from datetime import datetime
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class CheckpointManager:
    """Manage ETL pipeline checkpoints for idempotency"""
    
    def __init__(self, db_loader):
        self.db_loader = db_loader
        self.current_checkpoint = None
    
    def start_pipeline(self, pipeline_name: str, source_system: str, 
                      league_external_id: str) -> bool:
        """
        Start a pipeline run and create checkpoint
        
        Returns:
            True if pipeline should proceed, False if already processed
        """
        query = """
            INSERT INTO monitoring.pipeline_checkpoints (
                pipeline_name, source_system, league_external_id,
                last_successful_run, watermark_timestamp, records_processed,
                is_active, created_at, updated_at
            ) VALUES (%s, %s, %s, NULL, NULL, 0, TRUE, %s, %s)
            ON CONFLICT (pipeline_name, source_system, league_external_id) 
            DO UPDATE SET
                is_active = TRUE,
                updated_at = %s
            RETURNING checkpoint_id, last_successful_run
        """
        
        try:
            self.db_loader.cursor.execute(query, (
                pipeline_name,
                source_system,
                league_external_id,
                datetime.now(),
                datetime.now(),
                datetime.now()
            ))
            
            result = self.db_loader.cursor.fetchone()
            self.current_checkpoint = {
                'checkpoint_id': result[0],
                'last_successful_run': result[1],
                'pipeline_name': pipeline_name,
                'source_system': source_system,
                'league_external_id': league_external_id
            }
            
            self.db_loader.connection.commit()
            
            # If last_successful_run is recent, we might skip
            if result[1] and (datetime.now() - result[1]).days < 1:
                logger.info(f"Pipeline {pipeline_name} for {league_external_id} was run recently")
                return False
            
            logger.info(f"Started pipeline {pipeline_name} for {league_external_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting pipeline: {e}")
            self.db_loader.connection.rollback()
            return False
    
    def update_checkpoint(self, records_processed: int, 
                         watermark_timestamp: Optional[datetime] = None,
                         additional_info: Optional[Dict] = None) -> bool:
        """
        Update checkpoint with progress
        
        Args:
            records_processed: Number of records processed in this batch
            watermark_timestamp: Last processed timestamp for incremental updates
            additional_info: Additional metadata
        """
        if not self.current_checkpoint:
            logger.error("No active checkpoint to update")
            return False
        
        query = """
            UPDATE monitoring.pipeline_checkpoints 
            SET 
                last_successful_run = %s,
                watermark_timestamp = COALESCE(%s, watermark_timestamp),
                records_processed = records_processed + %s,
                additional_info = COALESCE(%s::jsonb, additional_info),
                updated_at = %s
            WHERE checkpoint_id = %s
        """
        
        try:
            self.db_loader.cursor.execute(query, (
                datetime.now(),
                watermark_timestamp,
                records_processed,
                Json(additional_info) if additional_info else None,
                datetime.now(),
                self.current_checkpoint['checkpoint_id']
            ))
            
            self.db_loader.connection.commit()
            logger.debug(f"Updated checkpoint: {records_processed} records processed")
            return True
            
        except Exception as e:
            logger.error(f"Error updating checkpoint: {e}")
            self.db_loader.connection.rollback()
            return False
    
    def complete_pipeline(self, success: bool = True, 
                         error_message: Optional[str] = None) -> bool:
        """
        Complete pipeline run
        
        Args:
            success: Whether pipeline completed successfully
            error_message: Error message if pipeline failed
        """
        if not self.current_checkpoint:
            logger.error("No active checkpoint to complete")
            return False
        
        query = """
            UPDATE monitoring.pipeline_checkpoints 
            SET 
                is_active = %s,
                last_error = %s,
                retry_count = CASE WHEN %s = FALSE THEN retry_count + 1 ELSE retry_count END,
                updated_at = %s
            WHERE checkpoint_id = %s
        """
        
        try:
            self.db_loader.cursor.execute(query, (
                False,
                error_message,
                success,
                datetime.now(),
                self.current_checkpoint['checkpoint_id']
            ))
            
            self.db_loader.connection.commit()
            
            status = "successfully" if success else "with errors"
            logger.info(f"Completed pipeline {status}: {self.current_checkpoint['pipeline_name']}")
            
            self.current_checkpoint = None
            return True
            
        except Exception as e:
            logger.error(f"Error completing pipeline: {e}")
            self.db_loader.connection.rollback()
            return False
    
    def get_pipeline_status(self, pipeline_name: str, 
                           source_system: str, 
                           league_external_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a pipeline
        """
        query = """
            SELECT 
                checkpoint_id, last_successful_run, watermark_timestamp,
                records_processed, success_rate, last_error, retry_count,
                is_active, created_at, updated_at, additional_info
            FROM monitoring.pipeline_checkpoints
            WHERE pipeline_name = %s 
                AND source_system = %s 
                AND league_external_id = %s
        """
        
        try:
            self.db_loader.cursor.execute(query, (
                pipeline_name, source_system, league_external_id
            ))
            
            result = self.db_loader.cursor.fetchone()
            if not result:
                return None
            
            columns = ['checkpoint_id', 'last_successful_run', 'watermark_timestamp',
                      'records_processed', 'success_rate', 'last_error', 'retry_count',
                      'is_active', 'created_at', 'updated_at', 'additional_info']
            
            return dict(zip(columns, result))
            
        except Exception as e:
            logger.error(f"Error getting pipeline status: {e}")
            return None
    
    def should_retry(self, pipeline_name: str, 
                    source_system: str, 
                    league_external_id: str,
                    max_retries: int = 3) -> bool:
        """
        Check if pipeline should be retried based on retry count
        """
        status = self.get_pipeline_status(pipeline_name, source_system, league_external_id)
        if not status:
            return True
        
        return status['retry_count'] < max_retries
