"""
Main application window integrating all UI components.
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QTreeWidget, QTreeWidgetItem, QSplitter, QTextEdit,
                           QPushButton, QLabel, QFrame, QScrollArea, QMenu,
                           QToolBar, QStatusBar, QMessageBox, QListWidget,
                           QListWidgetItem, QSizePolicy)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QAction, QColor, QPalette
from email_providers import EmailProviders
from services.credential_service import CredentialService
from account_manager import AccountManager
from utils.logger import logger
from .email_account_dialog import EmailAccountDialog
import json

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.account_manager = AccountManager()
        self.credential_service = CredentialService()
        self.setup_ui()
        
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
        
        # Create central widget and main layout with proper spacing
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        
        # Left panel (folders and accounts)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)
        
        # Account selector with proper sizing
        self.account_selector = QListWidget()
        self.account_selector.setMaximumWidth(300)
        self.account_selector.setMinimumWidth(240)
        self.account_selector.setMinimumHeight(120)
        self.account_selector.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        left_layout.addWidget(self.account_selector)
        
        # Folder tree with proper sizing
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setMinimumWidth(240)
        self.folder_tree.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        left_layout.addWidget(self.folder_tree)
        
        splitter.addWidget(left_panel)
        
        # Middle panel (email list)
        middle_panel = QWidget()
        middle_layout = QVBoxLayout(middle_panel)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(16)
        
        # Email list with proper sizing
        self.email_list = QListWidget()
        self.email_list.setMinimumWidth(340)
        self.email_list.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        middle_layout.addWidget(self.email_list)
        
        splitter.addWidget(middle_panel)
        
        # Right panel (email preview and AI features)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)
        
        # Email preview with improved styling
        preview_frame = QFrame()
        preview_frame.setFrameShape(QFrame.Shape.StyledPanel)
        preview_frame.setStyleSheet("""
            QFrame {
                background-color: #2b2d31;
                border: 1px solid #383a40;
                border-radius: 8px;
                padding: 24px;
            }
        """)
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setSpacing(16)
        
        # Email header with improved visibility
        self.email_subject = QLabel()
        self.email_subject.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: white;
            padding: 4px 0;
            qproperty-wordWrap: true;
        """)
        preview_layout.addWidget(self.email_subject)
        
        self.email_from = QLabel()
        self.email_from.setStyleSheet("""
            font-size: 14px;
            color: #dcddde;
            padding: 4px 0;
            qproperty-wordWrap: true;
        """)
        preview_layout.addWidget(self.email_from)
        
        self.email_date = QLabel()
        self.email_date.setStyleSheet("""
            font-size: 13px;
            color: #a0a0a0;
            padding: 4px 0;
        """)
        preview_layout.addWidget(self.email_date)
        
        # Separator with improved visibility
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("""
            background-color: #383a40;
            margin: 16px 0;
            min-height: 2px;
        """)
        preview_layout.addWidget(separator)
        
        # Email content with proper sizing
        self.email_content = QTextEdit()
        self.email_content.setReadOnly(True)
        self.email_content.setMinimumHeight(200)
        self.email_content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.email_content.setStyleSheet("""
            QTextEdit {
                background-color: #32353b;
                border: 1px solid #383a40;
                border-radius: 6px;
                padding: 16px;
                color: #ffffff;
                font-size: 14px;
                selection-background-color: #4f545c;
                selection-color: #ffffff;
            }
        """)
        preview_layout.addWidget(self.email_content)
        
        # AI Features panel with improved styling
        ai_panel = QFrame()
        ai_panel.setStyleSheet("""
            QFrame {
                background-color: #32353b;
                border: 1px solid #383a40;
                border-radius: 8px;
                padding: 20px;
                margin-top: 16px;
            }
        """)
        ai_layout = QVBoxLayout(ai_panel)
        ai_layout.setSpacing(16)
        
        # AI Analysis with improved visibility
        ai_analysis_label = QLabel("AI Analysis")
        ai_analysis_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: white;
            padding: 4px 0;
        """)
        ai_layout.addWidget(ai_analysis_label)
        
        self.ai_analysis = QTextEdit()
        self.ai_analysis.setReadOnly(True)
        self.ai_analysis.setMinimumHeight(100)
        self.ai_analysis.setMaximumHeight(150)
        self.ai_analysis.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.ai_analysis.setStyleSheet("""
            QTextEdit {
                background-color: #2b2d31;
                border: 1px solid #383a40;
                border-radius: 6px;
                padding: 16px;
                color: #ffffff;
                font-size: 13px;
                selection-background-color: #4f545c;
                selection-color: #ffffff;
            }
        """)
        ai_layout.addWidget(self.ai_analysis)
        
        # AI Action buttons with proper spacing
        ai_buttons_layout = QHBoxLayout()
        ai_buttons_layout.setSpacing(16)
        
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
        
        # Quick reply suggestions with improved visibility
        suggestions_label = QLabel("Quick Reply Suggestions")
        suggestions_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: white;
            padding: 12px 0 4px 0;
        """)
        ai_layout.addWidget(suggestions_label)
        
        self.suggestions_list = QListWidget()
        self.suggestions_list.setMinimumHeight(100)
        self.suggestions_list.setMaximumHeight(150)
        self.suggestions_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.suggestions_list.setStyleSheet("""
            QListWidget {
                background-color: #2b2d31;
                border: 1px solid #383a40;
                border-radius: 6px;
                padding: 12px;
                color: #ffffff;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 12px;
                border-radius: 4px;
                margin: 2px 4px;
                min-height: 24px;
            }
            QListWidget::item:hover {
                background-color: #32353b;
            }
            QListWidget::item:selected {
                background-color: #4f545c;
                color: white;
            }
        """)
        ai_layout.addWidget(self.suggestions_list)
        
        preview_layout.addWidget(ai_panel)
        right_layout.addWidget(preview_frame)
        
        splitter.addWidget(right_panel)
        
        # Set stretch factors for proper panel sizing
        splitter.setStretchFactor(0, 1)  # Left panel
        splitter.setStretchFactor(1, 2)  # Middle panel
        splitter.setStretchFactor(2, 3)  # Right panel
        
        main_layout.addWidget(splitter)
        
        # Create toolbar with proper sizing
        self.create_toolbar()
        
        # Create status bar with proper visibility
        status_bar = self.statusBar()
        status_bar.setMinimumHeight(28)
        status_bar.showMessage("Ready")
        
        # Load accounts
        self.load_accounts()
    
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
        # TODO: Implement email refresh
        pass
    
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
    
    def handle_error(self, error_type: str, error_message: str):
        """Handle application errors."""
        logger.error(f"{error_type}: {error_message}")
        self.statusBar().showMessage(f"Error: {error_message}", 5000)
        
        QMessageBox.critical(
            self,
            "Error",
            f"{error_type}: {error_message}"
        )