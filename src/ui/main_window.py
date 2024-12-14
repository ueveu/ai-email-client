"""
Main application window integrating all UI components.
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QSystemTrayIcon,
                           QMenu, QMenuBar, QToolBar, QDockWidget, QApplication, QDialog, QDialogButtonBox, QMessageBox)
from PyQt6.QtCore import Qt, QSize, QSettings
from PyQt6.QtGui import QIcon, QAction
import qtawesome as qta
import threading

from services.notification_service import NotificationService, NotificationType
from services.email_operation_service import EmailOperationService
from services.shortcut_service import ShortcutService
from services.theme_service import ThemeService
from services.ai_service import AIService
from services.credential_service import CredentialService
from account_manager import AccountManager
from email_manager import EmailManager
from email_providers import EmailProviders, Provider

from .status_bar_widget import StatusBarWidget
from .settings_dialog import SettingsDialog
from utils.logger import logger
from .loading_spinner import LoadingSpinner

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize services
        self.notification_service = NotificationService()
        self.operation_service = EmailOperationService(self.notification_service)
        self.shortcut_service = ShortcutService()
        self.theme_service = ThemeService()
        self.ai_service = AIService()
        self.credential_service = CredentialService()
        
        # Initialize email management
        self.account_manager = AccountManager()
        self.email_manager = None  # Will be set when account is selected
        
        # Add loading indicators
        self.loading_indicator = LoadingSpinner()
        
        # Set up UI
        self.setup_ui()
        self.setup_system_tray()
        self.setup_shortcuts()
        
        # Apply theme
        self.theme_service.apply_theme(self.theme_service.get_current_theme())
        
        # Load accounts and connect if auto-connect is enabled
        self.load_accounts()
    
    def setup_ui(self):
        """Set up the main window UI."""
        self.setWindowTitle("AI Email Assistant")
        self.setMinimumSize(1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Menu bar
        self.create_menu_bar()
        
        # Tool bar
        self.create_tool_bar()
        
        # Status bar
        self.status_bar = StatusBarWidget(
            self.notification_service,
            self.operation_service
        )
        layout.addWidget(self.status_bar)
    
    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # Account management actions
        add_account_action = QAction("Add Email Account...", self)
        add_account_action.setStatusTip("Add a new email account")
        add_account_action.triggered.connect(self.show_add_account_dialog)
        file_menu.addAction(add_account_action)
        
        manage_accounts_action = QAction("Manage Accounts...", self)
        manage_accounts_action.setStatusTip("Manage email accounts")
        manage_accounts_action.triggered.connect(self.show_manage_accounts_dialog)
        file_menu.addAction(manage_accounts_action)
        
        file_menu.addSeparator()
        
        # Settings action
        settings_action = QAction("Settings...", self)
        settings_action.setStatusTip("Configure application settings")
        settings_action.triggered.connect(self.show_settings_dialog)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        toggle_notifications = QAction("Show Notifications", self)
        toggle_notifications.setCheckable(True)
        toggle_notifications.setShortcut(
            self.shortcut_service.get_shortcut('toggle_notifications')
        )
        toggle_notifications.triggered.connect(
            lambda checked: self.status_bar.toggle_section('notifications', checked)
        )
        view_menu.addAction(toggle_notifications)
        
        toggle_operations = QAction("Show Operations", self)
        toggle_operations.setCheckable(True)
        toggle_operations.setShortcut(
            self.shortcut_service.get_shortcut('toggle_operations')
        )
        toggle_operations.triggered.connect(
            lambda checked: self.status_bar.toggle_section('operations', checked)
        )
        view_menu.addAction(toggle_operations)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("About", self)
        about_action.setStatusTip("Show about dialog")
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def create_tool_bar(self):
        """Create the main toolbar."""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Email operations
        compose_btn = QAction(qta.icon("fa.edit"), "Compose", self)
        compose_btn.setShortcut(self.shortcut_service.get_shortcut('email_compose'))
        toolbar.addAction(compose_btn)
        
        reply_btn = QAction(qta.icon("fa.reply"), "Reply", self)
        reply_btn.setShortcut(self.shortcut_service.get_shortcut('email_reply'))
        toolbar.addAction(reply_btn)
        
        forward_btn = QAction(qta.icon("fa.share"), "Forward", self)
        forward_btn.setShortcut(self.shortcut_service.get_shortcut('email_forward'))
        toolbar.addAction(forward_btn)
        
        toolbar.addSeparator()
        
        # AI features
        generate_btn = QAction(qta.icon("fa.magic"), "Generate Reply", self)
        generate_btn.setShortcut(self.shortcut_service.get_shortcut('ai_generate_reply'))
        toolbar.addAction(generate_btn)
        
        customize_btn = QAction(qta.icon("fa.sliders"), "Customize", self)
        customize_btn.setShortcut(self.shortcut_service.get_shortcut('ai_customize_reply'))
        toolbar.addAction(customize_btn)
    
    def setup_system_tray(self):
        """Set up the system tray icon."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(qta.icon("fa.envelope"))
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # Connect to notification service
        self.notification_service.set_system_tray(self.tray_icon)
    
    def setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        self.shortcut_service.initialize(self)
        self.shortcut_service.shortcut_triggered.connect(self.handle_shortcut)
    
    def handle_shortcut(self, action: str):
        """Handle triggered shortcuts."""
        if action == 'toggle_notifications':
            self.status_bar.notification_indicator.toggle()
        elif action == 'toggle_operations':
            self.status_bar.operation_indicator.toggle()
        elif action == 'clear_notifications':
            self.notification_service.clear_all()
        elif action == 'toggle_status_bar':
            self.status_bar.setVisible(not self.status_bar.isVisible())
    
    def show_settings_dialog(self):
        """Show application settings dialog."""
        from .settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        if dialog.exec():
            # Reload settings if dialog was accepted
            self.load_settings()
    
    def show_about_dialog(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About AI Email Assistant",
            "AI Email Assistant\n\n"
            "A modern email client with AI-powered features\n"
            "Version 1.0.0\n\n"
            "© 2024 Your Company"
        )
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Minimize to tray instead of closing
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()
    
    def test_notifications(self):
        """Test method to demonstrate notifications and operations."""
        # Show a test notification
        self.notification_service.show_notification(
            "Welcome",
            "Welcome to AI Email Assistant!",
            duration=5000
        )
        
        # Start a test operation
        self.operation_service.sync_folder("INBOX") 
    
    def handle_error(self, error_type: str, error_message: str):
        """
        Handle errors from the error handler.
        
        Args:
            error_type (str): Type of error
            error_message (str): Error message
        """
        # Show error in status bar
        self.status_bar.showMessage(f"Error: {error_message}", 5000)  # Show for 5 seconds
        
        # Also show notification
        self.notification_service.show_notification(
            "Error",
            f"{error_type}: {error_message}",
            level="error"
        )
        
        # Log the error
        logger.error(f"Error handled by MainWindow: {error_type} - {error_message}")
    
    def authenticate_account(self, email: str) -> bool:
        """
        Authenticate an email account.
        
        Args:
            email (str): Email address to authenticate
            
        Returns:
            bool: True if authentication successful
        """
        try:
            # Get account data
            account_data = self.account_manager.get_account(email)
            if not account_data:
                self.notification_service.show_notification(
                    "Authentication Error",
                    f"Account {email} not found",
                    NotificationType.ERROR
                )
                return False
            
            # Check provider type
            provider = EmailProviders.detect_provider(email)
            
            # Handle Gmail OAuth
            if provider == Provider.GMAIL:
                # Check for existing OAuth tokens
                tokens = self.credential_service.get_oauth_tokens(email)
                if not tokens:
                    # Show authentication dialog
                    from .email_account_dialog import EmailAccountDialog
                    dialog = EmailAccountDialog(self)
                    dialog.email_input.setText(email)
                    dialog.quick_setup(Provider.GMAIL)
                    if not dialog.exec():
                        return False
                    
                    # Get fresh tokens
                    tokens = self.credential_service.get_oauth_tokens(email)
                    if not tokens:
                        return False
                    
                    # Update account data with new tokens
                    account_data['oauth_tokens'] = tokens
            else:
                # Check for password
                credentials = self.credential_service.get_email_credentials(email)
                if not credentials or 'password' not in credentials:
                    # Show authentication dialog
                    from .email_account_dialog import EmailAccountDialog
                    dialog = EmailAccountDialog(self)
                    dialog.email_input.setText(email)
                    if not dialog.exec():
                        return False
                    
                    # Get fresh credentials
                    credentials = self.credential_service.get_email_credentials(email)
                    if not credentials:
                        return False
                    
                    # Update account data with password
                    account_data['password'] = credentials['password']
            
            # Create email manager with authenticated account
            self.email_manager = EmailManager(account_data)
            
            # Test connection
            if not self.email_manager.connect_imap():
                raise ConnectionError("Failed to connect to IMAP server")
            if not self.email_manager.connect_smtp():
                raise ConnectionError("Failed to connect to SMTP server")
            
            # Update UI
            self.setWindowTitle(f"AI Email Assistant - {email}")
            self.notification_service.show_notification(
                "Connected",
                f"Successfully connected to {email}",
                NotificationType.SUCCESS
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Authentication error for {email}: {str(e)}")
            self.notification_service.show_notification(
                "Authentication Error",
                f"Failed to authenticate {email}: {str(e)}",
                NotificationType.ERROR
            )
            return False
    
    def load_accounts(self):
        """Load email accounts and connect if auto-connect is enabled."""
        try:
            settings = QSettings('AI Email Assistant', 'Settings')
            auto_connect = settings.value('general/auto_connect', True, bool)
            
            # Get all accounts
            accounts = self.account_manager.get_all_accounts()
            if not accounts:
                # Show welcome message if no accounts
                self.notification_service.show_notification(
                    "Welcome",
                    "Add an email account to get started",
                    duration=None  # Persistent until dismissed
                )
                return
            
            if auto_connect:
                # Connect to the first account
                first_account = accounts[0]
                self.authenticate_account(first_account['email'])
        
        except Exception as e:
            logger.error(f"Error loading accounts: {str(e)}")
            self.notification_service.show_notification(
                "Error",
                f"Failed to load email accounts: {str(e)}",
                NotificationType.ERROR
            )
    
    def show_add_account_dialog(self):
        """Show dialog to add a new email account."""
        from .email_account_dialog import EmailAccountDialog
        dialog = EmailAccountDialog(self)
        if dialog.exec():
            # Refresh accounts and authenticate new account
            self.load_accounts()
            if dialog.account_data:
                self.authenticate_account(dialog.account_data['email'])
    
    def show_manage_accounts_dialog(self):
        """Show dialog to manage email accounts."""
        from .email_accounts_tab import EmailAccountsTab
        dialog = QDialog(self)
        dialog.setWindowTitle("Manage Email Accounts")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout(dialog)
        accounts_tab = EmailAccountsTab(dialog)
        layout.addWidget(accounts_tab)
        
        # Add close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.exec()
    
    def refresh_accounts(self):
        # Move to background thread
        self.loading_indicator.start()
        threading.Thread(target=self._async_refresh).start()