from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QListWidget, QListWidgetItem, QPushButton,
                           QFileDialog, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QIcon, QDrag
import os
import shutil
from utils.logger import logger
from utils.error_handler import handle_errors

class AttachmentListItem(QListWidgetItem):
    """Custom list item for displaying attachment information."""
    
    def __init__(self, attachment_data):
        """
        Initialize attachment list item.
        
        Args:
            attachment_data (dict): Attachment information including filename,
                                  size, content_type, and filepath
        """
        super().__init__()
        self.attachment_data = attachment_data
        self.setText(f"{attachment_data['filename']} ({self._format_size(attachment_data['size'])})")
        self.setToolTip(f"Type: {attachment_data['content_type']}")
    
    def _format_size(self, size_bytes):
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

class AttachmentView(QWidget):
    """Widget for displaying and managing email attachments."""
    
    attachment_saved = pyqtSignal(str)  # Signal emitted when attachment is saved
    
    def __init__(self, parent=None):
        """Initialize attachment view."""
        super().__init__(parent)
        self.attachments = []
        self.setup_ui()
    
    @handle_errors
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        self.header_label = QLabel("Attachments")
        self.header_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self.header_label)
        
        # Save all button
        self.save_all_button = QPushButton("Save All")
        self.save_all_button.clicked.connect(self.save_all_attachments)
        self.save_all_button.setEnabled(False)
        header_layout.addWidget(self.save_all_button)
        
        layout.addLayout(header_layout)
        
        # Attachment list
        self.attachment_list = QListWidget()
        self.attachment_list.setDragEnabled(True)
        self.attachment_list.itemDoubleClicked.connect(self.open_attachment)
        self.attachment_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.attachment_list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.attachment_list)
        
        # Set up drag and drop
        self.attachment_list.setAcceptDrops(True)
        self.attachment_list.setDragDropMode(QListWidget.DragDropMode.DragOnly)
    
    @handle_errors
    def set_attachments(self, attachments):
        """
        Set the attachments to display.
        
        Args:
            attachments (list): List of attachment dictionaries
        """
        self.attachments = attachments or []
        self.attachment_list.clear()
        
        for attachment in self.attachments:
            item = AttachmentListItem(attachment)
            self.attachment_list.addItem(item)
        
        self.save_all_button.setEnabled(bool(self.attachments))
        self.header_label.setText(f"Attachments ({len(self.attachments)})")
    
    @handle_errors
    def save_attachment(self, attachment_data):
        """
        Save an attachment to disk.
        
        Args:
            attachment_data (dict): Attachment information including filepath
        
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Get save location from user
            file_name = attachment_data['filename']
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save Attachment", file_name
            )
            
            if save_path:
                # Copy file to selected location
                shutil.copy2(attachment_data['filepath'], save_path)
                self.attachment_saved.emit(save_path)
                logger.logger.info(f"Saved attachment to {save_path}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving attachment: {str(e)}")
        
        return False
    
    @handle_errors
    def save_all_attachments(self):
        """Save all attachments to a selected directory."""
        if not self.attachments:
            return
        
        # Get directory to save attachments
        save_dir = QFileDialog.getExistingDirectory(
            self, "Select Directory to Save Attachments"
        )
        
        if save_dir:
            success_count = 0
            for attachment in self.attachments:
                try:
                    save_path = os.path.join(save_dir, attachment['filename'])
                    # If file exists, add number to filename
                    base, ext = os.path.splitext(save_path)
                    counter = 1
                    while os.path.exists(save_path):
                        save_path = f"{base}_{counter}{ext}"
                        counter += 1
                    
                    shutil.copy2(attachment['filepath'], save_path)
                    success_count += 1
                    self.attachment_saved.emit(save_path)
                    
                except Exception as e:
                    logger.error(f"Error saving attachment: {str(e)}")
            
            logger.logger.info(f"Saved {success_count} attachments to {save_dir}")
    
    @handle_errors
    def open_attachment(self, item):
        """Open an attachment with the default system application."""
        attachment_data = item.attachment_data
        try:
            os.startfile(attachment_data['filepath'])
            logger.logger.info(f"Opened attachment: {attachment_data['filename']}")
        except Exception as e:
            logger.error(f"Error opening attachment: {str(e)}")
    
    @handle_errors
    def show_context_menu(self, position):
        """Show context menu for attachment list items."""
        item = self.attachment_list.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        open_action = menu.addAction("Open")
        save_action = menu.addAction("Save As...")
        
        action = menu.exec(self.attachment_list.mapToGlobal(position))
        
        if action == open_action:
            self.open_attachment(item)
        elif action == save_action:
            self.save_attachment(item.attachment_data)
    
    def dragEnterEvent(self, event):
        """Handle drag enter events for drag and drop."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Handle drop events for drag and drop."""
        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                # Handle dropped file (for future attachment upload feature)
                pass 