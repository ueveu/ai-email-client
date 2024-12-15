"""
Widget for displaying application notifications.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QProgressBar, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSlot, QPropertyAnimation
from PyQt6.QtGui import QIcon, QColor, QPalette
from services.notification_service import NotificationService, Notification, NotificationType
from typing import Dict
import qtawesome as qta

class NotificationItemWidget(QWidget):
    """Widget for displaying a single notification."""
    
    def __init__(self, notification: Notification, parent=None):
        super().__init__(parent)
        self.notification = notification
        self.setup_ui()
        
        # Add fade-in animation
        self.setWindowOpacity(0)
        self.fade_in()
    
    def fade_in(self):
        """Animate fade-in effect for the notification."""
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.start()
    
    def setup_ui(self):
        """Set up the notification item UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Header layout
        header = QHBoxLayout()
        
        # Icon
        icon_map = {
            NotificationType.INFO: "fa.info-circle",
            NotificationType.SUCCESS: "fa.check-circle",
            NotificationType.WARNING: "fa.exclamation-triangle",
            NotificationType.ERROR: "fa.times-circle",
            NotificationType.PROGRESS: "fa.spinner fa-spin"
        }
        color_map = {
            NotificationType.INFO: "#2196F3",
            NotificationType.SUCCESS: "#4CAF50",
            NotificationType.WARNING: "#FFC107",
            NotificationType.ERROR: "#F44336",
            NotificationType.PROGRESS: "#2196F3"
        }
        
        icon = qta.icon(
            icon_map.get(self.notification.type, "fa.info-circle"),
            color=color_map.get(self.notification.type, "#2196F3")
        )
        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(16, 16))
        header.addWidget(icon_label)
        
        # Title
        title = QLabel(self.notification.title)
        title.setStyleSheet("font-weight: bold;")
        header.addWidget(title, stretch=1)
        
        # Close button
        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa.times"))
        close_btn.setFlat(True)
        close_btn.setFixedSize(16, 16)
        close_btn.clicked.connect(self.close_notification)
        header.addWidget(close_btn)
        
        layout.addLayout(header)
        
        # Message
        message = QLabel(self.notification.message)
        message.setWordWrap(True)
        layout.addWidget(message)
        
        # Progress bar for progress notifications
        if self.notification.type == NotificationType.PROGRESS:
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(self.notification.progress or 0)
            layout.addWidget(progress)
        
        # Action button if provided
        if self.notification.action_text and self.notification.action_callback:
            action_btn = QPushButton(self.notification.action_text)
            action_btn.clicked.connect(self.notification.action_callback)
            layout.addWidget(action_btn)
        
        # Set background color based on type
        self.setAutoFillBackground(True)
        palette = self.palette()
        color = QColor(color_map.get(self.notification.type, "#2196F3"))
        color.setAlpha(20)
        palette.setColor(QPalette.ColorRole.Window, color)
        self.setPalette(palette)
    
    def close_notification(self):
        """Close this notification."""
        self.parent().parent().parent().dismiss_notification(self.notification.id)

class NotificationWidget(QWidget):
    """Widget for displaying all notifications."""
    
    def __init__(self, notification_service: NotificationService, parent=None):
        super().__init__(parent)
        self.notification_service = notification_service
        self.notification_widgets: Dict[str, NotificationItemWidget] = {}
        
        # Connect signals
        self.notification_service.notification_added.connect(self.add_notification)
        self.notification_service.notification_removed.connect(self.remove_notification)
        self.notification_service.notification_updated.connect(self.update_notification)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the notifications widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Scroll area for notifications
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Container for notification items
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(8, 8, 8, 8)
        self.container_layout.setSpacing(8)
        self.container_layout.addStretch()
        
        scroll.setWidget(self.container)
        layout.addWidget(scroll)
    
    @pyqtSlot(Notification)
    def add_notification(self, notification: Notification):
        """Add a new notification to the widget."""
        item = NotificationItemWidget(notification)
        self.notification_widgets[notification.id] = item
        
        # Insert before the stretch
        self.container_layout.insertWidget(
            self.container_layout.count() - 1,
            item
        )
    
    @pyqtSlot(str)
    def remove_notification(self, notification_id: str):
        """Remove a notification from the widget."""
        if notification_id in self.notification_widgets:
            widget = self.notification_widgets[notification_id]
            self.container_layout.removeWidget(widget)
            widget.deleteLater()
            del self.notification_widgets[notification_id]
    
    @pyqtSlot(Notification)
    def update_notification(self, notification: Notification):
        """Update an existing notification."""
        if notification.id in self.notification_widgets:
            # Remove old widget
            self.remove_notification(notification.id)
            # Add updated widget
            self.add_notification(notification)
    
    def dismiss_notification(self, notification_id: str):
        """Dismiss a notification."""
        self.notification_service.dismiss_notification(notification_id) 