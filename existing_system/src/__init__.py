# src/__init__.py

# Import common utilities and configuration loading
from .utils import load_config, setup_logger

# Load configuration from a YAML file
config = load_config('config.yaml')

# Set up the logger for the project
logger = setup_logger(config)

# Package Initialization complete
logger.info("Football Prediction Package initialized with the provided config.")
