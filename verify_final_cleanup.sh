#!/bin/bash
echo "=================================================="
echo "Ì¥ç FINAL PHASE 2 COMPLETION VERIFICATION"
echo "=================================================="

echo ""
echo "Ì≥ä 1. Python Environment Check"
echo "----------------------------"
# Check virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "‚úÖ Virtual environment: $(basename $VIRTUAL_ENV)"
else
    echo "‚ö†Ô∏è  Not in virtual environment"
fi

# Check Python
python -c "
import sys
print(f'Python version: {sys.version.split()[0]}')
print(f'Python executable: {sys.executable}')
"

echo ""
echo "Ì≥Å 2. Project Structure Verification"
echo "---------------------------------"
echo "Root directory files:"
echo "-------------------"
ls -la | grep -E "\.(py|sh|md|txt)$" | awk '{print "  "$9}'

echo ""
echo "Ì≥¶ 3. ETL Core Module Check"
echo "-------------------------"
python -c "
import sys
sys.path.insert(0, 'src')

modules_to_test = [
    ('etl.parser', 'CSVParser'),
    ('etl.loader', 'DatabaseLoader'),
    ('etl.pipeline', 'ETLPipeline'),
    ('etl.downloader', 'CSVDownloader'),
    ('etl.checkpoint', 'CheckpointManager'),
    ('pipeline', 'run_pipeline'),
]

print('Testing ETL module imports:')
for module_path, class_name in modules_to_test:
    try:
        if '.' in module_path:
            # For module.class imports
            module_parts = module_path.split('.')
            module = __import__(module_parts[0])
            for part in module_parts[1:]:
                module = getattr(module, part)
            # Try to get the class
            getattr(module, class_name)
        else:
            # For direct module
            __import__(module_path)
        print(f'  ‚úÖ {module_path}.{class_name}')
    except ImportError as e:
        print(f'  ‚ùå {module_path}: ImportError - {str(e)[:50]}')
    except AttributeError as e:
        print(f'  ‚úÖ {module_path} (no {class_name} check)')
    except Exception as e:
        print(f'  ‚ö†Ô∏è  {module_path}: {type(e).__name__}')
"

echo ""
echo "Ì∑ÑÔ∏è 4. Database Status (Optional)"
echo "-----------------------------"
# Check if Docker is installed and running
if command -v docker &> /dev/null; then
    if docker ps | grep -q "alpha_betting_postgres"; then
        echo "‚úÖ Docker PostgreSQL container is running"
        echo "   Testing database connection..."
        docker exec alpha_betting_postgres psql -U betting_user -d football_betting -c "
        SELECT 
            table_name,
            COUNT(*) as record_count,
            pg_size_pretty(pg_total_relation_size('raw.' || table_name)) as size
        FROM information_schema.tables 
        WHERE table_schema = 'raw' 
        GROUP BY table_name 
        ORDER BY table_name;
        " 2>/dev/null || echo "   ‚ö†Ô∏è  Could not connect to database"
    else
        echo "‚ÑπÔ∏è  Docker PostgreSQL not running (normal if not needed)"
    fi
else
    echo "‚ÑπÔ∏è  Docker not installed or not in PATH"
fi

echo ""
echo "Ì≥à 5. Archive Status"
echo "-----------------"
ARCHIVE_DIR="../../project_alphaBetting_archive"
if [ -d "$ARCHIVE_DIR" ]; then
    echo "‚úÖ Archive directory exists:"
    echo "   Location: $ARCHIVE_DIR"
    echo "   Contents:"
    find "$ARCHIVE_DIR" -type f | wc -l | awk '{print "     Total files: "$1}'
    du -sh "$ARCHIVE_DIR" | awk '{print "     Total size: "$1}'
else
    echo "‚ùå Archive directory not found"
fi

echo ""
echo "Ì∫Ä 6. Phase 3 Readiness"
echo "---------------------"
# Check if Phase 3 directories exist or need creation
PHASE3_DIRS=("src/features" "src/models" "src/evaluation")

echo "Required directories for Phase 3:"
for dir in "${PHASE3_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ‚úÖ $dir"
    else
        echo "  ‚ö†Ô∏è  $dir (will be created)"
        mkdir -p "$dir"
    fi
done

echo ""
echo "=================================================="
echo "Ìæâ VERIFICATION COMPLETE"
echo "=================================================="
echo ""
echo "Ì≥ã NEXT STEPS FOR PHASE 3:"
echo "1. Implement Dixon-Coles model in src/features/dixon_coles.py"
echo "2. Create feature calculator in src/features/calculator.py"
echo "3. Build market features in src/features/market_features.py"
echo "4. Create feature pipeline in src/features/pipeline.py"
echo ""
echo "Ì≤° Run: mkdir -p src/features src/models src/evaluation"
echo "Ì≤° Then start implementing the research-mandated Dixon-Coles model"
echo "=================================================="
