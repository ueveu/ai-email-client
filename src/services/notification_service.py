"""
Service for managing application-wide status notifications.
"""

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap
from enum import Enum
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime
import json
import os
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
    duration: Optional[int] = None  # Duration in milliseconds

class NotificationService(QObject):
    """Service for managing application notifications."""
    
    # Signals for notification events
    notification_added = pyqtSignal(Notification)
    notification_removed = pyqtSignal(str)  # Notification ID
    notification_updated = pyqtSignal(Notification)
    
    def __init__(self):
        """Initialize notification service."""
        super().__init__()
        
        # Initialize notification storage
        self.notifications: List[Notification] = []
        self.active_notifications: Dict[str, Notification] = {}
        
        # Initialize system tray icon if available
        self.tray_icon = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            try:
                self.tray_icon = QSystemTrayIcon()
                
                # Create a default icon if app.png doesn't exist
                icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                       "resources", "icons", "app.png")
                
                if os.path.exists(icon_path):
                    icon = QIcon(icon_path)
                else:
                    # Create a simple default icon
                    pixmap = QPixmap(32, 32)
                    pixmap.fill(QApplication.palette().color(QApplication.palette().Window))
                    icon = QIcon(pixmap)
                
                self.tray_icon.setIcon(icon)
                self.tray_icon.setToolTip("AI Email Assistant")
                
                # Create context menu
                menu = QMenu()
                menu.addAction("Show").triggered.connect(self._show_main_window)
                menu.addAction("Exit").triggered.connect(QApplication.quit)
                self.tray_icon.setContextMenu(menu)
                
                self.tray_icon.show()
                logger.debug("System tray icon initialized successfully")
                
            except Exception as e:
                logger.error(f"Error initializing system tray icon: {str(e)}")
                self.tray_icon = None
    
    def _show_main_window(self):
        """Show the main application window."""
        main_window = QApplication.activeWindow()
        if main_window:
            main_window.show()
            main_window.activateWindow()
    
    def show_notification(self, title: str, message: str, type: NotificationType = NotificationType.INFO,
                        duration: Optional[int] = 5000, progress: Optional[int] = None) -> str:
        """
        Show a notification.
        
        Args:
            title: Notification title
            message: Notification message
            type: Notification type
            duration: Duration in milliseconds (None for persistent)
            progress: Progress value (0-100) for progress notifications
            
        Returns:
            str: Notification ID
        """
        try:
            # Create notification
            notification = Notification(
                id=f"{datetime.now().timestamp()}",
                type=type,
                title=title,
                message=message,
                timestamp=datetime.now(),
                progress=progress,
                duration=duration
            )
            
            # Store notification
            self.notifications.append(notification)
            self.active_notifications[notification.id] = notification
            
            # Emit signal
            self.notification_added.emit(notification)
            
            # Show system tray notification if available
            if self.tray_icon and self.tray_icon.isVisible():
                icon_type = {
                    NotificationType.INFO: QSystemTrayIcon.MessageIcon.Information,
                    NotificationType.SUCCESS: QSystemTrayIcon.MessageIcon.Information,
                    NotificationType.WARNING: QSystemTrayIcon.MessageIcon.Warning,
                    NotificationType.ERROR: QSystemTrayIcon.MessageIcon.Critical,
                    NotificationType.PROGRESS: QSystemTrayIcon.MessageIcon.Information
                }.get(type, QSystemTrayIcon.MessageIcon.Information)
                
                self.tray_icon.showMessage(
                    title,
                    message,
                    icon_type,
                    duration or 5000
                )
            
            # Set up auto-removal timer if duration specified
            if duration:
                QTimer.singleShot(duration, lambda: self.remove_notification(notification.id))
            
            return notification.id
            
        except Exception as e:
            logger.error(f"Error showing notification: {str(e)}")
            return ""
    
    def update_notification(self, notification_id: str, title: Optional[str] = None,
                          message: Optional[str] = None, progress: Optional[int] = None):
        """
        Update an existing notification.
        
        Args:
            notification_id: ID of the notification to update
            title: New title (optional)
            message: New message (optional)
            progress: New progress value (optional)
        """
        try:
            if notification_id not in self.active_notifications:
                return
            
            notification = self.active_notifications[notification_id]
            
            # Update fields
            if title is not None:
                notification.title = title
            if message is not None:
                notification.message = message
            if progress is not None:
                notification.progress = progress
            
            # Emit signal
            self.notification_updated.emit(notification)
            
            # Update system tray notification if available
            if self.tray_icon and self.tray_icon.isVisible() and (title is not None or message is not None):
                icon_type = {
                    NotificationType.INFO: QSystemTrayIcon.MessageIcon.Information,
                    NotificationType.SUCCESS: QSystemTrayIcon.MessageIcon.Information,
                    NotificationType.WARNING: QSystemTrayIcon.MessageIcon.Warning,
                    NotificationType.ERROR: QSystemTrayIcon.MessageIcon.Critical,
                    NotificationType.PROGRESS: QSystemTrayIcon.MessageIcon.Information
                }.get(notification.type, QSystemTrayIcon.MessageIcon.Information)
                
                self.tray_icon.showMessage(
                    notification.title,
                    notification.message,
                    icon_type,
                    notification.duration or 5000
                )
            
        except Exception as e:
            logger.error(f"Error updating notification: {str(e)}")
    
    def remove_notification(self, notification_id: str):
        """
        Remove a notification.
        
        Args:
            notification_id: ID of the notification to remove
        """
        try:
            if notification_id not in self.active_notifications:
                return
            
            # Remove from storage
            notification = self.active_notifications.pop(notification_id)
            if notification in self.notifications:
                self.notifications.remove(notification)
            
            # Emit signal
            self.notification_removed.emit(notification_id)
            
        except Exception as e:
            logger.error(f"Error removing notification: {str(e)}")
    
    def clear_notifications(self):
        """Clear all notifications."""
        try:
            # Get list of IDs to remove
            notification_ids = list(self.active_notifications.keys())
            
            # Remove each notification
            for notification_id in notification_ids:
                self.remove_notification(notification_id)
            
        except Exception as e:
            logger.error(f"Error clearing notifications: {str(e)}")
    
    def get_active_notifications(self) -> List[Notification]:
        """
        Get list of active notifications.
        
        Returns:
            List[Notification]: List of active notifications
        """
        return list(self.active_notifications.values())
    
    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """
        Get a specific notification.
        
        Args:
            notification_id: ID of the notification
            
        Returns:
            Optional[Notification]: Notification if found
        """
        return self.active_notifications.get(notification_id) 