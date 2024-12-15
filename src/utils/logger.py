"""
Logging configuration for the application.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# Create logs directory
logs_dir = Path.home() / ".ai-email-assistant" / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)

# Create log file with timestamp
log_file = logs_dir / f"app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Configure logging
logger = logging.getLogger("AIEmailAssistant")
logger.setLevel(logging.DEBUG)

# Create formatters
file_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
console_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
)

# Create file handler
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(file_formatter)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(console_formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Set exception handling
def handle_exception(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        # Call default handler for keyboard interrupt
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
        
    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

# Set exception hook
sys.excepthook = handle_exception 