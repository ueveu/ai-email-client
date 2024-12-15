"""
Service for managing email operations and their status.
"""

from PyQt6.QtCore import QObject, pyqtSignal
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
from utils.logger import logger
from services.notification_service import NotificationService, NotificationType

class OperationType(Enum):
    """Types of email operations."""
    SEND = "send"
    FETCH = "fetch"
    MOVE = "move"
    DELETE = "delete"
    SYNC = "sync"
    SEARCH = "search"
    ATTACHMENT = "attachment"
    FOLDER = "folder"

class OperationStatus(Enum):
    """Status of an email operation."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Operation:
    """Data class representing an email operation."""
    id: str
    type: OperationType
    status: OperationStatus
    description: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    progress: Optional[int] = None

class EmailOperationService(QObject):
    """Service for managing email operations."""
    
    # Signals for operation events
    operation_started = pyqtSignal(Operation)
    operation_completed = pyqtSignal(Operation)
    operation_failed = pyqtSignal(Operation)
    operation_cancelled = pyqtSignal(Operation)
    operation_progress = pyqtSignal(Operation)
    
    def __init__(self, notification_service: NotificationService):
        """
        Initialize operation service.
        
        Args:
            notification_service: Service for showing notifications
        """
        super().__init__()
        self.notification_service = notification_service
        self.active_operations: Dict[str, Operation] = {}
        self.operation_history: List[Operation] = []
    
    def start_operation(self, type: OperationType, description: str) -> str:
        """
        Start a new operation.
        
        Args:
            type: Type of operation
            description: Operation description
            
        Returns:
            str: Operation ID
        """
        try:
            # Create operation
            operation = Operation(
                id=f"{type.value}_{datetime.now().timestamp()}",
                type=type,
                status=OperationStatus.RUNNING,
                description=description,
                started_at=datetime.now()
            )
            
            # Store operation
            self.active_operations[operation.id] = operation
            self.operation_history.append(operation)
            
            # Emit signal
            self.operation_started.emit(operation)
            
            # Show notification
            self.notification_service.show_notification(
                title=f"Starting {type.value}",
                message=description,
                type=NotificationType.INFO
            )
            
            return operation.id
            
        except Exception as e:
            logger.error(f"Error starting operation: {str(e)}")
            return ""
    
    def complete_operation(self, operation_id: str, success: bool, message: str):
        """
        Complete an operation.
        
        Args:
            operation_id: ID of the operation
            success: Whether the operation was successful
            message: Completion message
        """
        try:
            if operation_id not in self.active_operations:
                return
            
            operation = self.active_operations[operation_id]
            
            # Update operation
            operation.status = OperationStatus.COMPLETED if success else OperationStatus.FAILED
            operation.completed_at = datetime.now()
            operation.error_message = None if success else message
            
            # Remove from active operations
            del self.active_operations[operation_id]
            
            # Emit signal
            if success:
                self.operation_completed.emit(operation)
            else:
                self.operation_failed.emit(operation)
            
            # Show notification
            self.notification_service.show_notification(
                title=f"{operation.type.value.title()} {'completed' if success else 'failed'}",
                message=message,
                type=NotificationType.SUCCESS if success else NotificationType.ERROR
            )
            
        except Exception as e:
            logger.error(f"Error completing operation: {str(e)}")
    
    def fail_operation(self, operation_id: str, error_message: str):
        """
        Mark an operation as failed.
        
        Args:
            operation_id: ID of the operation
            error_message: Error message
        """
        self.complete_operation(operation_id, False, error_message)
    
    def cancel_operation(self, operation_id: str):
        """
        Cancel an operation.
        
        Args:
            operation_id: ID of the operation
        """
        try:
            if operation_id not in self.active_operations:
                return
            
            operation = self.active_operations[operation_id]
            
            # Update operation
            operation.status = OperationStatus.CANCELLED
            operation.completed_at = datetime.now()
            
            # Remove from active operations
            del self.active_operations[operation_id]
            
            # Emit signal
            self.operation_cancelled.emit(operation)
            
            # Show notification
            self.notification_service.show_notification(
                title=f"{operation.type.value.title()} cancelled",
                message=f"Operation cancelled: {operation.description}",
                type=NotificationType.WARNING
            )
            
        except Exception as e:
            logger.error(f"Error cancelling operation: {str(e)}")
    
    def update_progress(self, operation_id: str, progress: int):
        """
        Update operation progress.
        
        Args:
            operation_id: ID of the operation
            progress: Progress value (0-100)
        """
        try:
            if operation_id not in self.active_operations:
                return
            
            operation = self.active_operations[operation_id]
            
            # Update progress
            operation.progress = progress
            
            # Emit signal
            self.operation_progress.emit(operation)
            
            # Update notification
            self.notification_service.update_notification(
                operation_id,
                progress=progress
            )
            
        except Exception as e:
            logger.error(f"Error updating operation progress: {str(e)}")
    
    def get_active_operations(self) -> List[Operation]:
        """
        Get list of active operations.
        
        Returns:
            List[Operation]: List of active operations
        """
        return list(self.active_operations.values())
    
    def get_operation(self, operation_id: str) -> Optional[Operation]:
        """
        Get a specific operation.
        
        Args:
            operation_id: ID of the operation
            
        Returns:
            Optional[Operation]: Operation if found
        """
        return self.active_operations.get(operation_id)
    
    def get_operation_history(self) -> List[Operation]:
        """
        Get operation history.
        
        Returns:
            List[Operation]: List of all operations
        """
        return self.operation_history.copy() 