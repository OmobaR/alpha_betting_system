#!/bin/bash
# AlphaBetting Project Activation Script

echo "=== AlphaBetting Project Setup ==="

# 1. Start Docker containers
echo "1. Starting Docker containers..."
docker-compose -f docker/compose.yaml up -d

# 2. Activate virtual environment
echo "2. Activating virtual environment..."
if [ -d "alphabetting_env" ]; then
    source alphabetting_env/Scripts/activate
    echo "   ✅ Virtual environment activated"
    
    # 3. Check/install dependencies
    echo "3. Checking dependencies..."
    if python -c "import pandas, psycopg2, requests, yaml, tenacity, dotenv" 2>/dev/null; then
        echo "   ✅ All dependencies already installed"
    else
        echo "   ⚠️  Missing dependencies, running installer..."
        ./install_dependencies.sh
    fi
else
    echo "   ❌ Virtual environment not found"
    echo "   Please create it: python -m venv alphabetting_env"
    echo "   Then activate and run: ./install_dependencies.sh"
    exit 1
fi

echo "=== Ready to work! ==="
echo "Run ETL: python scripts/run_etl.py"
echo "Deactivate: 'deactivate' then 'docker-compose down'"
