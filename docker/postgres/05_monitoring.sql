-- ========== MONITORING TABLES ==========

-- Pipeline checkpoints for state management
CREATE TABLE monitoring.pipeline_checkpoints (
    checkpoint_id SERIAL PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    source_system VARCHAR(50) NOT NULL,
    league_external_id INTEGER,
    
    -- State tracking
    last_successful_run TIMESTAMP WITH TIME ZONE,
    last_processed_id BIGINT,
    watermark_timestamp TIMESTAMP WITH TIME ZONE,
    records_processed INTEGER DEFAULT 0,
    
    -- Performance metrics
    avg_processing_time_ms INTEGER,
    success_rate DECIMAL(5,4) DEFAULT 1.0,
    
    -- Error handling
    last_error TEXT,
    retry_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    additional_info JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE (pipeline_name, source_system, league_external_id)
);

-- Model performance tracking (Multi-Class Brier Score)
CREATE TABLE monitoring.model_performance (
    performance_id BIGSERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50),
    fixture_id BIGINT REFERENCES raw.fixtures(fixture_id),
    
    -- Predictions
    predicted_at TIMESTAMP WITH TIME ZONE NOT NULL,
    predicted_home_win DECIMAL(5,4) CHECK (predicted_home_win BETWEEN 0 AND 1),
    predicted_draw DECIMAL(5,4) CHECK (predicted_draw BETWEEN 0 AND 1),
    predicted_away_win DECIMAL(5,4) CHECK (predicted_away_win BETWEEN 0 AND 1),
    
    -- Actual outcome
    actual_result CHAR(1),
    actual_home_goals INTEGER,
    actual_away_goals INTEGER,
    
    -- MULTI-CLASS BRIER SCORE (Research-mandated)
    brier_score DECIMAL(8,6),
    reliability_component DECIMAL(8,6),
    resolution_component DECIMAL(8,6),
    uncertainty_component DECIMAL(8,6),
    
    -- Additional metrics
    log_loss DECIMAL(8,6),
    accuracy BOOLEAN,
    confidence DECIMAL(5,4),
    
    -- Timing
    result_available_at TIMESTAMP WITH TIME ZONE,
    available_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for monitoring queries
    INDEX idx_perf_model_time (model_name, predicted_at),
    INDEX idx_perf_brier (brier_score),
    INDEX idx_perf_accuracy (accuracy)
);

-- Function to calculate Multi-Class Brier Score
CREATE OR REPLACE FUNCTION monitoring.calculate_brier_score(
    predicted_home DECIMAL,
    predicted_draw DECIMAL,
    predicted_away DECIMAL,
    actual_result CHAR
) RETURNS DECIMAL AS $$
DECLARE
    outcome_home DECIMAL := CASE WHEN actual_result = 'H' THEN 1.0 ELSE 0.0 END;
    outcome_draw DECIMAL := CASE WHEN actual_result = 'D' THEN 1.0 ELSE 0.0 END;
    outcome_away DECIMAL := CASE WHEN actual_result = 'A' THEN 1.0 ELSE 0.0 END;
BEGIN
    RETURN 
        POWER(predicted_home - outcome_home, 2) +
        POWER(predicted_draw - outcome_draw, 2) + 
        POWER(predicted_away - outcome_away, 2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- View for monitoring model degradation
CREATE OR REPLACE VIEW monitoring.model_degradation AS
WITH recent_scores AS (
    SELECT 
        model_name,
        brier_score,
        predicted_at,
        AVG(brier_score) OVER (
            PARTITION BY model_name 
            ORDER BY predicted_at 
            ROWS BETWEEN 99 PRECEDING AND CURRENT ROW
        ) as rolling_avg_100
    FROM monitoring.model_performance
    WHERE brier_score IS NOT NULL
    ORDER BY predicted_at DESC
)
SELECT 
    model_name,
    AVG(brier_score) as current_brier,
    MIN(brier_score) as best_brier,
    MAX(brier_score) as worst_brier,
    STDDEV(brier_score) as brier_stddev,
    COUNT(*) as n_predictions,
    CASE 
        WHEN AVG(brier_score) > 0.67 THEN 'CRITICAL'
        WHEN AVG(brier_score) > 0.55 THEN 'WARNING'
        ELSE 'HEALTHY'
    END as status
FROM recent_scores
GROUP BY model_name;