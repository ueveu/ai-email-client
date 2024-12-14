"""
Widget for displaying application status, notifications, and operations.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                           QLabel, QFrame, QSizePolicy, QSpacerItem)
from PyQt6.QtCore import Qt, QSize, pyqtSlot, QPropertyAnimation, QRect
from PyQt6.QtGui import QIcon
from services.notification_service import NotificationService
from services.email_operation_service import EmailOperationService
from .notification_widget import NotificationWidget
from .operation_status_widget import OperationStatusWidget
import qtawesome as qta

class StatusBarWidget(QWidget):
    """Widget for displaying application status, notifications, and operations."""
    
    def __init__(self, notification_service: NotificationService,
                 operation_service: EmailOperationService, parent=None):
        super().__init__(parent)
        self.notification_service = notification_service
        self.operation_service = operation_service
        
        # Track active items
        self.active_notifications = 0
        self.active_operations = 0
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Set up the status bar UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Status bar
        self.status_bar = QFrame()
        self.status_bar.setFrameStyle(QFrame.Shape.NoFrame)
        self.status_bar.setStyleSheet("""
            QFrame {
                background-color: palette(window);
                border-top: 1px solid palette(mid);
            }
        """)
        
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(8, 4, 8, 4)
        
        # Status indicators
        self.notification_indicator = self._create_indicator(
            "fa.bell",
            "Notifications",
            "Click to show/hide notifications"
        )
        status_layout.addWidget(self.notification_indicator)
        
        self.operation_indicator = self._create_indicator(
            "fa.tasks",
            "Operations",
            "Click to show/hide active operations"
        )
        status_layout.addWidget(self.operation_indicator)
        
        # Spacer
        status_layout.addStretch()
        
        # Add status bar to main layout
        layout.addWidget(self.status_bar)
        
        # Detail panel (notifications and operations)
        self.detail_panel = QFrame()
        self.detail_panel.setFrameStyle(QFrame.Shape.NoFrame)
        self.detail_panel.setStyleSheet("""
            QFrame {
                background-color: palette(window);
                border-top: 1px solid palette(mid);
            }
        """)
        
        panel_layout = QHBoxLayout(self.detail_panel)
        panel_layout.setContentsMargins(8, 8, 8, 8)
        panel_layout.setSpacing(16)
        
        # Notifications section
        self.notification_widget = NotificationWidget(self.notification_service)
        self.notification_widget.setVisible(False)
        panel_layout.addWidget(self.notification_widget)
        
        # Vertical separator
        separator = QFrame()
        separator.setFrameStyle(QFrame.Shape.VLine)
        separator.setStyleSheet("QFrame { color: palette(mid); }")
        panel_layout.addWidget(separator)
        
        # Operations section
        self.operation_widget = OperationStatusWidget(self.operation_service)
        self.operation_widget.setVisible(False)
        panel_layout.addWidget(self.operation_widget)
        
        # Initially hide detail panel
        self.detail_panel.setMaximumHeight(0)
        layout.addWidget(self.detail_panel)
    
    def _create_indicator(self, icon_name: str, text: str, tooltip: str) -> QPushButton:
        """Create a status bar indicator button."""
        btn = QPushButton()
        btn.setIcon(qta.icon(icon_name))
        btn.setText(text)
        btn.setToolTip(tooltip)
        btn.setFlat(True)
        btn.setCheckable(True)
        btn.setStyleSheet("""
            QPushButton {
                padding: 4px 8px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: palette(mid);
            }
            QPushButton:checked {
                background-color: palette(highlight);
                color: palette(highlighted-text);
            }
        """)
        return btn
    
    def connect_signals(self):
        """Connect widget signals."""
        # Connect indicator buttons
        self.notification_indicator.toggled.connect(
            lambda checked: self.toggle_section('notifications', checked)
        )
        self.operation_indicator.toggled.connect(
            lambda checked: self.toggle_section('operations', checked)
        )
        
        # Connect notification service signals
        self.notification_service.notification_added.connect(
            lambda notif: self.on_notification_added(notif)
        )
        self.notification_service.notification_removed.connect(
            lambda notif_id: self.on_notification_removed(notif_id)
        )
        
        # Connect operation service signals
        self.operation_service.operation_started.connect(
            lambda op_id, op_type: self.on_operation_started(op_id, op_type)
        )
        self.operation_service.operation_completed.connect(
            lambda op_id, success, msg: self.on_operation_completed(op_id, success, msg)
        )
    
    def toggle_section(self, section: str, show: bool):
        """Toggle visibility of a section."""
        if section == 'notifications':
            self.notification_widget.setVisible(show)
            if not show:
                self.notification_indicator.setChecked(False)
        elif section == 'operations':
            self.operation_widget.setVisible(show)
            if not show:
                self.operation_indicator.setChecked(False)
        
        # Show/hide detail panel based on section visibility
        show_panel = (self.notification_widget.isVisible() or
                     self.operation_widget.isVisible())
        
        # Animate panel height
        target_height = 300 if show_panel else 0
        self._animate_panel_height(target_height)
    
    def _animate_panel_height(self, target_height: int):
        """Animate the detail panel height."""
        animation = QPropertyAnimation(self.detail_panel, b"maximumHeight")
        animation.setDuration(200)
        animation.setStartValue(self.detail_panel.height())
        animation.setEndValue(target_height)
        animation.start()
    
    @pyqtSlot()
    def on_notification_added(self, notification):
        """Handle new notification."""
        self.active_notifications += 1
        self._update_notification_indicator()
    
    @pyqtSlot()
    def on_notification_removed(self, notification_id):
        """Handle notification removal."""
        self.active_notifications = max(0, self.active_notifications - 1)
        self._update_notification_indicator()
    
    @pyqtSlot()
    def on_operation_started(self, _, __):
        """Handle operation started."""
        self.active_operations += 1
        self._update_operation_indicator()
    
    @pyqtSlot()
    def on_operation_completed(self, _, __, ___):
        """Handle operation completed."""
        self.active_operations = max(0, self.active_operations - 1)
        self._update_operation_indicator()
    
    def _update_notification_indicator(self):
        """Update notification indicator appearance."""
        if self.active_notifications > 0:
            self.notification_indicator.setIcon(qta.icon("fa.bell"))
            self.notification_indicator.setText(
                f"Notifications ({self.active_notifications})"
            )
        else:
            self.notification_indicator.setIcon(qta.icon("fa.bell-o"))
            self.notification_indicator.setText("Notifications")
    
    def _update_operation_indicator(self):
        """Update operation indicator appearance."""
        if self.active_operations > 0:
            self.operation_indicator.setIcon(qta.icon("fa.tasks"))
            self.operation_indicator.setText(
                f"Operations ({self.active_operations})"
            )
            # Auto-show operations panel
            if not self.operation_widget.isVisible():
                self.operation_indicator.setChecked(True)
                self.toggle_section('operations', True)
        else:
            self.operation_indicator.setIcon(qta.icon("fa.check"))
            self.operation_indicator.setText("Operations")
            # Auto-hide operations panel if empty
            if self.operation_widget.isVisible():
                self.operation_indicator.setChecked(False)
                self.toggle_section('operations', False) 