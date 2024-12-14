"""
Service for handling email operations with progress tracking.
"""

from PyQt6.QtCore import QObject, pyqtSignal
from services.notification_service import NotificationService, NotificationType
from typing import Optional, Dict, Any, List
from utils.logger import logger
import threading
import time

class EmailOperationService(QObject):
    """Service for handling email operations with progress tracking."""
    
    # Signals for operation progress
    operation_started = pyqtSignal(str, str)  # operation_id, operation_type
    operation_progress = pyqtSignal(str, int)  # operation_id, progress
    operation_completed = pyqtSignal(str, bool, str)  # operation_id, success, message
    
    def __init__(self, notification_service: NotificationService):
        """Initialize the email operation service."""
        super().__init__()
        self.notification_service = notification_service
        self.active_operations: Dict[str, Dict[str, Any]] = {}
        
        # Connect signals to notification handling
        self.operation_started.connect(self._handle_operation_started)
        self.operation_progress.connect(self._handle_operation_progress)
        self.operation_completed.connect(self._handle_operation_completed)
    
    def send_email(self, email_data: Dict[str, Any]) -> str:
        """
        Send an email with progress tracking.
        
        Args:
            email_data: Dictionary containing email data
            
        Returns:
            str: Operation ID for tracking
        """
        operation_id = f"send_{time.time()}"
        
        def send_task():
            try:
                # Emit started signal
                self.operation_started.emit(operation_id, "send")
                
                # Simulate email sending steps
                # In real implementation, these would be actual SMTP operations
                steps = [
                    ("Preparing email", 10),
                    ("Processing attachments", 30),
                    ("Establishing connection", 50),
                    ("Sending message", 80),
                    ("Finalizing", 100)
                ]
                
                for step, progress in steps:
                    # Update operation info
                    self.active_operations[operation_id]["status"] = step
                    self.active_operations[operation_id]["progress"] = progress
                    
                    # Emit progress
                    self.operation_progress.emit(operation_id, progress)
                    
                    # Simulate work
                    time.sleep(0.5)
                
                # Emit completion
                self.operation_completed.emit(
                    operation_id,
                    True,
                    "Email sent successfully"
                )
                
            except Exception as e:
                logger.error(f"Error sending email: {str(e)}")
                self.operation_completed.emit(
                    operation_id,
                    False,
                    f"Failed to send email: {str(e)}"
                )
        
        # Store operation info
        self.active_operations[operation_id] = {
            "type": "send",
            "data": email_data,
            "status": "Starting",
            "progress": 0
        }
        
        # Start operation in thread
        thread = threading.Thread(target=send_task)
        thread.daemon = True
        thread.start()
        
        return operation_id
    
    def fetch_emails(self, folder: str, count: int = 50) -> str:
        """
        Fetch emails from a folder with progress tracking.
        
        Args:
            folder: Folder to fetch from
            count: Number of emails to fetch
            
        Returns:
            str: Operation ID for tracking
        """
        operation_id = f"fetch_{time.time()}"
        
        def fetch_task():
            try:
                # Emit started signal
                self.operation_started.emit(operation_id, "fetch")
                
                # Simulate email fetching steps
                # In real implementation, these would be actual IMAP operations
                total_steps = 4
                for i in range(total_steps):
                    progress = int((i + 1) * (100 / total_steps))
                    
                    # Update operation info
                    status = f"Fetching emails ({i + 1}/{total_steps})"
                    self.active_operations[operation_id]["status"] = status
                    self.active_operations[operation_id]["progress"] = progress
                    
                    # Emit progress
                    self.operation_progress.emit(operation_id, progress)
                    
                    # Simulate work
                    time.sleep(0.5)
                
                # Emit completion
                self.operation_completed.emit(
                    operation_id,
                    True,
                    f"Successfully fetched {count} emails"
                )
                
            except Exception as e:
                logger.error(f"Error fetching emails: {str(e)}")
                self.operation_completed.emit(
                    operation_id,
                    False,
                    f"Failed to fetch emails: {str(e)}"
                )
        
        # Store operation info
        self.active_operations[operation_id] = {
            "type": "fetch",
            "folder": folder,
            "count": count,
            "status": "Starting",
            "progress": 0
        }
        
        # Start operation in thread
        thread = threading.Thread(target=fetch_task)
        thread.daemon = True
        thread.start()
        
        return operation_id
    
    def sync_folder(self, folder: str) -> str:
        """
        Synchronize an email folder with progress tracking.
        
        Args:
            folder: Folder to synchronize
            
        Returns:
            str: Operation ID for tracking
        """
        operation_id = f"sync_{time.time()}"
        
        def sync_task():
            try:
                # Emit started signal
                self.operation_started.emit(operation_id, "sync")
                
                # Simulate folder sync steps
                steps = [
                    ("Checking for changes", 20),
                    ("Downloading new messages", 40),
                    ("Updating flags", 60),
                    ("Removing deleted messages", 80),
                    ("Finalizing sync", 100)
                ]
                
                for step, progress in steps:
                    # Update operation info
                    self.active_operations[operation_id]["status"] = step
                    self.active_operations[operation_id]["progress"] = progress
                    
                    # Emit progress
                    self.operation_progress.emit(operation_id, progress)
                    
                    # Simulate work
                    time.sleep(0.5)
                
                # Emit completion
                self.operation_completed.emit(
                    operation_id,
                    True,
                    f"Successfully synchronized {folder}"
                )
                
            except Exception as e:
                logger.error(f"Error syncing folder: {str(e)}")
                self.operation_completed.emit(
                    operation_id,
                    False,
                    f"Failed to sync folder: {str(e)}"
                )
        
        # Store operation info
        self.active_operations[operation_id] = {
            "type": "sync",
            "folder": folder,
            "status": "Starting",
            "progress": 0
        }
        
        # Start operation in thread
        thread = threading.Thread(target=sync_task)
        thread.daemon = True
        thread.start()
        
        return operation_id
    
    def cancel_operation(self, operation_id: str):
        """
        Cancel an ongoing operation.
        
        Args:
            operation_id: ID of the operation to cancel
        """
        if operation_id in self.active_operations:
            # Mark operation as cancelled
            self.active_operations[operation_id]["cancelled"] = True
            
            # Show cancellation notification
            self.notification_service.show_notification(
                "Operation Cancelled",
                f"The operation was cancelled by user",
                NotificationType.WARNING
            )
            
            # Clean up
            del self.active_operations[operation_id]
    
    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of an operation.
        
        Args:
            operation_id: ID of the operation
            
        Returns:
            Dict containing operation status or None if not found
        """
        return self.active_operations.get(operation_id)
    
    def get_active_operations(self) -> List[Dict[str, Any]]:
        """Get list of all active operations."""
        return list(self.active_operations.values())
    
    def _handle_operation_started(self, operation_id: str, operation_type: str):
        """Handle operation started signal."""
        operation = self.active_operations.get(operation_id)
        if not operation:
            return
        
        # Show notification
        title_map = {
            "send": "Sending Email",
            "fetch": "Fetching Emails",
            "sync": "Synchronizing Folder"
        }
        
        self.notification_service.show_notification(
            title_map.get(operation_type, "Operation Started"),
            operation.get("status", "Operation in progress..."),
            NotificationType.PROGRESS,
            progress=0,
            duration=None  # Persistent until completed
        )
    
    def _handle_operation_progress(self, operation_id: str, progress: int):
        """Handle operation progress signal."""
        operation = self.active_operations.get(operation_id)
        if not operation:
            return
        
        # Update notification progress
        self.notification_service.update_progress(operation_id, progress)
    
    def _handle_operation_completed(self, operation_id: str, success: bool, message: str):
        """Handle operation completed signal."""
        operation = self.active_operations.get(operation_id)
        if not operation:
            return
        
        # Show completion notification
        self.notification_service.show_notification(
            "Operation Complete" if success else "Operation Failed",
            message,
            NotificationType.SUCCESS if success else NotificationType.ERROR,
            duration=5000  # Show for 5 seconds
        )
        
        # Clean up
        if operation_id in self.active_operations:
            del self.active_operations[operation_id] 