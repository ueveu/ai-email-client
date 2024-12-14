"""
Error handling utilities for the application.
"""

import sys
import traceback
from functools import wraps
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal
from .logger import logger
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Error:
    """Represents an error with timestamp and context."""
    timestamp: datetime
    message: str
    traceback: str
    context: Dict[str, Any]

class ErrorCollection:
    """Collection of errors that occurred during an operation."""
    
    def __init__(self):
        self.errors: List[Error] = []
    
    def add(self, message: str, context: Dict[str, Any] = None):
        """Add an error to the collection."""
        error = Error(
            timestamp=datetime.now(),
            message=message,
            traceback=''.join(traceback.format_stack()),
            context=context or {}
        )
        self.errors.append(error)
        logger.error(f"{message} | Context: {context}")
    
    def has_errors(self) -> bool:
        """Check if collection has any errors."""
        return len(self.errors) > 0
    
    def get_messages(self) -> List[str]:
        """Get list of error messages."""
        return [error.message for error in self.errors]
    
    def clear(self):
        """Clear all errors."""
        self.errors.clear()

class ErrorHandler(QObject):
    """
    Central error handler for the application.
    Manages error reporting, logging, and user notifications.
    """
    
    error_occurred = pyqtSignal(str, str)  # message, details
    
    def __init__(self):
        super().__init__()
        self.error_occurred.connect(self._show_error_dialog)
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None):
        """
        Handle an error by logging it and notifying the user if needed.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
        """
        # Log the error
        logger.log_error(error, context)
        
        # Get error details
        error_type = type(error).__name__
        error_message = str(error)
        error_traceback = ''.join(traceback.format_exception(
            type(error), error, error.__traceback__
        ))
        
        # Emit signal for UI notification
        self.error_occurred.emit(
            f"{error_type}: {error_message}",
            error_traceback
        )
    
    def _show_error_dialog(self, message: str, details: str = None):
        """Show error dialog to user."""
        dialog = QMessageBox()
        dialog.setIcon(QMessageBox.Icon.Critical)
        dialog.setText(message)
        dialog.setWindowTitle("Error")
        
        if details:
            dialog.setDetailedText(details)
        
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.exec()

# Global error handler instance
error_handler = ErrorHandler()

def handle_errors(func):
    """
    Decorator to handle exceptions in functions.
    Logs errors and shows user-friendly messages.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_handler.handle_error(e, {
                'function': func.__name__,
                'args': args,
                'kwargs': kwargs
            })
            return None
    return wrapper

def collect_errors(collection: ErrorCollection, operation: str):
    """
    Decorator to collect errors in an ErrorCollection.
    Used for operations that may have multiple recoverable errors.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if collection:
                    collection.add(
                        f"Error in {operation}: {str(e)}",
                        {
                            'function': func.__name__,
                            'args': args,
                            'kwargs': kwargs
                        }
                    )
                return None
        return wrapper
    return decorator 