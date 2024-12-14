"""
Widget for displaying active email operations and their progress.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSlot
from services.email_operation_service import EmailOperationService, OperationType
import qtawesome as qta

class OperationStatusWidget(QWidget):
    """Widget for displaying active operations and their progress."""
    
    def __init__(self, operation_service: EmailOperationService, parent=None):
        super().__init__(parent)
        self.operation_service = operation_service
        
        # Connect signals
        self.operation_service.operation_started.connect(self.on_operation_started)
        self.operation_service.operation_updated.connect(self.on_operation_progress)
        self.operation_service.operation_completed.connect(self.on_operation_completed)
        
        self.operation_widgets = {}  # operation_id -> widget mapping
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the operations widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("Active Operations")
        title.setStyleSheet("font-weight: bold;")
        header.addWidget(title)
        
        # Clear completed button
        clear_btn = QPushButton("Clear Completed")
        clear_btn.setIcon(qta.icon("fa.check"))
        clear_btn.clicked.connect(self.clear_completed)
        header.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        layout.addLayout(header)
        
        # Container for operation items
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(4)
        
        layout.addWidget(self.container)
        layout.addStretch()
    
    @pyqtSlot(str, OperationType)
    def on_operation_started(self, operation_id: str, operation_type: OperationType):
        """Handle new operation started."""
        # Create operation widget
        widget = QWidget()
        widget_layout = QVBoxLayout(widget)
        widget_layout.setContentsMargins(8, 8, 8, 8)
        widget_layout.setSpacing(4)
        
        # Header with title and cancel button
        header = QHBoxLayout()
        
        # Operation icon and title
        icon_map = {
            OperationType.SEND: "fa.paper-plane",
            OperationType.FETCH: "fa.download",
            OperationType.SYNC: "fa.refresh",
            OperationType.MOVE: "fa.arrows",
            OperationType.DELETE: "fa.trash",
            OperationType.SEARCH: "fa.search",
            OperationType.ATTACHMENT: "fa.paperclip",
            OperationType.FOLDER: "fa.folder"
        }
        title_map = {
            OperationType.SEND: "Sending Email",
            OperationType.FETCH: "Fetching Emails",
            OperationType.SYNC: "Synchronizing Folder",
            OperationType.MOVE: "Moving Email",
            OperationType.DELETE: "Deleting Email",
            OperationType.SEARCH: "Searching Emails",
            OperationType.ATTACHMENT: "Processing Attachment",
            OperationType.FOLDER: "Managing Folder"
        }
        
        icon = qta.icon(icon_map.get(operation_type, "fa.cog"))
        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(16, 16))
        header.addWidget(icon_label)
        
        title = QLabel(title_map.get(operation_type, "Operation"))
        header.addWidget(title)
        header.addStretch()
        
        # Cancel button
        cancel_btn = QPushButton()
        cancel_btn.setIcon(qta.icon("fa.times"))
        cancel_btn.setFlat(True)
        cancel_btn.setFixedSize(16, 16)
        cancel_btn.clicked.connect(
            lambda: self.operation_service.cancel_operation(operation_id)
        )
        header.addWidget(cancel_btn)
        
        widget_layout.addLayout(header)
        
        # Status label
        status_label = QLabel()
        status_label.setObjectName("status")
        widget_layout.addWidget(status_label)
        
        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setObjectName("progress")
        widget_layout.addWidget(progress_bar)
        
        # Store widget
        self.operation_widgets[operation_id] = widget
        self.container_layout.addWidget(widget)
        
        # Update status
        self.update_operation_status(operation_id)
    
    @pyqtSlot(str, int)
    def on_operation_progress(self, operation_id: str, progress: int):
        """Handle operation progress update."""
        if operation_id in self.operation_widgets:
            widget = self.operation_widgets[operation_id]
            
            # Update progress bar
            progress_bar = widget.findChild(QProgressBar, "progress")
            if progress_bar:
                progress_bar.setValue(progress)
            
            # Update status label
            self.update_operation_status(operation_id)
    
    @pyqtSlot(str, bool, str)
    def on_operation_completed(self, operation_id: str, success: bool, message: str):
        """Handle operation completion."""
        if operation_id in self.operation_widgets:
            widget = self.operation_widgets[operation_id]
            
            # Update status label
            status_label = widget.findChild(QLabel, "status")
            if status_label:
                status_label.setText(message)
                status_label.setStyleSheet(
                    "color: #4CAF50;" if success else "color: #F44336;"
                )
            
            # Update progress bar
            progress_bar = widget.findChild(QProgressBar, "progress")
            if progress_bar:
                progress_bar.setValue(100 if success else 0)
                progress_bar.setStyleSheet(
                    "QProgressBar::chunk { background-color: #4CAF50; }"
                    if success else
                    "QProgressBar::chunk { background-color: #F44336; }"
                )
            
            # Remove widget after delay
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(5000, lambda: self.remove_operation(operation_id))
    
    def update_operation_status(self, operation_id: str):
        """Update the status display for an operation."""
        status = self.operation_service.get_operation_status(operation_id)
        if not status:
            return
        
        widget = self.operation_widgets.get(operation_id)
        if not widget:
            return
        
        # Update status label
        status_label = widget.findChild(QLabel, "status")
        if status_label:
            status_label.setText(status.get("status", ""))
    
    def remove_operation(self, operation_id: str):
        """Remove an operation widget."""
        if operation_id in self.operation_widgets:
            widget = self.operation_widgets[operation_id]
            self.container_layout.removeWidget(widget)
            widget.deleteLater()
            del self.operation_widgets[operation_id]
    
    def clear_completed(self):
        """Clear all completed operations."""
        # Get list of completed operations
        completed = []
        for operation_id, widget in self.operation_widgets.items():
            progress_bar = widget.findChild(QProgressBar, "progress")
            if progress_bar and progress_bar.value() == 100:
                completed.append(operation_id)
        
        # Remove completed operations
        for operation_id in completed:
            self.remove_operation(operation_id) 