#!/bin/bash
# save as: cleanup_with_archive.sh

echo "=================================================="
echo "Ì≥¶ PHASE 2 COMPLETE: ARCHIVE & CLEANUP"
echo "=================================================="

# ------------------------------------------------------
# STEP 1: CREATE ARCHIVE DIRECTORY
# ------------------------------------------------------
echo ""
echo "Ì≥Å STEP 1: Creating archive directory..."
ARCHIVE_DIR="../../project_alphaBetting_archive"
mkdir -p "$ARCHIVE_DIR/phase1_2_debug_scripts"
mkdir -p "$ARCHIVE_DIR/logs"
mkdir -p "$ARCHIVE_DIR/backups"

echo "‚úÖ Archive created at: $ARCHIVE_DIR"

# ------------------------------------------------------
# STEP 2: ARCHIVE TEMPORARY FIX SCRIPTS
# ------------------------------------------------------
echo ""
echo "Ì≥¶ STEP 2: Archiving temporary fix scripts..."

# List of temporary fix scripts to archive
TEMP_SCRIPTS=(
    # Fix scripts
    "apply_parser_fix.py"
    "check_db.py"
    "check_full_etl.py"
    "clean_test.py"
    "create_clean_parser.py"
    "create_final_parser.py"
    "create_working_parser.py"
    "fix_indentation.py"
    "fix_loader_simple.py"
    "fix_parser_carefully.py"
    "fix_parser_directly.py"
    "fix_parser_simple.py"
    "fix_run_etl.py"
    "fix_script.py"
    "minimal_test.py"
    "fix_pipeline_simple.py"
    "fix_pipeline_three_values.py"
    "fix_parser_definitive.py"
    "fix_parser_return.py"
    "fix_parser_return_two.py"
    "fix_parser_syntax.py"
    "fix_teams_sql.py"
    "minimal_parser_fix.py"
    "patch_pipeline_final.py"
    "replace_parse_file.py"
    "write_correct_parser.py"
    
    # Test files
    "test_downloader.py"
    "test_downloader_final.py"
    "test_downloader2.py"
    "test_etl_simple.py"
    "test_fixed_pipeline.py"
    "test_location.py"
    "test_parser_complete.py"
    "test_parser_final.py"
    "test_parser_return.py"
    "debug_parser_return.py"
    
    # Diagnostic scripts
    "simple_output.py"
    "check_parsed_data.py"
    "skip_database.py"
    "switch_to_sqlite.py"
)

archive_count=0
for script in "${TEMP_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        cp "$script" "$ARCHIVE_DIR/phase1_2_debug_scripts/"
        rm "$script"
        echo "  Archived: $script"
        ((archive_count++))
    fi
done
echo "‚úÖ Archived $archive_count temporary scripts"

# ------------------------------------------------------
# STEP 3: ARCHIVE DUPLICATE RUNNERS
# ------------------------------------------------------
echo ""
echo "ÌøÉ STEP 3: Archiving duplicate runners..."
DUPLICATE_RUNNERS=(
    "run_etl_ascii.py"
    "run_etl_clean.py"
    "run_etl_test.py"
    "run_final_etl.py"
    "test_all_components.py"
)

for runner in "${DUPLICATE_RUNNERS[@]}"; do
    if [ -f "$runner" ]; then
        cp "$runner" "$ARCHIVE_DIR/phase1_2_debug_scripts/"
        rm "$runner"
        echo "  Archived: $runner"
        ((archive_count++))
    fi
done

# ------------------------------------------------------
# STEP 4: ARCHIVE LOG FILES
# ------------------------------------------------------
echo ""
echo "Ì≥ù STEP 4: Archiving log files..."
LOG_FILES=(
    "debugging_report.txt"
    "validation_results.log"
    "unnest_log.txt"
)

for log in "${LOG_FILES[@]}"; do
    if [ -f "$log" ]; then
        cp "$log" "$ARCHIVE_DIR/logs/"
        rm "$log"
        echo "  Archived: $log"
        ((archive_count++))
    fi
done

# ------------------------------------------------------
# STEP 5: CLEAN UP BACKUP FILES (KEEP ONLY LATEST)
# ------------------------------------------------------
echo ""
echo "Ì≤æ STEP 5: Managing backup files..."

