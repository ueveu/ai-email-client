from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
                           QMenu, QFileDialog, QMessageBox, QLabel, QProgressBar)
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QMimeData
from PyQt6.QtGui import QIcon, QPixmap, QDrag
from utils.logger import logger
from .attachment_preview_dialog import AttachmentPreviewDialog
import os
import mimetypes
import shutil

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
    
    def set_attachments(self, attachments):
        """Set the list of attachments to display."""
        self.attachments = attachments or []
        self.update_list()
    
    def update_list(self):
        """Update the attachment list display."""
        self.list_widget.clear()
        self.header.setVisible(bool(self.attachments))
        
        for attachment in self.attachments:
            item = QListWidgetItem()
            
            # Get appropriate icon based on MIME type
            mime_type = attachment.get('content_type', 'application/octet-stream')
            icon = self.get_mime_icon(mime_type)
            
            # Set item properties
            item.setText(f"{icon} {attachment['filename']} ({self.format_size(attachment.get('size', 0))})")
            item.setData(Qt.ItemDataRole.UserRole, attachment)
            
            self.list_widget.addItem(item)
    
    def get_mime_icon(self, mime_type):
        """Get appropriate icon for MIME type."""
        main_type = mime_type.split('/')[0]
        
        if mime_type in self.mime_icons:
            return self.mime_icons[mime_type]
        elif main_type in self.mime_icons:
            return self.mime_icons[main_type]
        return self.mime_icons['default']
    
    def format_size(self, size_bytes):
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def show_context_menu(self, position):
        """Show context menu for attachment operations."""
        item = self.list_widget.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        
        # Add menu actions
        preview_action = menu.addAction("Preview")
        download_action = menu.addAction("Download")
        menu.addSeparator()
        remove_action = menu.addAction("Remove")
        
        # Handle action selection
        action = menu.exec(self.list_widget.mapToGlobal(position))
        if not action:
            return
        
        attachment = item.data(Qt.ItemDataRole.UserRole)
        
        if action == preview_action:
            self.preview_attachment(attachment)
        elif action == download_action:
            self.download_attachment(attachment)
        elif action == remove_action:
            self.remove_attachment(attachment)
    
    def on_attachment_double_clicked(self, item):
        """Handle double-click on attachment item."""
        attachment = item.data(Qt.ItemDataRole.UserRole)
        self.preview_attachment(attachment)
    
    def preview_attachment(self, attachment):
        """Preview an attachment using the AttachmentPreviewDialog."""
        try:
            preview_dialog = AttachmentPreviewDialog(attachment, self)
            preview_dialog.exec()
        except Exception as e:
            logger.error(f"Error previewing attachment: {str(e)}")
            QMessageBox.warning(
                self,
                "Preview Failed",
                f"Failed to preview attachment:\n{str(e)}"
            )
    
    def download_attachment(self, attachment):
        """Download an attachment to local storage."""
        # Get download location from user
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Attachment",
            attachment['filename']
        )
        
        if not file_path:
            return
        
        try:
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # Copy file to destination
            source_path = attachment.get('path')
            if source_path and os.path.exists(source_path):
                shutil.copy2(source_path, file_path)
                self.attachment_downloaded.emit(file_path)
                self.attachment_saved.emit(file_path)  # Emit saved signal
                
                QMessageBox.information(
                    self,
                    "Download Complete",
                    f"Attachment saved to:\n{file_path}"
                )
            else:
                raise FileNotFoundError("Attachment file not found")
                
        except Exception as e:
            logger.error(f"Error downloading attachment: {str(e)}")
            QMessageBox.warning(
                self,
                "Download Failed",
                f"Failed to download attachment:\n{str(e)}"
            )
        finally:
            self.progress_bar.setVisible(False)
    
    def remove_attachment(self, attachment):
        """Remove an attachment from the list."""
        reply = QMessageBox.question(
            self,
            "Remove Attachment",
            f"Remove attachment '{attachment['filename']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Find and remove the attachment
            for i, att in enumerate(self.attachments):
                if att['filename'] == attachment['filename']:
                    self.attachments.pop(i)
                    break
            
            self.update_list()
            self.attachment_removed.emit(attachment['filename'])
    
    def dragEnterEvent(self, event):
        """Handle drag enter events for file drops."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Handle file drops for adding attachments."""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.exists(file_path):
                # Create attachment data
                mime_type, _ = mimetypes.guess_type(file_path)
                attachment = {
                    'filename': os.path.basename(file_path),
                    'path': file_path,
                    'content_type': mime_type or 'application/octet-stream',
                    'size': os.path.getsize(file_path)
                }
                
                self.attachments.append(attachment)
        
        self.update_list()
        event.acceptProposedAction()