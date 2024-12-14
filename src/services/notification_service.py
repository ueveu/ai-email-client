"""
Service for managing application-wide status notifications.
"""

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QSystemTrayIcon
from enum import Enum
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime
import json
from utils.logger import logger

class NotificationType(Enum):
    """Types of notifications that can be displayed."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PROGRESS = "progress"

@dataclass
class Notification:
    """Data class representing a notification."""
    id: str
    type: NotificationType
    title: str
    message: str
    timestamp: datetime
    progress: Optional[int] = None  # For progress notifications (0-100)
    duration: Optional[int] = None  # How long to show in ms, None for persistent
    action_text: Optional[str] = None  # Text for action button
    action_callback: Optional[callable] = None  # Callback for action button

class NotificationService(QObject):
    """Service for managing application notifications."""
    
    # Signals
    notification_added = pyqtSignal(Notification)
    notification_removed = pyqtSignal(str)  # Emits notification ID
    notification_updated = pyqtSignal(Notification)
    
    def __init__(self, parent=None):
        """Initialize the notification service."""
        super().__init__(parent)
        self.notifications: Dict[str, Notification] = {}
        self.notification_history: List[Notification] = []
        self.max_history = 100
        self.system_tray: Optional[QSystemTrayIcon] = None
        
        # Timer for auto-dismissing notifications
        self.dismiss_timer = QTimer(self)
        self.dismiss_timer.timeout.connect(self._check_notifications)
        self.dismiss_timer.start(1000)  # Check every second
    
    def set_system_tray(self, tray: QSystemTrayIcon):
        """Set the system tray icon for showing notifications."""
        self.system_tray = tray
    
    def show_notification(
        self,
        title: str,
        message: str,
        type: NotificationType = NotificationType.INFO,
        duration: Optional[int] = 5000,  # 5 seconds default
        progress: Optional[int] = None,
        action_text: Optional[str] = None,
        action_callback: Optional[callable] = None
    ) -> str:
        """
        Show a new notification.
        
        Args:
            title: Notification title
            message: Notification message
            type: Type of notification
            duration: How long to show in ms (None for persistent)
            progress: Progress value (0-100) for progress notifications
            action_text: Text for action button
            action_callback: Callback for action button
            
        Returns:
            str: Notification ID
        """
        try:
            # Generate unique ID
            notification_id = f"{type.value}_{datetime.now().timestamp()}"
            
            # Create notification
            notification = Notification(
                id=notification_id,
                type=type,
                title=title,
                message=message,
                timestamp=datetime.now(),
                progress=progress,
                duration=duration,
                action_text=action_text,
                action_callback=action_callback
            )
            
            # Store notification
            self.notifications[notification_id] = notification
            
            # Add to history
            self.notification_history.append(notification)
            if len(self.notification_history) > self.max_history:
                self.notification_history.pop(0)
            
            # Show system tray notification if available
            if self.system_tray and self.system_tray.isSystemTrayAvailable():
                icon = self._get_icon_for_type(type)
                self.system_tray.showMessage(
                    title,
                    message,
                    icon,
                    duration if duration else 5000
                )
            
            # Emit signal
            self.notification_added.emit(notification)
            
            logger.info(f"Showed notification: {title}")
            return notification_id
            
        except Exception as e:
            logger.error(f"Error showing notification: {str(e)}")
            return ""
    
    def update_progress(self, notification_id: str, progress: int):
        """
        Update the progress of a progress notification.
        
        Args:
            notification_id: ID of the notification
            progress: New progress value (0-100)
        """
        if notification_id in self.notifications:
            notification = self.notifications[notification_id]
            if notification.type == NotificationType.PROGRESS:
                notification.progress = max(0, min(100, progress))
                self.notification_updated.emit(notification)
    
    def dismiss_notification(self, notification_id: str):
        """
        Dismiss a notification.
        
        Args:
            notification_id: ID of the notification to dismiss
        """
        if notification_id in self.notifications:
            del self.notifications[notification_id]
            self.notification_removed.emit(notification_id)
    
    def get_active_notifications(self) -> List[Notification]:
        """Get list of currently active notifications."""
        return list(self.notifications.values())
    
    def get_notification_history(self) -> List[Notification]:
        """Get list of historical notifications."""
        return self.notification_history.copy()
    
    def clear_all(self):
        """Clear all active notifications."""
        notification_ids = list(self.notifications.keys())
        for notification_id in notification_ids:
            self.dismiss_notification(notification_id)
    
    def _check_notifications(self):
        """Check for notifications that should be auto-dismissed."""
        current_time = datetime.now()
        to_dismiss = []
        
        for notification in self.notifications.values():
            if notification.duration:
                age = (current_time - notification.timestamp).total_seconds() * 1000
                if age >= notification.duration:
                    to_dismiss.append(notification.id)
        
        for notification_id in to_dismiss:
            self.dismiss_notification(notification_id)
    
    def _get_icon_for_type(self, type: NotificationType) -> QSystemTrayIcon.MessageIcon:
        """Get system tray icon for notification type."""
        icon_map = {
            NotificationType.INFO: QSystemTrayIcon.MessageIcon.Information,
            NotificationType.SUCCESS: QSystemTrayIcon.MessageIcon.Information,
            NotificationType.WARNING: QSystemTrayIcon.MessageIcon.Warning,
            NotificationType.ERROR: QSystemTrayIcon.MessageIcon.Critical,
            NotificationType.PROGRESS: QSystemTrayIcon.MessageIcon.Information
        }
        return icon_map.get(type, QSystemTrayIcon.MessageIcon.Information) 