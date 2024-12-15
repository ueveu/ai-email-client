from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QScrollArea, QFrame, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from typing import List, Dict
from utils.logger import logger
import os
import mimetypes

class AttachmentView(QWidget):
    """Widget for displaying and managing email attachments."""
    
    attachment_downloaded = pyqtSignal(str)  # Emitted when attachment is downloaded
    
    def __init__(self, parent=None):
        """Initialize the attachment view."""
        super().__init__(parent)
        self.attachments = []
        self.email_manager = None
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header
        header = QLabel("Attachments")
        header.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                padding: 4px 0;
            }
        """)
        layout.addWidget(header)
        
        # Scroll area for attachments
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)
        
        # Container for attachment items
        self.container = QWidget()
        self.container.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(8)
        
        scroll.setWidget(self.container)
        layout.addWidget(scroll)
        
    def set_email_manager(self, email_manager):
        """Set the email manager instance."""
        self.email_manager = email_manager
        
    def set_attachments(self, attachments: List[Dict]):
        """Set and display attachments."""
        self.attachments = attachments
        self.refresh_view()
        
    def refresh_view(self):
        """Refresh the attachment view."""
        # Clear existing items
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Add attachment items
        for attachment in self.attachments:
            try:
                item = self.create_attachment_item(attachment)
                self.container_layout.addWidget(item)
            except Exception as e:
                logger.error(f"Error creating attachment item: {str(e)}")
                
        # Add stretch at the end
        self.container_layout.addStretch()
        
    def create_attachment_item(self, attachment: Dict) -> QWidget:
        """Create a widget for an attachment."""
        item = QWidget()
        item.setStyleSheet("""
            QWidget {
                background-color: #2b2d31;
                border: 1px solid #383a40;
                border-radius: 8px;
            }
            QWidget:hover {
                background-color: #32353a;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #5865f2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
            QPushButton:pressed {
                background-color: #3c45a5;
            }
        """)
        
        layout = QHBoxLayout(item)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Icon based on file type
        icon_label = QLabel()
        icon = self.get_attachment_icon(attachment['content_type'])
        icon_label.setPixmap(icon.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, 
                                       Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(icon_label)
        
        # File info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        filename = QLabel(attachment['filename'])
        filename.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(filename)
        
        details = QLabel(f"{self.format_size(attachment.get('size', 0))} • {attachment['content_type']}")
        details.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        info_layout.addWidget(details)
        
        layout.addLayout(info_layout, stretch=1)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        if self.is_previewable(attachment['content_type']):
            preview_btn = QPushButton("Preview")
            preview_btn.setIcon(QIcon("resources/icons/preview.png"))
            preview_btn.clicked.connect(lambda: self.preview_attachment(attachment))
            buttons_layout.addWidget(preview_btn)
            
        download_btn = QPushButton("Download")
        download_btn.setIcon(QIcon("resources/icons/download.png"))
        download_btn.clicked.connect(lambda: self.download_attachment(attachment))
        buttons_layout.addWidget(download_btn)
        
        layout.addLayout(buttons_layout)
        
        return item
        
    def get_attachment_icon(self, content_type: str) -> QIcon:
        """Get an appropriate icon for the file type."""
        icon_map = {
            'image': 'image.png',
            'audio': 'audio.png',
            'video': 'video.png',
            'text': 'text.png',
            'application/pdf': 'pdf.png',
            'application/msword': 'doc.png',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'doc.png',
            'application/vnd.ms-excel': 'xls.png',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xls.png',
            'application/vnd.ms-powerpoint': 'ppt.png',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'ppt.png',
            'application/zip': 'archive.png',
            'application/x-rar-compressed': 'archive.png',
            'application/x-7z-compressed': 'archive.png'
        }
        
        # Get base type
        base_type = content_type.split('/')[0]
        
        # Find matching icon
        icon_name = icon_map.get(content_type) or icon_map.get(base_type, 'generic.png')
        icon_path = os.path.join('resources', 'icons', icon_name)
        
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        else:
            return QIcon('resources/icons/generic.png')
            
    def format_size(self, size: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
        
    def is_previewable(self, content_type: str) -> bool:
        """Check if the file type can be previewed."""
        previewable_types = [
            'image/',
            'text/',
            'application/pdf'
        ]
        return any(content_type.startswith(t) for t in previewable_types)
        
    def preview_attachment(self, attachment: Dict):
        """Preview an attachment."""
        try:
            if not self.email_manager:
                raise Exception("No email manager available")
                
            # Download to temp location first
            temp_path = self.email_manager.download_attachment(
                attachment['message_id'],
                attachment['part_id'],
                os.path.join(os.path.expanduser('~'), '.ai-email-assistant', 'temp')
            )
            
            # Open with system default application
            os.startfile(temp_path)
            
        except Exception as e:
            logger.error(f"Error previewing attachment: {str(e)}")
            
    def download_attachment(self, attachment: Dict):
        """Download an attachment."""
        try:
            if not self.email_manager:
                raise Exception("No email manager available")
                
            # Get save location from user
            file_name = attachment['filename']
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Attachment",
                os.path.join(os.path.expanduser('~'), 'Downloads', file_name),
                f"All Files (*.*)"
            )
            
            if save_path:
                # Download attachment
                self.email_manager.download_attachment(
                    attachment['message_id'],
                    attachment['part_id'],
                    save_path
                )
                
                self.attachment_downloaded.emit(save_path)
                
        except Exception as e:
            logger.error(f"Error downloading attachment: {str(e)}")