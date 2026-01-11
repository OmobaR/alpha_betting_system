import yaml
import logging
import os
import joblib

def load_config(config_path):
    """
    Load the YAML configuration file.
    
    Args:
        config_path (str): Path to the configuration file.
        
    Returns:
        dict: Configuration data as a dictionary.
    """
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        return config
    except Exception as e:
        raise Exception(f"Error loading configuration file: {e}")

def setup_logger(config):
    """
    Set up the logging configuration using the config file.
    
    Args:
        config (dict): Configuration settings.
    
    Returns:
        logger (logging.Logger): Configured logger.
    """
    log_file = config['paths']['logs_folder'] + 'app.log'
    log_level = getattr(logging, config['project']['logging_level'], logging.INFO)
    
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    
    # Create file handler
    if not os.path.exists(os.path.dirname(log_file)):
        os.makedirs(os.path.dirname(log_file))
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # Set format
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to the logger if not already added
    if not logger.hasHandlers():
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger

def save_model(model, filename):
    """
    Save the model to a pickle file.
    
    Args:
        model (sklearn.Model): Trained model to be saved.
        filename (str): Path where the model will be saved.
    """
    try:
        folder = os.path.dirname(filename)
        if not os.path.exists(folder):
            os.makedirs(folder)
        joblib.dump(model, filename)
        print(f"Model saved to {filename}")
    except Exception as e:
        print(f"Error saving model: {e}")

def save_models(models, config):
    """
    Save multiple models to files in the models folder.
    
    Args:
        models (dict): Dictionary of trained models.
        config (dict): Configuration settings.
    """
    folder_path = config['paths']['models_folder']
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    for name, model in models.items():
        file_path = os.path.join(folder_path, f"{name.replace(' ', '_')}.pkl")
        joblib.dump(model, file_path)
        print(f"Saved {name} model to {file_path}")

def load_model(filename):
    """
    Load a model from a pickle file.
    
    Args:
        filename (str): Path to the model file.
    
    Returns:
        model: Loaded model object.
    """
    try:
        model = joblib.load(filename)
        print(f"Model loaded from {filename}")
        return model
    except Exception as e:
        print(f"Error loading model: {e}")