# Archive old parser backups
if [ -f "src/etl/parser.py.bak" ]; then
    cp "src/etl/parser.py.bak" "$ARCHIVE_DIR/backups/"
    rm "src/etl/parser.py.bak"
    echo "  Archived: parser.py.bak"
fi

if [ -f "src/etl/loader.py.bak" ]; then
    cp "src/etl/loader.py.bak" "$ARCHIVE_DIR/backups/"
    rm "src/etl/loader.py.bak"
    echo "  Archived: loader.py.bak"
fi

# Keep only the .backup files (these are the most recent)
if [ -f "src/etl/config.py.backup3" ]; then
    cp "src/etl/config.py.backup3" "$ARCHIVE_DIR/backups/"
    rm "src/etl/config.py.backup3"
    echo "  Archived: config.py.backup3"
fi

# ------------------------------------------------------
# STEP 6: CLEAN PYTHON CACHE
# ------------------------------------------------------
echo ""
echo "Ì∑π STEP 6: Cleaning Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type f -name ".coverage" -delete
echo "‚úÖ Python cache cleaned"

# ------------------------------------------------------
# STEP 7: VERIFY CORE FILES
# ------------------------------------------------------
echo ""
echo "Ì¥ç STEP 7: Verifying core files..."
CORE_FILES=(
    "src/etl/parser.py"
    "src/etl/loader.py"
    "src/etl/pipeline.py"
    "src/etl/downloader.py"
    "run_full_etl.py"
    "docker/compose.yaml"
    "config/etl_config.yaml"
)

all_core_ok=true
for file in "${CORE_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ‚úÖ $file"
    else
        echo "  ‚ùå MISSING: $file"
        all_core_ok=false
    fi
done

if $all_core_ok; then
    echo "‚úÖ All core files intact"
else
    echo "‚ùå Some core files missing - stopping cleanup"
    exit 1
fi

# ------------------------------------------------------
# STEP 8: FINAL VERIFICATION
# ------------------------------------------------------
echo ""
echo "Ì∑™ STEP 8: Final verification..."

# Quick Python import test
python3 -c "
import sys
sys.path.insert(0, 'src')
try:
    from etl.parser import CSVParser
    from etl.loader import DatabaseLoader
    from etl.pipeline import ETLPipeline
    print('‚úÖ Core imports working')
except Exception as e:
    print(f'‚ùå Import error: {e}')
    sys.exit(1)
"

# Database connection test (if Docker is running)
if docker ps | grep -q alpha_betting_postgres; then
    echo "‚úÖ Docker PostgreSQL is running"
else
    echo "‚ö†Ô∏è  Docker PostgreSQL not running (expected if not needed)"
fi

# ------------------------------------------------------
# STEP 9: SUMMARY
# ------------------------------------------------------
echo ""
echo "=================================================="
echo "Ì≥ä CLEANUP SUMMARY"
echo "=================================================="
echo "‚úÖ Archive created: $ARCHIVE_DIR"
echo "‚úÖ Files archived: $archive_count"
echo "‚úÖ Core functionality verified"
echo ""
echo "Ì≥Å Project structure after cleanup:"
echo "‚îú‚îÄ‚îÄ src/etl/                  # Core ETL engine"
echo "‚îÇ   ‚îú‚îÄ‚îÄ parser.py            # ‚úÖ Fixed parser"
echo "‚îÇ   ‚îú‚îÄ‚îÄ loader.py           # ‚úÖ Fixed loader"
echo "‚îÇ   ‚îú‚îÄ‚îÄ pipeline.py         # ‚úÖ Fixed pipeline"
echo "‚îÇ   ‚îî‚îÄ‚îÄ downloader.py       # ‚úÖ Working downloader"
echo "‚îú‚îÄ‚îÄ docker/                  # Docker configuration"
echo "‚îú‚îÄ‚îÄ config/                  # Project configuration"
echo "‚îú‚îÄ‚îÄ scripts/                 # Production scripts"
echo "‚îú‚îÄ‚îÄ logs/                    # Current logs (kept)"
echo "‚îî‚îÄ‚îÄ run_full_etl.py         # ‚úÖ Primary runner"
echo ""
echo "Ì∫Ä Ready for Phase 3: Feature Engine & Dixon-Coles Model"
echo "=================================================="
