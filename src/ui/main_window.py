"""
Main application window integrating all UI components.
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QTreeWidget, QTreeWidgetItem, QSplitter, QTextEdit,
                           QPushButton, QLabel, QFrame, QScrollArea, QMenu,
                           QToolBar, QStatusBar, QMessageBox, QListWidget,
                           QListWidgetItem, QSizePolicy, QGridLayout, QDialog,
                           QFileDialog)
from PyQt6.QtCore import (Qt, QSize, pyqtSignal, QTimer, QUrl, QStandardPaths)
from PyQt6.QtGui import (QIcon, QAction, QColor, QPalette, QImage, QPixmap,
                        QDesktopServices)
from email_providers import EmailProviders
from services.credential_service import CredentialService
from services.email_operation_service import EmailOperationService, OperationType
from services.notification_service import NotificationService, NotificationType
from account_manager import AccountManager
from email_manager import EmailManager
from utils.logger import logger
from utils.error_handler import handle_errors
from .email_account_dialog import EmailAccountDialog
from typing import Dict, List, Optional
import json
import os

# File type icons mapping
FILE_TYPE_ICONS = {
    'image': 'resources/icons/image.png',
    'video': 'resources/icons/video.png',
    'audio': 'resources/icons/audio.png',
    'pdf': 'resources/icons/pdf.png',
    'word': 'resources/icons/word.png',
    'excel': 'resources/icons/excel.png',
    'powerpoint': 'resources/icons/powerpoint.png',
    'text': 'resources/icons/text.png',
    'archive': 'resources/icons/archive.png',
    'file': 'resources/icons/file.png'
}

# Previewable file types
PREVIEWABLE_TYPES = [
    'image/jpeg', 'image/png', 'image/gif', 'image/bmp',
    'application/pdf', 'text/plain', 'text/html',
    'text/markdown', 'text/csv'
]

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        try:
            # Initialize services
            self.notification_service = NotificationService()
            self.credential_service = CredentialService()
            self.operation_service = EmailOperationService(self.notification_service)
            self.account_manager = AccountManager(self.credential_service)
            self.email_manager = EmailManager(self.credential_service, self.operation_service)
            self.current_account = None
            self.current_folder = "INBOX"  # Default folder
            
            # Create required directories
            os.makedirs("resources/icons", exist_ok=True)
            
            # Set up UI
            self.setup_ui()
            
            # Load accounts after UI setup
            self.load_accounts()
            
            # Set up auto-refresh timer
            self.refresh_timer = QTimer(self)
            self.refresh_timer.timeout.connect(self.refresh_emails)
            self.refresh_timer.start(300000)  # Refresh every 5 minutes
            
        except Exception as e:
            logger.critical(f"Failed to initialize main window: {str(e)}")
            QMessageBox.critical(
                self,
                "Initialization Error",
                f"Failed to initialize application: {str(e)}\n\nPlease restart the application."
            )
            raise

    @handle_errors
    def handle_error(self, error_type: str, error_message: str):
        """Handle application errors with proper logging and user notification."""
        logger.error(f"{error_type}: {error_message}")
        
        # Show error in status bar
        self.statusBar().showMessage(f"Error: {error_message}", 5000)
        
        # Show error notification
        self.notification_service.show_notification(
            title=error_type,
            message=error_message,
            type=NotificationType.ERROR
        )
        
        # Show error dialog for critical errors
        QMessageBox.critical(
            self,
            error_type,
            error_message
        )

    @handle_errors
    def on_account_selected(self, current, previous):
        """Handle account selection with proper error handling."""
        if not current:
            return
            
        try:
            # Disconnect previous account if any
            if self.current_account:
                self.email_manager.disconnect_imap()
                self.email_manager.disconnect_smtp()
            
            self.current_account = current.text()
            
            # Show loading state
            self.statusBar().showMessage("Loading account...")
            
            # Initialize account in email manager
            credentials = self.credential_service.get_email_credentials(self.current_account)
            if not credentials:
                raise Exception("No credentials found for account")
                
            account_data = self.account_manager.get_account(self.current_account)
            if not account_data:
                raise Exception("Account configuration not found")
                
            if not self.email_manager.initialize_account(account_data, credentials):
                raise Exception("Failed to initialize account")
            
            # Refresh folders and emails
            self.refresh_folders()
            self.refresh_emails()
            
        except Exception as e:
            self.handle_error("Account Selection Error", str(e))
            self.current_account = None
    
    def setup_ui(self):
        """Set up the main window UI."""
        self.setWindowTitle("AI Email Assistant")
        self.setMinimumSize(1200, 800)
        
        # Set dark theme with improved visibility
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1b1e;
            }
            QSplitter::handle {
                background-color: #2b2d31;
                width: 2px;
                margin: 2px 4px;
            }
            QTreeWidget, QListWidget, QTextEdit {
                background-color: #2b2d31;
                color: #ffffff;
                border: 1px solid #383a40;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                selection-background-color: #404249;
                selection-color: #ffffff;
            }
            QTreeWidget::item, QListWidget::item {
                padding: 12px;
                border-radius: 6px;
                margin: 3px 4px;
                min-height: 24px;
            }
            QTreeWidget::item:hover, QListWidget::item:hover {
                background-color: #32353b;
            }
            QTreeWidget::item:selected, QListWidget::item:selected {
                background-color: #4f545c;
                color: white;
            }
            QPushButton {
                background-color: #5865f2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 13px;
                min-width: 100px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
            QPushButton:pressed {
                background-color: #3c45a5;
            }
            QLabel {
                color: #ffffff;
                font-size: 13px;
                padding: 4px;
            }
            QStatusBar {
                background-color: #2b2d31;
                color: #ffffff;
                border-top: 1px solid #383a40;
                min-height: 24px;
                padding: 4px;
            }
            QToolBar {
                background-color: #2b2d31;
                border-bottom: 1px solid #383a40;
                spacing: 16px;
                padding: 12px;
                min-height: 48px;
            }
            QMenu {
                background-color: #2b2d31;
                color: #ffffff;
                border: 1px solid #383a40;
                border-radius: 6px;
                padding: 8px;
            }
            QMenu::item {
                padding: 12px 24px;
                border-radius: 4px;
                margin: 2px 4px;
                min-width: 150px;
            }
            QMenu::item:selected {
                background-color: #4f545c;
            }
            QFrame {
                border: none;
                padding: 8px;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #2b2d31;
                width: 14px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #383a40;
                border-radius: 7px;
                min-height: 30px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4f545c;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px;
                margin: 2px;
            }
            QToolButton:hover {
                background-color: #32353b;
            }
            QToolButton:pressed {
                background-color: #4f545c;
            }
        """)
        
        # Create main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # Create left panel (accounts and folders)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        
        # Account selector with header
        account_header = QLabel("Email Accounts")
        account_header.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #ffffff;
            padding: 8px 4px;
        """)
        left_layout.addWidget(account_header)
        
        self.account_selector = QListWidget()
        self.account_selector.setMinimumWidth(250)
        self.account_selector.setMaximumWidth(300)
        self.account_selector.setStyleSheet("""
            QListWidget::item {
                padding: 16px;
                border-radius: 8px;
            }
            QListWidget::item:selected {
                background-color: #5865f2;
            }
        """)
        left_layout.addWidget(self.account_selector)
        
        # Folder tree with header
        folder_header = QLabel("Folders")
        folder_header.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #ffffff;
            padding: 8px 4px;
        """)
        left_layout.addWidget(folder_header)
        
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setStyleSheet("""
            QTreeWidget::item {
                padding: 12px;
                border-radius: 6px;
            }
            QTreeWidget::item:selected {
                background-color: #5865f2;
            }
            QTreeWidget::branch {
                background-color: transparent;
            }
            QTreeWidget::branch:has-siblings:!adjoins-item {
                border-image: url(resources/icons/vline.png) 0;
            }
            QTreeWidget::branch:has-siblings:adjoins-item {
                border-image: url(resources/icons/branch-more.png) 0;
            }
            QTreeWidget::branch:!has-children:!has-siblings:adjoins-item {
                border-image: url(resources/icons/branch-end.png) 0;
            }
        """)
        left_layout.addWidget(self.folder_tree)
        
        # Add left panel to main layout
        main_layout.addWidget(left_panel)
        
        # Create middle panel (email list)
        middle_panel = QWidget()
        middle_layout = QVBoxLayout(middle_panel)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(8)
        
        # Email list header
        email_header = QLabel("Messages")
        email_header.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #ffffff;
            padding: 8px 4px;
        """)
        middle_layout.addWidget(email_header)
        
        # Email list
        self.email_list = QListWidget()
        self.email_list.setStyleSheet("""
            QListWidget::item {
                padding: 16px;
                border-radius: 8px;
            }
            QListWidget::item:selected {
                background-color: #5865f2;
            }
        """)
        middle_layout.addWidget(self.email_list)
        
        # Add middle panel to main layout
        main_layout.addWidget(middle_panel, stretch=2)
        
        # Create right panel (email content and AI features)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        
        # Email content header
        content_header = QLabel("Email Content")
        content_header.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #ffffff;
            padding: 8px 4px;
        """)
        right_layout.addWidget(content_header)
        
        # Email content scroll area
        self.email_content = QScrollArea()
        self.email_content.setWidgetResizable(True)
        self.email_content.setStyleSheet("""
            QScrollArea {
                background-color: #1a1b1e;
                border: none;
            }
        """)
        right_layout.addWidget(self.email_content)
        
        # AI Features panel
        ai_panel = QFrame()
        ai_panel.setStyleSheet("""
            QFrame {
                background-color: #2b2d31;
                border: 1px solid #383a40;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        ai_layout = QVBoxLayout(ai_panel)
        
        # AI Features header
        ai_header = QLabel("AI Features")
        ai_header.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #ffffff;
            padding: 8px 4px;
        """)
        ai_layout.addWidget(ai_header)
        
        # AI buttons
        ai_buttons_layout = QHBoxLayout()
        ai_buttons_layout.setSpacing(12)
        
        ai_reply_btn = QPushButton("AI Reply")
        ai_reply_btn.setIcon(QIcon("resources/icons/ai_reply.png"))
        ai_reply_btn.clicked.connect(self.generate_ai_reply)
        ai_buttons_layout.addWidget(ai_reply_btn)
        
        ai_summarize_btn = QPushButton("Summarize")
        ai_summarize_btn.setIcon(QIcon("resources/icons/summarize.png"))
        ai_summarize_btn.clicked.connect(self.generate_summary)
        ai_buttons_layout.addWidget(ai_summarize_btn)
        
        ai_translate_btn = QPushButton("Translate")
        ai_translate_btn.setIcon(QIcon("resources/icons/translate.png"))
        ai_translate_btn.clicked.connect(self.translate_email)
        ai_buttons_layout.addWidget(ai_translate_btn)
        
        ai_layout.addLayout(ai_buttons_layout)
        right_layout.addWidget(ai_panel)
        
        # Add right panel to main layout
        main_layout.addWidget(right_panel, stretch=2)
        
        # Create toolbar
        self.create_toolbar()
        
        # Create status bar
        status_bar = self.statusBar()
        status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #2b2d31;
                color: #ffffff;
                border-top: 1px solid #383a40;
            }
        """)
        status_bar.showMessage("Ready")
        
        # Connect signals
        self.folder_tree.itemClicked.connect(self.on_folder_selected)
        self.account_selector.currentItemChanged.connect(self.on_account_selected)
        self.email_list.currentItemChanged.connect(self.on_email_selected)
    
    def create_toolbar(self):
        """Create the main toolbar."""
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Compose new email
        compose_action = QAction(QIcon("resources/icons/compose.png"), "Compose", self)
        compose_action.setStatusTip("Compose new email")
        compose_action.triggered.connect(self.compose_email)
        toolbar.addAction(compose_action)
        
        toolbar.addSeparator()
        
        # Refresh
        refresh_action = QAction(QIcon("resources/icons/refresh.png"), "Refresh", self)
        refresh_action.setStatusTip("Refresh emails")
        refresh_action.triggered.connect(self.refresh_emails)
        toolbar.addAction(refresh_action)
        
        # Add account
        add_account_action = QAction(QIcon("resources/icons/add_account.png"), "Add Account", self)
        add_account_action.setStatusTip("Add new email account")
        add_account_action.triggered.connect(self.add_account)
        toolbar.addAction(add_account_action)
        
        toolbar.addSeparator()
        
        # AI features
        ai_menu = QMenu()
        
        train_ai_action = QAction(QIcon("resources/icons/train.png"), "Train AI", self)
        train_ai_action.setStatusTip("Train AI with your email style")
        ai_menu.addAction(train_ai_action)
        
        ai_settings_action = QAction(QIcon("resources/icons/settings.png"), "AI Settings", self)
        ai_settings_action.setStatusTip("Configure AI assistant")
        ai_menu.addAction(ai_settings_action)
        
        ai_button = QPushButton("AI Features")
        ai_button.setIcon(QIcon("resources/icons/ai.png"))
        ai_button.setMenu(ai_menu)
        toolbar.addWidget(ai_button)
    
    def load_accounts(self):
        """Load email accounts."""
        accounts = self.account_manager.get_all_accounts()
        self.account_selector.clear()
        
        for account in accounts:
            item = QListWidgetItem(account['email'])
            item.setIcon(QIcon("resources/icons/account.png"))
            self.account_selector.addItem(item)
    
    def add_account(self):
        """Show dialog to add new email account."""
        dialog = EmailAccountDialog(self)
        if dialog.exec():
            self.load_accounts()
            self.refresh_emails()
    
    def compose_email(self):
        """Show compose email dialog."""
        # TODO: Implement compose email dialog
        pass
    
    def refresh_emails(self):
        """Refresh email list."""
        if not self.current_account:
            return
            
        try:
            # Show loading state in status bar
            self.statusBar().showMessage("Loading emails...")
            
            # Get credentials for the account
            credentials = self.credential_service.get_email_credentials(self.current_account)
            if not credentials:
                raise Exception("No credentials found for account")
            
            # Start operation
            operation_id = self.operation_service.start_operation(
                OperationType.FETCH,
                f"Loading emails from {self.current_folder}"
            )
            
            try:
                # Get emails from the current folder
                emails = self.email_manager.get_emails(
                    self.current_account,
                    credentials,
                    folder=self.current_folder,
                    limit=50  # Load last 50 emails initially
                )
                
                # Clear and populate email list
                self.email_list.clear()
                
                for email_data in emails:
                    # Create list item with email info
                    item = QListWidgetItem()
                    
                    # Format the subject line
                    subject = email_data.get('subject', 'No subject')
                    sender = email_data.get('from', 'Unknown')
                    date = email_data.get('date', '')
                    
                    # Add indicators for attachments and flags
                    if email_data.get('attachments'):
                        subject = f"📎 {subject}"
                    if email_data.get('flags') and '\\Flagged' in email_data['flags']:
                        subject = f"⭐ {subject}"
                    
                    # Set item text and data
                    item.setText(f"{subject}\nFrom: {sender}\n{date}")
                    item.setData(Qt.ItemDataRole.UserRole, email_data)
                    
                    # Style unread emails
                    if email_data.get('flags') and '\\Seen' not in email_data['flags']:
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    
                    self.email_list.addItem(item)
                
                # Complete operation
                self.operation_service.complete_operation(
                    operation_id,
                    True,
                    f"Loaded {len(emails)} emails"
                )
                
            except Exception as e:
                # Fail operation
                self.operation_service.fail_operation(
                    operation_id,
                    str(e)
                )
                raise
                
        except Exception as e:
            logger.error(f"Error loading emails: {str(e)}")
            self.statusBar().showMessage("Error loading emails", 5000)
            self.handle_error("Email Loading Error", str(e))
    
    def generate_ai_reply(self):
        """Generate AI-powered reply."""
        # TODO: Implement AI reply generation
        pass
    
    def generate_summary(self):
        """Generate email summary."""
        # TODO: Implement email summarization
        pass
    
    def translate_email(self):
        """Translate email content."""
        # TODO: Implement email translation
        pass
    
    @handle_errors
    def on_email_selected(self, current, previous):
        """Handle email selection with proper error handling and status updates."""
        if not current:
            self.email_content.clear()
            return
            
        try:
            # Get email data from item
            email_data = current.data(Qt.ItemDataRole.UserRole)
            if not email_data:
                return
                
            # Show loading state
            self.statusBar().showMessage("Loading email content...")
            
            # Start operation
            operation_id = self.operation_service.start_operation(
                OperationType.FETCH,
                f"Loading email content"
            )
            
            try:
                # Create email content widget
                content_widget = QWidget()
                content_layout = QVBoxLayout(content_widget)
                content_layout.setContentsMargins(0, 0, 0, 0)
                content_layout.setSpacing(16)
                
                # Email header
                header_widget = QWidget()
                header_widget.setStyleSheet("""
                    QWidget {
                        background-color: #2b2d31;
                        border: 1px solid #383a40;
                        border-radius: 8px;
                        padding: 16px;
                    }
                    QLabel {
                        color: #ffffff;
                    }
                """)
                header_layout = QGridLayout(header_widget)
                
                # Subject
                subject_label = QLabel("<b>Subject:</b>")
                subject_value = QLabel(email_data.get('subject', 'No subject'))
                subject_value.setWordWrap(True)
                header_layout.addWidget(subject_label, 0, 0)
                header_layout.addWidget(subject_value, 0, 1)
                
                # From
                from_label = QLabel("<b>From:</b>")
                from_value = QLabel(email_data.get('from', 'Unknown'))
                header_layout.addWidget(from_label, 1, 0)
                header_layout.addWidget(from_value, 1, 1)
                
                # To
                to_label = QLabel("<b>To:</b>")
                to_value = QLabel(", ".join(email_data.get('to', ['Unknown'])))
                to_value.setWordWrap(True)
                header_layout.addWidget(to_label, 2, 0)
                header_layout.addWidget(to_value, 2, 1)
                
                # Date
                date_label = QLabel("<b>Date:</b>")
                date_value = QLabel(email_data.get('date', ''))
                header_layout.addWidget(date_label, 3, 0)
                header_layout.addWidget(date_value, 3, 1)
                
                content_layout.addWidget(header_widget)
                
                # Attachments section
                if email_data.get('attachments'):
                    attachment_widget = QWidget()
                    attachment_widget.setStyleSheet("""
                        QWidget {
                            background-color: #2b2d31;
                            border: 1px solid #383a40;
                            border-radius: 8px;
                            padding: 16px;
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
                    attachment_layout = QVBoxLayout(attachment_widget)
                    
                    # Attachments header
                    att_header = QLabel(f"Attachments ({len(email_data['attachments'])})")
                    att_header.setStyleSheet("""
                        font-size: 14px;
                        font-weight: bold;
                        color: #ffffff;
                        padding: 4px 0;
                    """)
                    attachment_layout.addWidget(att_header)
                    
                    # Attachment list
                    for attachment in email_data['attachments']:
                        att_item = QWidget()
                        att_item_layout = QHBoxLayout(att_item)
                        att_item_layout.setContentsMargins(0, 4, 0, 4)
                        
                        # Icon based on file type
                        icon_label = QLabel()
                        icon = self.get_attachment_icon(attachment['content_type'])
                        icon_label.setPixmap(icon.pixmap(24, 24))
                        att_item_layout.addWidget(icon_label)
                        
                        # File info
                        file_info = QLabel(f"{attachment['filename']} ({self.format_size(attachment['size'])})")
                        att_item_layout.addWidget(file_info, stretch=1)
                        
                        # Preview button for supported types
                        if self.is_previewable(attachment['content_type']):
                            preview_btn = QPushButton("Preview")
                            preview_btn.setIcon(QIcon("resources/icons/preview.png"))
                            preview_btn.clicked.connect(
                                lambda checked, a=attachment: self.preview_attachment(a)
                            )
                            att_item_layout.addWidget(preview_btn)
                        
                        # Download button
                        download_btn = QPushButton("Download")
                        download_btn.setIcon(QIcon("resources/icons/download.png"))
                        download_btn.clicked.connect(
                            lambda checked, a=attachment: self.download_attachment(a)
                        )
                        att_item_layout.addWidget(download_btn)
                        
                        attachment_layout.addWidget(att_item)
                    
                    content_layout.addWidget(attachment_widget)
                
                # Email content
                content_browser = QTextEdit()
                content_browser.setReadOnly(True)
                content_browser.setStyleSheet("""
                    QTextEdit {
                        background-color: #2b2d31;
                        color: #ffffff;
                        border: 1px solid #383a40;
                        border-radius: 8px;
                        padding: 16px;
                        font-size: 14px;
                        line-height: 1.5;
                    }
                """)
                
                # Use HTML content if available, fallback to text
                content = email_data.get('html', email_data.get('text', 'No content'))
                content_browser.setHtml(content)
                content_layout.addWidget(content_browser, stretch=1)
                
                # Set the content widget
                self.email_content.setWidget(content_widget)
                
                # Mark email as read if unread
                if email_data.get('flags') and '\\Seen' not in email_data['flags']:
                    try:
                        credentials = self.credential_service.get_email_credentials(self.current_account)
                        if credentials:
                            if self.email_manager.mark_as_read(
                                self.current_account,
                                credentials,
                                email_data['message_id']
                            ):
                                # Update UI to reflect read status
                                font = current.font()
                                font.setBold(False)
                                current.setFont(font)
                                
                                # Update status
                                self.statusBar().showMessage("Email marked as read", 3000)
                            else:
                                logger.warning("Failed to mark email as read")
                                
                    except Exception as e:
                        logger.error(f"Error marking email as read: {str(e)}")
                        self.notification_service.show_notification(
                            "Warning",
                            "Could not mark email as read",
                            NotificationType.WARNING
                        )
                
                # Complete operation
                self.operation_service.complete_operation(
                    operation_id,
                    True,
                    "Email content loaded successfully"
                )
                
            except Exception as e:
                # Fail operation
                self.operation_service.fail_operation(
                    operation_id,
                    str(e)
                )
                raise
                
        except Exception as e:
            logger.error(f"Error displaying email: {str(e)}")
            self.email_content.setPlainText("Error displaying email content")
            self.handle_error("Email Display Error", str(e))
    
    def get_attachment_icon(self, content_type: str) -> QIcon:
        """Get appropriate icon for attachment type."""
        if content_type.startswith('image/'):
            return QIcon(FILE_TYPE_ICONS['image'])
        elif content_type.startswith('video/'):
            return QIcon(FILE_TYPE_ICONS['video'])
        elif content_type.startswith('audio/'):
            return QIcon(FILE_TYPE_ICONS['audio'])
        elif content_type == 'application/pdf':
            return QIcon(FILE_TYPE_ICONS['pdf'])
        elif content_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            return QIcon(FILE_TYPE_ICONS['word'])
        elif content_type in ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
            return QIcon(FILE_TYPE_ICONS['excel'])
        elif content_type in ['application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation']:
            return QIcon(FILE_TYPE_ICONS['powerpoint'])
        elif content_type.startswith('text/'):
            return QIcon(FILE_TYPE_ICONS['text'])
        elif content_type in ['application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed']:
            return QIcon(FILE_TYPE_ICONS['archive'])
        else:
            return QIcon(FILE_TYPE_ICONS['file'])
    
    def format_size(self, size: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def is_previewable(self, content_type: str) -> bool:
        """Check if attachment can be previewed."""
        return content_type in PREVIEWABLE_TYPES
    
    def preview_attachment(self, attachment: Dict):
        """Show attachment preview dialog."""
        try:
            # Create preview dialog
            preview = QDialog(self)
            preview.setWindowTitle(f"Preview: {attachment['filename']}")
            preview.setMinimumSize(800, 600)
            preview.setStyleSheet("""
                QDialog {
                    background-color: #1a1b1e;
                }
                QLabel {
                    color: #ffffff;
                }
                QTextEdit {
                    background-color: #2b2d31;
                    color: #ffffff;
                    border: 1px solid #383a40;
                    border-radius: 8px;
                    padding: 16px;
                }
                QPushButton {
                    background-color: #5865f2;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #4752c4;
                }
            """)
            
            layout = QVBoxLayout(preview)
            layout.setContentsMargins(16, 16, 16, 16)
            layout.setSpacing(16)
            
            # Create preview widget based on content type
            if attachment['content_type'].startswith('image/'):
                image = QImage.fromData(attachment['data'])
                if not image.isNull():
                    label = QLabel()
                    pixmap = QPixmap.fromImage(image)
                    label.setPixmap(pixmap.scaled(
                        preview.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    ))
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(label)
                else:
                    layout.addWidget(QLabel("Failed to load image"))
                    
            elif attachment['content_type'] == 'application/pdf':
                # TODO: Implement PDF preview using PyMuPDF or similar
                layout.addWidget(QLabel("PDF preview not implemented yet"))
                
            elif attachment['content_type'].startswith('text/'):
                text = QTextEdit()
                text.setReadOnly(True)
                text.setPlainText(attachment['data'].decode('utf-8', errors='ignore'))
                layout.addWidget(text)
                
            else:
                msg = QLabel("Preview not available for this file type")
                msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(msg)
            
            # Add buttons
            button_layout = QHBoxLayout()
            
            # Download button
            download_btn = QPushButton("Download")
            download_btn.setIcon(QIcon("resources/icons/download.png"))
            download_btn.clicked.connect(lambda: self.download_attachment(attachment))
            button_layout.addWidget(download_btn)
            
            # Close button
            close_btn = QPushButton("Close")
            close_btn.setIcon(QIcon("resources/icons/close.png"))
            close_btn.clicked.connect(preview.close)
            button_layout.addWidget(close_btn)
            
            layout.addLayout(button_layout)
            
            preview.exec()
            
        except Exception as e:
            logger.error(f"Error previewing attachment: {str(e)}")
            self.handle_error("Preview Error", str(e))
    
    def download_attachment(self, attachment: Dict):
        """Download attachment to user's system."""
        try:
            # Get download directory
            download_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
            
            # Show file save dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Attachment",
                os.path.join(download_dir, attachment['filename']),
                "All Files (*.*)"
            )
            
            if file_path:
                # Start operation
                operation_id = self.operation_service.start_operation(
                    OperationType.ATTACHMENT,
                    f"Downloading {attachment['filename']}"
                )
                
                try:
                    # Save file
                    with open(file_path, 'wb') as f:
                        f.write(attachment['data'])
                    
                    # Complete operation
                    self.operation_service.complete_operation(
                        operation_id,
                        True,
                        f"Attachment saved to {file_path}"
                    )
                    
                    self.statusBar().showMessage(f"Attachment saved to {file_path}", 5000)
                    
                    # Show in folder
                    show_in_folder = QMessageBox.question(
                        self,
                        "Download Complete",
                        "Attachment downloaded successfully. Open containing folder?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    
                    if show_in_folder == QMessageBox.StandardButton.Yes:
                        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(file_path)))
                    
                except Exception as e:
                    # Fail operation
                    self.operation_service.fail_operation(
                        operation_id,
                        str(e)
                    )
                    raise
                
        except Exception as e:
            logger.error(f"Error downloading attachment: {str(e)}")
            self.handle_error("Download Error", str(e))
    
    @handle_errors
    def on_folder_selected(self, item):
        """Handle folder selection with proper error handling."""
        if not item:
            return
            
        try:
            folder_name = item.text(0)
            if not folder_name:
                return
                
            self.current_folder = folder_name
            self.refresh_emails()
            
        except Exception as e:
            self.handle_error("Folder Selection Error", str(e))

    def refresh_folders(self):
        """Refresh folder list."""
        if not self.current_account:
            return
            
        try:
            # Show loading state
            self.statusBar().showMessage("Loading folders...")
            
            # Get credentials
            credentials = self.credential_service.get_email_credentials(self.current_account)
            if not credentials:
                raise Exception("No credentials found for account")
            
            # Start operation
            operation_id = self.operation_service.start_operation(
                OperationType.FETCH,
                f"Loading folders for {self.current_account}"
            )
            
            try:
                # Get folders
                folders = self.email_manager.list_folders()
                
                # Clear and populate folder tree
                self.folder_tree.clear()
                
                for folder_data in folders:
                    item = QTreeWidgetItem([folder_data['name']])
                    
                    # Get folder status
                    status = self.email_manager.get_folder_status(folder_data['name'])
                    if status:
                        total = status['messages']
                        unread = status['unseen']
                        if unread > 0:
                            item.setText(0, f"{folder_data['name']} ({unread}/{total})")
                            font = item.font(0)
                            font.setBold(True)
                            item.setFont(0, font)
                    
                    self.folder_tree.addTopLevelItem(item)
                
                # Complete operation
                self.operation_service.complete_operation(
                    operation_id,
                    True,
                    f"Loaded {len(folders)} folders"
                )
                
            except Exception as e:
                # Fail operation
                self.operation_service.fail_operation(
                    operation_id,
                    str(e)
                )
                raise
                
        except Exception as e:
            logger.error(f"Error loading folders: {str(e)}")
            self.statusBar().showMessage("Error loading folders", 5000)
            self.handle_error("Folder Loading Error", str(e))

    def closeEvent(self, event):
        """Handle application close event."""
        try:
            # Stop refresh timer
            if hasattr(self, 'refresh_timer'):
                self.refresh_timer.stop()
            
            # Close email connections
            if hasattr(self, 'email_manager'):
                self.email_manager.disconnect_imap()
                self.email_manager.disconnect_smtp()
            
            # Save any pending changes
            if hasattr(self, 'account_manager'):
                self.account_manager.save_changes()
            
            # Accept the close event
            event.accept()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            event.accept()  # Still close even if cleanup fails