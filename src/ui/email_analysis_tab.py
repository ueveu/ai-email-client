from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                           QTreeWidget, QTreeWidgetItem, QTextEdit, QPushButton,
                           QLabel, QComboBox, QApplication, QMessageBox,
                           QRadioButton, QButtonGroup, QTabWidget, QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QClipboard
from datetime import datetime
from typing import List, Dict, Optional
from .folder_tree import FolderTree
from .email_list_view import EmailListView
from .attachment_view import AttachmentView
from .conversation_analysis_widget import ConversationAnalysisWidget
from .loading_spinner import LoadingSpinner
from email_manager import EmailManager
from utils.logger import logger
from services.ai_service import AIService

class EmailAnalysisTab(QWidget):
    """Widget for analyzing and displaying email content with AI assistance."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.email_manager = None
        self.accounts = []
        self.current_folder = 'INBOX'
        self.ai_service = AIService()
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        
        # Account selector
        account_layout = QHBoxLayout()
        account_label = QLabel("Account:")
        self.account_selector = QComboBox()
        self.account_selector.currentIndexChanged.connect(self.on_account_changed)
        account_layout.addWidget(account_label)
        account_layout.addWidget(self.account_selector)
        account_layout.addStretch()
        layout.addLayout(account_layout)
        
        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Folder tree
        self.folder_tree = FolderTree()
        self.folder_tree.folder_selected.connect(self.on_folder_selected)
        splitter.addWidget(self.folder_tree)
        
        # Middle - Email list
        self.email_list = EmailListView()
        self.email_list.email_selected.connect(self.on_email_selected)
        splitter.addWidget(self.email_list)
        
        # Right side - Email content and analysis
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # Email content viewer
        self.email_content = QTextEdit()
        self.email_content.setReadOnly(True)
        content_layout.addWidget(self.email_content)
        
        # Attachment view
        self.attachment_view = AttachmentView()
        content_layout.addWidget(self.attachment_view)
        
        # AI Analysis section
        analysis_group = QGroupBox("AI Analysis")
        analysis_layout = QVBoxLayout()
        
        # Reply suggestions
        self.reply_suggestions = QTextEdit()
        self.reply_suggestions.setPlaceholderText("AI-generated reply suggestions will appear here...")
        self.reply_suggestions.setReadOnly(True)
        analysis_layout.addWidget(self.reply_suggestions)
        
        analysis_group.setLayout(analysis_layout)
        content_layout.addWidget(analysis_group)
        
        splitter.addWidget(content_widget)
        
        # Set reasonable sizes for splitter
        splitter.setSizes([200, 300, 400])
        layout.addWidget(splitter)
        
        # Loading spinner
        self.loading_spinner = LoadingSpinner(self)
        self.loading_spinner.hide()
        
        # Welcome message (shown when no accounts)
        self.welcome_label = QLabel(
            "Welcome to AI Email Assistant!\n\n"
            "To get started, add an email account by clicking:\n"
            "File > Add Email Account"
        )
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.welcome_label.setStyleSheet("""
            QLabel {
                font-size: 14pt;
                color: #666;
                padding: 20px;
                background: #f5f5f5;
                border-radius: 10px;
            }
        """)
        layout.addWidget(self.welcome_label)
        self.welcome_label.hide()  # Hidden by default
        
    def set_accounts(self, accounts: list):
        """Set the available email accounts."""
        self.accounts = accounts
        self.account_selector.clear()
        
        for account in accounts:
            self.account_selector.addItem(account['email'])
        
        # Show/hide welcome message based on accounts
        if not accounts:
            self.welcome_label.show()
            self.folder_tree.hide()
            self.email_list.hide()
            self.email_content.hide()
            self.attachment_view.hide()
        else:
            self.welcome_label.hide()
            self.folder_tree.show()
            self.email_list.show()
            self.email_content.show()
            self.attachment_view.show()
    
    def set_active_account(self, index: int):
        """Set the active account by index."""
        if 0 <= index < len(self.accounts):
            self.account_selector.setCurrentIndex(index)
            
    def set_email_manager(self, email_manager):
        """Set the email manager instance."""
        self.email_manager = email_manager
        self.folder_tree.set_email_manager(email_manager)
        self.email_list.set_email_manager(email_manager)
        self.refresh_view()
        
    def on_account_changed(self, index: int):
        """Handle account selection changes."""
        if index < 0 or not self.email_manager:
            return
            
        try:
            # Set active account in email manager
            account = self.accounts[index]
            self.email_manager.set_active_account(account)
            
            # Clear current view
            self.email_content.clear()
            self.reply_suggestions.clear()
            self.attachment_view.set_attachments([])
            
            # Reset folder tree for new account
            self.folder_tree.set_email_manager(self.email_manager)
            self.current_folder = 'INBOX'
            
            # Refresh view with new account
            self.refresh_view()
            
            logger.debug(f"Switched to account: {account['email']}")
        except Exception as e:
            logger.error(f"Error changing account: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to switch account: {str(e)}"
            )
    
    def refresh_view(self):
        """Refresh the entire view including folders and emails."""
        logger.debug("Refreshing view")
        if not self.email_manager:
            logger.warning("No email manager available")
            return
        
        try:
            # Show loading state
            self.loading_spinner.start()
            QApplication.processEvents()
            
            # Update folder tree
            folders = self.email_manager.list_folders()
            logger.debug(f"Found {len(folders)} folders")
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
                logger.debug("No folder selected for refresh")
                
        except Exception as e:
            logger.error(f"Error refreshing view: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to refresh view: {str(e)}"
            )
        finally:
            self.loading_spinner.stop()
    
    def on_folder_selected(self, folder_name: str):
        """Handle folder selection."""
        logger.debug(f"Selected folder: {folder_name}")
        self.current_folder = folder_name
        self.refresh_emails()
    
    def refresh_emails(self):
        """Fetch and display emails for the current folder."""
        logger.debug("Refreshing emails")
        self.email_list.clear()
        
        if not self.email_manager:
            logger.warning("No email manager available")
            return
        
        if not self.current_folder:
            logger.warning("No folder selected")
            return
        
        try:
            # Show loading state
            self.loading_spinner.start()
            QApplication.processEvents()
            
            # Fetch emails from the selected folder
            logger.debug(f"Fetching emails from folder: {self.current_folder}")
            emails = self.email_manager.fetch_emails(self.current_folder)
            
            if not emails:
                logger.warning("No emails found in folder")
                self.email_content.setPlainText("No emails found in this folder.")
                return
                
            logger.debug(f"Found {len(emails)} emails")
            
            # Update email list view
            self.email_list.set_emails(emails)
            
        except Exception as e:
            logger.error(f"Error refreshing emails: {str(e)}")
            self.email_content.setPlainText(f"Error loading emails: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load emails: {str(e)}"
            )
        finally:
            self.loading_spinner.stop()
    
    def on_email_selected(self, email_data: dict):
        """Handle email selection."""
        if not email_data:
            logger.warning("No email data provided")
            return
            
        try:
            # Show loading state
            self.loading_spinner.start()
            QApplication.processEvents()
            
            logger.debug(f"Displaying email: {email_data.get('subject', 'No subject')}")
            
            # Build rich display of email
            html_content = f"""
                <h2>{email_data.get('subject', 'No subject')}</h2>
                <p><b>From:</b> {email_data.get('from', 'Unknown')}</p>
                <p><b>Date:</b> {email_data.get('date', 'Unknown')}</p>
                <hr>
                {email_data.get('html', email_data.get('text', 'No content'))}
            """
            
            # Display email content
            self.email_content.setHtml(html_content)
            
            # Update attachments
            attachments = email_data.get('attachments', [])
            self.attachment_view.set_attachments(attachments)
            logger.debug(f"Found {len(attachments)} attachments")
            
            # Generate AI analysis
            if self.ai_service and 'text' in email_data:
                logger.debug("Generating AI analysis...")
                analysis = self.ai_service.analyze_email(email_data['text'])
                self.reply_suggestions.setPlainText(analysis.get('reply_suggestions', ''))
            
        except Exception as e:
            logger.error(f"Error displaying email: {str(e)}")
            self.email_content.setPlainText(f"Error displaying email: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to display email: {str(e)}"
            )
        finally:
            self.loading_spinner.stop()
