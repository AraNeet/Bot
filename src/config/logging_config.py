import logging
import os
from datetime import datetime


def setup_logging(log_level=logging.INFO, log_to_file=True):
    """
    Configure logging for the application.
    
    Args:
        log_level: Logging level (default: INFO)
        log_to_file: Whether to also log to a file (default: True)
    """
    # Create logs directory if it doesn't exist
    if log_to_file:
        log_dir = "docs/logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"app_manager_{timestamp}.log")
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure handlers
    handlers = [logging.StreamHandler()]  # Console handler
    
    if log_to_file:
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        handlers.append(file_handler)
    
    # Apply configuration
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers
    )
    
    logging.info(f"Logging initialized. Level: {logging.getLevelName(log_level)}")
    if log_to_file:
        logging.info(f"Log file: {log_file}")