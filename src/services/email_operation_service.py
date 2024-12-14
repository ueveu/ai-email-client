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
    """Represents an email operation."""
    id: str
    type: OperationType
    status: OperationStatus
    description: str
    start_time: datetime
    end_time: Optional[datetime] = None
    progress: Optional[int] = None
    error: Optional[str] = None
    details: Optional[Dict] = None

class EmailOperationService(QObject):
    """Service for managing email operations."""
    
    # Signals
    operation_started = pyqtSignal(str, OperationType)  # id, type
    operation_updated = pyqtSignal(str, int)  # id, progress
    operation_completed = pyqtSignal(str, bool, str)  # id, success, message
    operation_failed = pyqtSignal(str, str)  # id, error
    operation_cancelled = pyqtSignal(str)  # id
    
    def __init__(self, notification_service: NotificationService):
        """Initialize the operation service."""
        super().__init__()
        self.notification_service = notification_service
        self.active_operations: Dict[str, Operation] = {}
        self.operation_history: List[Operation] = []
        self.max_history = 100
    
    def start_operation(
        self,
        type: OperationType,
        description: str,
        details: Optional[Dict] = None
    ) -> str:
        """
        Start a new email operation.
        
        Args:
            type: Type of operation
            description: Description of the operation
            details: Additional operation details
            
        Returns:
            str: Operation ID
        """
        try:
            # Generate unique ID
            operation_id = f"{type.value}_{datetime.now().timestamp()}"
            
            # Create operation
            operation = Operation(
                id=operation_id,
                type=type,
                status=OperationStatus.RUNNING,
                description=description,
                start_time=datetime.now(),
                details=details or {}
            )
            
            # Store operation
            self.active_operations[operation_id] = operation
            
            # Show notification
            self.notification_service.show_notification(
                f"Starting {type.value}",
                description,
                NotificationType.INFO
            )
            
            # Emit signal
            self.operation_started.emit(operation_id, type)
            
            logger.info(f"Started operation: {description}")
            return operation_id
            
        except Exception as e:
            logger.error(f"Error starting operation: {str(e)}")
            return ""
    
    def update_progress(self, operation_id: str, progress: int):
        """
        Update operation progress.
        
        Args:
            operation_id: ID of the operation
            progress: Progress value (0-100)
        """
        if operation_id in self.active_operations:
            operation = self.active_operations[operation_id]
            operation.progress = max(0, min(100, progress))
            self.operation_updated.emit(operation_id, progress)
    
    def complete_operation(self, operation_id: str, success: bool, message: str = ""):
        """
        Mark an operation as completed.
        
        Args:
            operation_id: ID of the operation
            success: Whether operation was successful
            message: Completion message
        """
        if operation_id in self.active_operations:
            operation = self.active_operations[operation_id]
            operation.status = OperationStatus.COMPLETED
            operation.end_time = datetime.now()
            
            # Move to history
            self.operation_history.append(operation)
            if len(self.operation_history) > self.max_history:
                self.operation_history.pop(0)
            
            # Remove from active operations
            del self.active_operations[operation_id]
            
            # Show notification
            notification_type = (
                NotificationType.SUCCESS if success
                else NotificationType.ERROR
            )
            self.notification_service.show_notification(
                f"Operation {operation.type.value} completed",
                message or operation.description,
                notification_type
            )
            
            # Emit signal
            self.operation_completed.emit(operation_id, success, message)
            
            logger.info(
                f"Completed operation {operation.type.value}: "
                f"{'Success' if success else 'Failed'}"
            )
    
    def fail_operation(self, operation_id: str, error: str):
        """
        Mark an operation as failed.
        
        Args:
            operation_id: ID of the operation
            error: Error message
        """
        if operation_id in self.active_operations:
            operation = self.active_operations[operation_id]
            operation.status = OperationStatus.FAILED
            operation.end_time = datetime.now()
            operation.error = error
            
            # Move to history
            self.operation_history.append(operation)
            if len(self.operation_history) > self.max_history:
                self.operation_history.pop(0)
            
            # Remove from active operations
            del self.active_operations[operation_id]
            
            # Show notification
            self.notification_service.show_notification(
                f"Operation {operation.type.value} failed",
                error,
                NotificationType.ERROR
            )
            
            # Emit signal
            self.operation_failed.emit(operation_id, error)
            
            logger.error(f"Operation failed: {error}")
    
    def cancel_operation(self, operation_id: str):
        """
        Cancel an active operation.
        
        Args:
            operation_id: ID of the operation to cancel
        """
        if operation_id in self.active_operations:
            operation = self.active_operations[operation_id]
            operation.status = OperationStatus.CANCELLED
            operation.end_time = datetime.now()
            
            # Move to history
            self.operation_history.append(operation)
            if len(self.operation_history) > self.max_history:
                self.operation_history.pop(0)
            
            # Remove from active operations
            del self.active_operations[operation_id]
            
            # Show notification
            self.notification_service.show_notification(
                f"Operation {operation.type.value} cancelled",
                operation.description,
                NotificationType.WARNING
            )
            
            # Emit signal
            self.operation_cancelled.emit(operation_id)
            
            logger.info(f"Cancelled operation: {operation.description}")
    
    def get_active_operations(self) -> List[Operation]:
        """Get list of currently active operations."""
        return list(self.active_operations.values())
    
    def get_operation_history(self) -> List[Operation]:
        """Get list of historical operations."""
        return self.operation_history.copy()
    
    def get_operation(self, operation_id: str) -> Optional[Operation]:
        """
        Get operation by ID.
        
        Args:
            operation_id: ID of the operation
            
        Returns:
            Operation if found, None otherwise
        """
        return self.active_operations.get(operation_id) or next(
            (op for op in self.operation_history if op.id == operation_id),
            None
        )
    
    def clear_history(self):
        """Clear operation history."""
        self.operation_history.clear()
    
    def get_stats(self) -> Dict:
        """
        Get operation statistics.
        
        Returns:
            dict: Operation statistics
        """
        stats = {
            'total_operations': len(self.operation_history),
            'active_operations': len(self.active_operations),
            'success_rate': 0,
            'average_duration': 0,
            'by_type': {},
            'by_status': {}
        }
        
        if self.operation_history:
            # Calculate success rate
            successful = sum(
                1 for op in self.operation_history
                if op.status == OperationStatus.COMPLETED
            )
            stats['success_rate'] = successful / len(self.operation_history)
            
            # Calculate average duration
            durations = [
                (op.end_time - op.start_time).total_seconds()
                for op in self.operation_history
                if op.end_time
            ]
            if durations:
                stats['average_duration'] = sum(durations) / len(durations)
            
            # Count by type
            for op in self.operation_history:
                if op.type.value not in stats['by_type']:
                    stats['by_type'][op.type.value] = 0
                stats['by_type'][op.type.value] += 1
            
            # Count by status
            for op in self.operation_history:
                if op.status.value not in stats['by_status']:
                    stats['by_status'][op.status.value] = 0
                stats['by_status'][op.status.value] += 1
        
        return stats 