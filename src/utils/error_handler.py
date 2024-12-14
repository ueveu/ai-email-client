import sys
import traceback
from functools import wraps
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal
from .logger import logger

class ErrorHandler(QObject):
    """
    Global error handler that manages exceptions and provides error reporting.
    """
    
    error_occurred = pyqtSignal(str, str)  # Signal emitted when an error occurs (type, message)
    
    def __init__(self):
        super().__init__()
        self.install_global_handler()
    
    def install_global_handler(self):
        """Install the global exception handler."""
        sys.excepthook = self.handle_global_exception
    
    def handle_global_exception(self, exc_type, exc_value, exc_traceback):
        """
        Handle uncaught exceptions globally.
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
        """
        # Format the traceback
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = ''.join(tb_lines)
        
        # Log the error
        logger.log_error(exc_value, {
            'traceback': tb_text,
            'type': exc_type.__name__
        })
        
        # Emit the error signal
        self.error_occurred.emit(exc_type.__name__, str(exc_value))
        
        # Show error dialog if in GUI context
        try:
            QMessageBox.critical(
                None,
                "Error",
                f"An error occurred: {str(exc_value)}\n\nCheck the logs for details."
            )
        except:
            # If we can't show GUI dialog, print to console
            print(f"Error: {exc_type.__name__}: {exc_value}\n{tb_text}", file=sys.stderr)

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
            
            # Log the error
            logger.log_error(e, context)
            
            # Show error dialog
            QMessageBox.warning(
                None,
                "Operation Failed",
                f"The operation failed: {str(e)}\n\nCheck the logs for details."
            )
            
            # Re-raise the exception if it's critical
            if isinstance(e, (SystemExit, KeyboardInterrupt)):
                raise
            
            return None
    
    return wrapper

# Global error handler instance
error_handler = ErrorHandler() 