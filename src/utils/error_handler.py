"""
Error handling utilities for the application.
"""

from functools import wraps
from typing import Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from utils.logger import logger

@dataclass
class Error:
    """Data class representing an error."""
    message: str
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: Optional[dict] = None

@dataclass
class ErrorCollection:
    """Collection of errors that occurred during an operation."""
    errors: List[Error] = field(default_factory=list)
    
    def add(self, message: str, source: str = "", details: Optional[dict] = None):
        """
        Add an error to the collection.
        
        Args:
            message: Error message
            source: Source of the error
            details: Additional error details
        """
        self.errors.append(Error(message, source, details=details))
    
    def has_errors(self) -> bool:
        """
        Check if collection has any errors.
        
        Returns:
            bool: True if collection has errors
        """
        return len(self.errors) > 0
    
    def clear(self):
        """Clear all errors from the collection."""
        self.errors.clear()
    
    def get_messages(self) -> List[str]:
        """
        Get list of error messages.
        
        Returns:
            List[str]: List of error messages
        """
        return [error.message for error in self.errors]
    
    def get_latest(self) -> Optional[Error]:
        """
        Get most recent error.
        
        Returns:
            Optional[Error]: Most recent error if any
        """
        return self.errors[-1] if self.errors else None

def handle_errors(func: Callable) -> Callable:
    """
    Decorator for handling function errors.
    
    Args:
        func: Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise
    return wrapper

def collect_errors(error_collection: Optional[ErrorCollection], source: str) -> Callable:
    """
    Decorator for collecting errors in a function.
    
    Args:
        error_collection: Collection to store errors
        source: Source identifier for errors
        
    Returns:
        Callable: Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if error_collection:
                    error_collection.add(str(e), source)
                logger.error(f"Error in {source}: {str(e)}")
                raise
        return wrapper
    return decorator 