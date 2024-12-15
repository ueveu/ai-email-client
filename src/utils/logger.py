import logging
import sys
from pathlib import Path

# Create logger
logger = logging.getLogger('AIEmailAssistant')
logger.setLevel(logging.DEBUG)

# Create formatters and handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

# File handler
log_dir = Path.home() / '.ai_email_assistant' / 'logs'
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / 'app.log'

file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Export common logging methods
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
critical = logger.critical 