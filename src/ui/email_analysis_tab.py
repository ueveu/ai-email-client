from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                           QTreeWidget, QTreeWidgetItem, QTextEdit, QPushButton,
                           QLabel, QComboBox, QApplication)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QClipboard
from .folder_tree import FolderTree
from .attachment_view import AttachmentView
from email_manager import EmailManager
from utils.logger import logger

class EmailAnalysisTab(QWidget):
    """
    Tab for analyzing emails and generating AI replies.
    Displays email folders, list, content, and suggested replies.
    """
    
    def __init__(self, parent=None):
        """Initialize the email analysis tab."""
        super().__init__(parent)
        self.email_manager = None
        self.current_folder = None
        logger.logger.debug("Initializing EmailAnalysisTab")
        self.setup_ui()
    
    def setup_ui(self):
        """Sets up the UI components for email analysis."""
        layout = QVBoxLayout(self)
        
        # Account selector
        account_layout = QHBoxLayout()
        account_layout.addWidget(QLabel("Email Account:"))
        self.account_selector = QComboBox()
        self.account_selector.currentIndexChanged.connect(self.on_account_changed)
        account_layout.addWidget(self.account_selector)
        account_layout.addStretch()
        layout.addLayout(account_layout)
        
        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Folder tree (leftmost)
        self.folder_tree = FolderTree()
        self.folder_tree.folder_selected.connect(self.on_folder_selected)
        splitter.addWidget(self.folder_tree)
        
        # Email list (middle)
        self.email_tree = QTreeWidget()
        self.email_tree.setHeaderLabels(["Subject", "From", "Date"])
        self.email_tree.itemClicked.connect(self.on_email_selected)
        splitter.addWidget(self.email_tree)
        
        # Right side container with vertical splitter
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Email content and attachments container
        email_content_widget = QWidget()
        email_content_layout = QVBoxLayout(email_content_widget)
        
        # Email content
        self.email_content = QTextEdit()
        self.email_content.setReadOnly(True)
        email_content_layout.addWidget(QLabel("Email Content:"))
        email_content_layout.addWidget(self.email_content)
        
        # Attachment view
        self.attachment_view = AttachmentView()
        self.attachment_view.attachment_saved.connect(self.on_attachment_saved)
        email_content_layout.addWidget(self.attachment_view)
        
        right_splitter.addWidget(email_content_widget)
        
        # AI Reply section
        reply_widget = QWidget()
        reply_layout = QVBoxLayout(reply_widget)
        
        reply_layout.addWidget(QLabel("AI Generated Replies:"))
        self.reply_suggestions = QTextEdit()
        self.reply_suggestions.setReadOnly(True)
        reply_layout.addWidget(self.reply_suggestions)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.generate_reply_btn = QPushButton("Generate Reply")
        self.generate_reply_btn.clicked.connect(self.generate_reply)
        self.copy_reply_btn = QPushButton("Copy to Clipboard")
        self.copy_reply_btn.clicked.connect(self.copy_reply)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_view)
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.generate_reply_btn)
        button_layout.addWidget(self.copy_reply_btn)
        reply_layout.addLayout(button_layout)
        
        right_splitter.addWidget(reply_widget)
        splitter.addWidget(right_splitter)
        
        layout.addWidget(splitter)
        
        # Set initial splitter sizes (25% folders, 35% email list, 40% content)
        splitter.setSizes([250, 350, 400])
        right_splitter.setSizes([600, 400])  # 60% content, 40% replies
    
    def set_email_manager(self, email_manager):
        """Set the email manager and initialize the view."""
        logger.logger.debug(f"Setting email manager: {email_manager}")
        self.email_manager = email_manager
        if self.email_manager:
            # Initialize with INBOX folder
            self.current_folder = 'INBOX'
            self.refresh_view()
        else:
            logger.logger.warning("Email manager is None")
    
    def refresh_view(self):
        """Refresh the entire view including folders and emails."""
        logger.logger.debug("Refreshing view")
        if not self.email_manager:
            logger.logger.warning("No email manager available")
            return
        
        try:
            # Update folder tree
            folders = self.email_manager.list_folders()
            logger.logger.debug(f"Found {len(folders)} folders")
            status_data = {}
            for folder in folders:
                status = self.email_manager.get_folder_status(folder['name'])
                if status:
                    status_data[folder['name']] = status
            
            self.folder_tree.update_folders(folders, status_data)
            
            # Refresh emails in current folder
            if self.current_folder:
                self.refresh_emails()
            else:
                logger.logger.debug("No folder selected for refresh")
        except Exception as e:
            logger.logger.error(f"Error refreshing view: {str(e)}")
    
    def on_account_changed(self, index):
        """Handle account selection change."""
        # Clear current view
        self.email_content.clear()
        self.reply_suggestions.clear()
        self.attachment_view.set_attachments([])
        self.refresh_view()
    
    def on_folder_selected(self, folder_name):
        """Handle folder selection."""
        logger.logger.debug(f"Selected folder: {folder_name}")
        self.current_folder = folder_name
        self.refresh_emails()
    
    def refresh_emails(self):
        """Fetch and display emails for the current folder."""
        logger.logger.debug("Refreshing emails")
        self.email_tree.clear()
        
        if not self.email_manager:
            logger.logger.warning("No email manager available")
            return
        
        if not self.current_folder:
            logger.logger.warning("No folder selected")
            return
        
        try:
            # Fetch emails from the selected folder
            logger.logger.debug(f"Fetching emails from folder: {self.current_folder}")
            emails = self.email_manager.fetch_emails(
                folder=self.current_folder,
                limit=50,
                offset=0
            )
            logger.logger.debug(f"Fetched {len(emails)} emails")
            
            # Add emails to the tree
            for email_data in emails:
                try:
                    logger.logger.debug(f"Adding email: {email_data.get('subject', 'No subject')} from {email_data.get('from', 'Unknown')}")
                    item = QTreeWidgetItem([
                        email_data.get("subject", "No subject"),
                        email_data.get("from", "Unknown"),
                        email_data.get("date", "").strftime("%Y-%m-%d %H:%M") if email_data.get("date") else ""
                    ])
                    item.setData(0, Qt.ItemDataRole.UserRole, email_data)
                    self.email_tree.addTopLevelItem(item)
                except Exception as e:
                    logger.logger.error(f"Error adding email to tree: {str(e)}")
                    logger.logger.error(f"Email data: {email_data}")
            
            logger.logger.debug(f"Email tree now has {self.email_tree.topLevelItemCount()} items")
        except Exception as e:
            logger.logger.error(f"Error refreshing emails: {str(e)}")
    
    def on_email_selected(self, item):
        """Handle email selection from the tree widget."""
        email_data = item.data(0, Qt.ItemDataRole.UserRole)
        if email_data:
            self.email_content.setText(email_data["body"])
            self.reply_suggestions.clear()
            
            # Update attachment view
            attachments = email_data.get("attachments", [])
            self.attachment_view.set_attachments(attachments)
    
    def on_attachment_saved(self, save_path):
        """Handle successful attachment save."""
        logger.logger.info(f"Attachment saved to: {save_path}")
    
    def generate_reply(self):
        """Generate AI reply for the selected email."""
        # TODO: Implement Gemini API integration
        self.reply_suggestions.setText("AI-generated reply suggestions will appear here.")
    
    def copy_reply(self):
        """Copy selected reply to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.reply_suggestions.toPlainText())