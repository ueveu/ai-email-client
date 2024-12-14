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
    """Represents a single error with timestamp and context."""
    message: str
    timestamp: datetime
    context: Dict[str, Any] = None
    
    def __str__(self):
        context_str = f" ({', '.join(f'{k}: {v}' for k, v in self.context.items())})" if self.context else ""
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {self.message}{context_str}"

class ErrorCollection:
    """Collects and manages multiple errors."""
    def __init__(self):
        self.errors: List[Error] = []
    
    def add(self, message: str, context: Dict[str, Any] = None):
        """Add a new error to the collection."""
        error = Error(message, datetime.now(), context)
        self.errors.append(error)
        logger.error(str(error))
    
    def clear(self):
        """Clear all collected errors."""
        self.errors.clear()
    
    def has_errors(self) -> bool:
        """Check if there are any errors collected."""
        return len(self.errors) > 0
    
    def format_errors(self) -> str:
        """Format all errors into a single string."""
        return "\n".join(str(error) for error in self.errors)

def handle_errors(func):
    """
    Decorator to handle errors in functions.
    Logs errors and shows user-friendly messages.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Get context information
            context = {
                'function': func.__name__,
                'args': str(args),
                'kwargs': str(kwargs)
            }
            
            # Format traceback
            tb_text = ''.join(traceback.format_exc())
            
            # Add error to handler's buffer
            error_handler.add_error({
                'type': type(e).__name__,
                'message': str(e),
                'traceback': tb_text,
                'context': context
            })
            
            # Show errors if we have accumulated some
            if len(error_handler.error_buffer) >= 3:  # Show after 3 errors
                error_handler.show_error_dialog()
            
            # Re-raise critical exceptions
            if isinstance(e, (SystemExit, KeyboardInterrupt)):
                raise
            
            return None
    
    return wrapper

def collect_errors(error_collection: ErrorCollection, operation: str):
    """
    Decorator factory that adds errors to an existing collection.
    Use this decorator when you want to collect errors from multiple operations.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_collection.add(str(e), {'operation': operation})
            return None
        return wrapper
    return decorator

# For backward compatibility
def show_error_dialog(message: str):
    """Show a simple error dialog with a single message."""
    logger.error(message)
    QMessageBox.critical(None, "Error", message)

class ErrorHandler(QObject):
    """
    Global error handler that manages exceptions and provides error reporting.
    Supports collecting and displaying multiple errors at once.
    """
    
    error_occurred = pyqtSignal(str, str)  # Signal emitted when an error occurs (type, message)
    
    def __init__(self):
        super().__init__()
        self.error_buffer = []  # Buffer to collect multiple errors
        self.max_buffer_size = 10  # Maximum number of errors to buffer
        self.install_global_handler()
    
    def install_global_handler(self):
        """Install the global exception handler."""
        sys.excepthook = self.handle_global_exception
    
    def handle_global_exception(self, exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions globally."""
        # Format the traceback
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = ''.join(tb_lines)
        
        # Add error to buffer
        error_info = {
            'type': exc_type.__name__,
            'message': str(exc_value),
            'traceback': tb_text,
            'context': {'type': 'global_exception'}
        }
        self.add_error(error_info)
        
        # Emit the error signal
        self.error_occurred.emit(exc_type.__name__, str(exc_value))
        
        # Show error dialog if in GUI context
        self.show_error_dialog()
    
    def add_error(self, error_info):
        """Add an error to the buffer."""
        # Log the error
        logger.log_error(error_info['message'], {
            'traceback': error_info['traceback'],
            'type': error_info['type'],
            'context': error_info['context']
        })
        
        # Add to buffer
        self.error_buffer.append(error_info)
        
        # Keep buffer size in check
        if len(self.error_buffer) > self.max_buffer_size:
            self.error_buffer.pop(0)  # Remove oldest error
    
    def show_error_dialog(self, clear_buffer=True):
        """Show dialog with all buffered errors."""
        if not self.error_buffer:
            return
            
        try:
            # Format error messages
            error_messages = []
            for error in self.error_buffer:
                error_messages.append(
                    f"Error Type: {error['type']}\n"
                    f"Message: {error['message']}\n"
                    f"{'='*50}"
                )
            
            # Show dialog with all errors
            QMessageBox.critical(
                None,
                f"Multiple Errors ({len(self.error_buffer)})",
                "The following errors occurred:\n\n" + "\n\n".join(error_messages)
            )
            
            # Clear buffer if requested
            if clear_buffer:
                self.error_buffer.clear()
                
        except:
            # If we can't show GUI dialog, print to console
            print("Multiple errors occurred:", file=sys.stderr)
            for error in self.error_buffer:
                print(f"\nError Type: {error['type']}", file=sys.stderr)
                print(f"Message: {error['message']}", file=sys.stderr)
                print(f"Traceback:\n{error['traceback']}", file=sys.stderr)
            
            if clear_buffer:
                self.error_buffer.clear()
    
    def handle_errors(self, func):
        """
        Decorator to handle errors in functions.
        Logs errors and shows user-friendly messages.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Get context information
                context = {
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs)
                }
                
                # Format traceback
                tb_text = ''.join(traceback.format_exc())
                
                # Add error to handler's buffer
                error_handler.add_error({
                    'type': type(e).__name__,
                    'message': str(e),
                    'traceback': tb_text,
                    'context': context
                })
                
                # Show errors if we have accumulated some
                if len(error_handler.error_buffer) >= 3:  # Show after 3 errors
                    error_handler.show_error_dialog()
                
                # Re-raise critical exceptions
                if isinstance(e, (SystemExit, KeyboardInterrupt)):
                    raise
                
                return None
        
        return wrapper

# Global error handler instance
error_handler = ErrorHandler() 