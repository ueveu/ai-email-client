"""
Dialog for previewing email attachments.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton,
                           QScrollArea, QWidget, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage
import os
import mimetypes
from utils.logger import logger

class AttachmentPreviewDialog(QDialog):
    """Dialog for previewing email attachments."""
    
    def __init__(self, parent=None, attachment_path=None):
        """
        Initialize dialog.
        
        Args:
            parent: Parent widget
            attachment_path (str): Path to attachment file
        """
        super().__init__(parent)
        self.attachment_path = attachment_path
        self.setup_ui()
        
        if attachment_path:
            self.load_attachment(attachment_path)
    
    def setup_ui(self):
        """Set up the dialog UI components."""
        self.setWindowTitle("Attachment Preview")
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        
        # Preview label
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.preview_label)
        
        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll)
        
        # Buttons
        button_layout = QVBoxLayout()
        
        save_btn = QPushButton("Save As...")
        save_btn.clicked.connect(self.save_attachment)
        button_layout.addWidget(save_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def load_attachment(self, path):
        """
        Load and display attachment content.
        
        Args:
            path (str): Path to attachment file
        """
        try:
            mime_type, _ = mimetypes.guess_type(path)
            
            if not mime_type:
                self.preview_label.setText("Unknown file type")
                return
            
            if mime_type.startswith('image/'):
                # Load and display image
                pixmap = QPixmap(path)
                if pixmap.isNull():
                    self.preview_label.setText("Failed to load image")
                    return
                
                # Scale image to fit dialog while maintaining aspect ratio
                scaled = pixmap.scaled(
                    self.width() - 50,
                    self.height() - 100,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled)
                
            elif mime_type.startswith('text/'):
                # Load and display text content
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.preview_label.setText(content)
                except Exception as e:
                    self.preview_label.setText(f"Failed to load text content: {str(e)}")
                    
            else:
                self.preview_label.setText(
                    f"Preview not available for this file type: {mime_type}\n"
                    "Use 'Save As...' to save and open with appropriate application."
                )
                
        except Exception as e:
            logger.error(f"Failed to load attachment: {str(e)}")
            self.preview_label.setText(f"Failed to load attachment: {str(e)}")
    
    def save_attachment(self):
        """Save attachment to user-selected location."""
        if not self.attachment_path or not os.path.exists(self.attachment_path):
            return
        
        try:
            filename = os.path.basename(self.attachment_path)
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Attachment",
                filename
            )
            
            if save_path:
                # Copy file to new location
                with open(self.attachment_path, 'rb') as src, open(save_path, 'wb') as dst:
                    dst.write(src.read())
                    
        except Exception as e:
            logger.error(f"Failed to save attachment: {str(e)}") 