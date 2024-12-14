import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

class Logger:
    """
    Centralized logging system for the application.
    Handles both file and console logging with different levels.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Create logs directory
        self.logs_dir = Path.home() / ".ai-email-assistant" / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up logging format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create file handler with rotation
        log_file = self.logs_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        
        # Set up root logger
        self.logger = logging.getLogger('AIEmailAssistant')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Initialize error tracking
        self.recent_errors = []
        self.max_stored_errors = 100
        
        self._initialized = True
    
    def error(self, message, *args, **kwargs):
        """Log an error message."""
        self.logger.error(message, *args, **kwargs)
    
    def warning(self, message, *args, **kwargs):
        """Log a warning message."""
        self.logger.warning(message, *args, **kwargs)
    
    def info(self, message, *args, **kwargs):
        """Log an info message."""
        self.logger.info(message, *args, **kwargs)
    
    def debug(self, message, *args, **kwargs):
        """Log a debug message."""
        self.logger.debug(message, *args, **kwargs)
    
    def log_error(self, error, context=None):
        """
        Log an error with optional context information.
        
        Args:
            error: The error object or message
            context (dict, optional): Additional context about the error
        """
        error_info = {
            'timestamp': datetime.now(),
            'error': str(error),
            'type': type(error).__name__,
            'context': context or {}
        }
        
        # Add to recent errors list
        self.recent_errors.insert(0, error_info)
        if len(self.recent_errors) > self.max_stored_errors:
            self.recent_errors.pop()
        
        # Log the error
        error_msg = f"{error_info['type']}: {error_info['error']}"
        if context:
            error_msg += f" | Context: {context}"
        
        self.logger.error(error_msg)
        if isinstance(error, Exception):
            self.logger.exception("Exception details:")
    
    def get_recent_errors(self, limit=None):
        """
        Get recent errors.
        
        Args:
            limit (int, optional): Maximum number of errors to return
        
        Returns:
            list: Recent error information
        """
        if limit is None or limit > len(self.recent_errors):
            return self.recent_errors
        return self.recent_errors[:limit]
    
    def clear_errors(self):
        """Clear the stored error history."""
        self.recent_errors = []
    
    def get_error_summary(self):
        """
        Get a summary of recent errors grouped by type.
        
        Returns:
            dict: Error counts by type
        """
        summary = {}
        for error in self.recent_errors:
            error_type = error['type']
            if error_type not in summary:
                summary[error_type] = 0
            summary[error_type] += 1
        return summary

# Global logger instance
logger = Logger() 