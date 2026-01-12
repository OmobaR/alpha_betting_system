#!/bin/bash
# Robust dependency installer for AlphaBetting

echo "=== Installing AlphaBetting Dependencies ==="

# Create backup of current environment
pip freeze > requirements-backup.txt 2>/dev/null || echo "No packages to backup"

# Remove problematic packages if they exist
pip uninstall -y ruamel.yaml ruamel.yaml.clib ruamel.yaml.clibz 2>/dev/null || true

# Step 1: Install base packages with explicit versions
echo "1. Installing base packages..."
BASE_PACKAGES="pandas==2.0.0 psycopg2-binary==2.9.6 requests==2.31.0 pyyaml==6.0 tenacity==8.2.0 python-dotenv==1.0.0"
for pkg in $BASE_PACKAGES; do
    echo "   Installing $pkg..."
    pip install "$pkg" --no-deps
done

# Step 2: Install dependencies separately
echo "2. Installing dependencies..."
pip install "numpy>=1.24.0" "python-dateutil>=2.8.0" "pytz>=2023.0" "tzdata>=2023.0"

# Step 3: Verify installation
echo "3. Verifying installation..."
python -c "
try:
    import pandas; print('✅ pandas:', pandas.__version__)
    import psycopg2; print('✅ psycopg2:', psycopg2.__version__)
    import requests; print('✅ requests:', requests.__version__)
    import yaml; print('✅ pyyaml installed')
    from tenacity import retry; print('✅ tenacity installed')
    import dotenv; print('✅ python-dotenv installed')
    print('\\n✅ All ETL dependencies installed successfully!')
except ImportError as e:
    print(f'❌ Error: {e}')
    exit(1)
"

# Step 4: Save working requirements
echo "4. Creating requirements.txt..."
cat > requirements.txt << 'REQEOF'
# AlphaBetting Working Requirements
# Installed on $(date)

# Core ETL
pandas>=2.0.0
psycopg2-binary>=2.9.6
requests>=2.31.0
pyyaml>=6.0
tenacity>=8.2.0
python-dotenv>=1.0.0

# Dependencies (auto-installed)
# numpy>=1.24.0
# python-dateutil>=2.8.0
# pytz>=2023.0
# tzdata>=2023.0

# To install later:
# scikit-learn>=1.3.0
# scipy>=1.10.0
# sqlalchemy>=2.0.0
# prefect>=2.10.0
# jupyter>=1.0.0
REQEOF

echo "=== Installation Complete ==="
echo "Requirements saved to: requirements.txt"
echo "Backup saved to: requirements-backup.txt"
