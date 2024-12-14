from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
                           QMenu, QFileDialog, QMessageBox, QLabel, QProgressBar)
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QMimeData
from PyQt6.QtGui import QIcon, QPixmap, QDrag
from utils.logger import logger
from .attachment_preview_dialog import AttachmentPreviewDialog
import os
import mimetypes
import shutil
from typing import List, Dict

class AttachmentView(QWidget):
    """
    Widget for displaying and managing email attachments.
    Supports preview, download, and drag-and-drop operations.
    """
    
    attachment_downloaded = pyqtSignal(str)  # Emitted when attachment is downloaded
    attachment_removed = pyqtSignal(str)     # Emitted when attachment is removed
    attachment_saved = pyqtSignal(str)       # Emitted when attachment is saved to disk
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.attachments = []  # List of attachment data dictionaries
        self.setup_ui()
        
        # Map common MIME types to icons
        self.mime_icons = {
            'image': '🖼️',
            'text': '📄',
            'application/pdf': '📑',
            'audio': '🎵',
            'video': '🎬',
            'application/zip': '📦',
            'application/x-compressed': '📦',
            'application/x-zip-compressed': '📦',
            'default': '📎'
        }
    
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header label
        self.header = QLabel("Attachments")
        self.header.setVisible(False)
        layout.addWidget(self.header)
        
        # Attachment list
        self.list_widget = QListWidget()
        self.list_widget.setDragEnabled(True)
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setIconSize(QSize(32, 32))
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.list_widget.itemDoubleClicked.connect(self.on_attachment_double_clicked)
        layout.addWidget(self.list_widget)
        
        # Progress bar for downloads
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
    
    def show_context_menu(self, position):
        """Show context menu for attachment operations."""
        item = self.list_widget.itemAt(position)
        if not item:
            return
        
        menu = QMenu()
        
        # Add menu actions
        open_action = menu.addAction("Open")
        save_action = menu.addAction("Save As...")
        menu.addSeparator()
        remove_action = menu.addAction("Remove")
        
        # Handle action selection
        action = menu.exec(self.list_widget.mapToGlobal(position))
        if not action:
            return
        
        attachment = self.attachments[self.list_widget.row(item)]
        
        if action == open_action:
            self.open_attachment(attachment)
        elif action == save_action:
            self.save_attachment(attachment)
        elif action == remove_action:
            self.remove_attachment(attachment)
    
    def on_attachment_double_clicked(self, item):
        """Handle double-click on attachment item."""
        attachment = self.attachments[self.list_widget.row(item)]
        self.open_attachment(attachment)
    
    def set_attachments(self, attachments: List[Dict]):
        """
        Set the attachments to display.
        
        Args:
            attachments (List[Dict]): List of attachment data dictionaries
        """
        self.attachments = attachments
        self.list_widget.clear()
        
        if attachments:
            self.header.setVisible(True)
            for attachment in attachments:
                self.add_attachment_item(attachment)
        else:
            self.header.setVisible(False)
    
    def add_attachment_item(self, attachment: Dict):
        """Add an attachment item to the list."""
        item = QListWidgetItem()
        
        # Set icon based on MIME type
        mime_type = attachment.get('content_type', 'application/octet-stream')
        icon_key = next(
            (k for k in self.mime_icons if k in mime_type.lower()),
            'default'
        )
        item.setText(f"{self.mime_icons[icon_key]} {attachment['filename']}")
        
        # Add size information
        size = attachment.get('size', 0)
        if size:
            size_str = self.format_size(size)
            item.setToolTip(f"{attachment['filename']} ({size_str})")
        
        self.list_widget.addItem(item)
    
    def format_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def open_attachment(self, attachment: Dict):
        """Open an attachment with the default system application."""
        try:
            filepath = attachment.get('filepath') or attachment.get('local_path')
            if not filepath or not os.path.exists(filepath):
                QMessageBox.warning(
                    self,
                    "Error",
                    "Attachment file not found."
                )
                return
            
            # Open with default application
            import platform
            if platform.system() == 'Windows':
                os.startfile(filepath)
            elif platform.system() == 'Darwin':  # macOS
                os.system(f'open "{filepath}"')
            else:  # Linux
                os.system(f'xdg-open "{filepath}"')
            
            self.attachment_downloaded.emit(filepath)
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to open attachment: {str(e)}"
            )
    
    def save_attachment(self, attachment: Dict):
        """Save attachment to user-selected location."""
        try:
            # Get source filepath
            source = attachment.get('filepath') or attachment.get('local_path')
            if not source or not os.path.exists(source):
                QMessageBox.warning(
                    self,
                    "Error",
                    "Attachment file not found."
                )
                return
            
            # Get save location
            filename = attachment['filename']
            target, _ = QFileDialog.getSaveFileName(
                self,
                "Save Attachment",
                filename,
                "All Files (*.*)"
            )
            
            if not target:
                return
            
            # Copy file
            shutil.copy2(source, target)
            self.attachment_saved.emit(target)
            
            QMessageBox.information(
                self,
                "Success",
                f"Attachment saved to {target}"
            )
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to save attachment: {str(e)}"
            )
    
    def remove_attachment(self, attachment: Dict):
        """Remove an attachment from the list."""
        try:
            # Confirm removal
            reply = QMessageBox.question(
                self,
                "Remove Attachment",
                f"Remove attachment {attachment['filename']}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return
            
            # Remove from list
            index = self.attachments.index(attachment)
            self.attachments.pop(index)
            self.list_widget.takeItem(index)
            
            # Update header visibility
            self.header.setVisible(bool(self.attachments))
            
            self.attachment_removed.emit(attachment['filename'])
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to remove attachment: {str(e)}"
            )
    
    def dragEnterEvent(self, event):
        """Handle drag enter event for attachment drag-and-drop."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Handle drop event for attachment drag-and-drop."""
        try:
            for url in event.mimeData().urls():
                filepath = url.toLocalFile()
                if os.path.isfile(filepath):
                    # Create attachment data
                    filename = os.path.basename(filepath)
                    mime_type, _ = mimetypes.guess_type(filepath)
                    size = os.path.getsize(filepath)
                    
                    attachment = {
                        'filename': filename,
                        'content_type': mime_type or 'application/octet-stream',
                        'size': size,
                        'filepath': filepath
                    }
                    
                    # Add to list
                    self.attachments.append(attachment)
                    self.add_attachment_item(attachment)
                    self.header.setVisible(True)
            
            event.acceptProposedAction()
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to add attachment: {str(e)}"
            )