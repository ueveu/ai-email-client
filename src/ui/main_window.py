"""
Main application window integrating all UI components.
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QSystemTrayIcon,
                           QMenu, QMenuBar, QToolBar, QDockWidget, QApplication, QDialog, QDialogButtonBox, QMessageBox,
                           QInputDialog, QLineEdit)
from PyQt6.QtCore import Qt, QSize, QSettings, QTimer
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
from .manage_accounts_dialog import ManageAccountsDialog
from .email_account_dialog import EmailAccountDialog
from utils.logger import logger
from .loading_spinner import LoadingSpinner
from services.network_service import NetworkService
from .email_analysis_tab import EmailAnalysisTab

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
        self.network_service = NetworkService()
        
        # Initialize email management
        self.account_manager = AccountManager()
        self.email_manager = EmailManager(self.credential_service, self.operation_service)
        
        # Add loading indicators
        self.loading_indicator = LoadingSpinner(self)
        
        # Set up UI
        self.setup_ui()
        self.setup_system_tray()
        self.setup_shortcuts()
        
        # Apply theme
        self.theme_service.apply_theme(self.theme_service.get_current_theme())
        
        # Load accounts and connect if auto-connect is enabled
        self.load_accounts()
        
        # Set up network monitoring
        self._setup_network_monitoring()
    
    def _setup_network_monitoring(self):
        """Set up network connectivity monitoring."""
        # Create network menu
        network_menu = self.menuBar().addMenu("&Network")
        
        # Work offline action
        self.offline_action = QAction("Work Offline", self)
        self.offline_action.setCheckable(True)
        self.offline_action.setStatusTip("Toggle offline mode")
        self.offline_action.triggered.connect(self._toggle_offline_mode)
        network_menu.addAction(self.offline_action)
        
        # Connect network service signals
        self.network_service.connection_changed.connect(self._on_connection_changed)
        
        # Start monitoring
        self.network_service.start_monitoring()
    
    def _toggle_offline_mode(self, checked: bool):
        """Toggle offline mode."""
        if checked:
            self.network_service.set_offline_mode(True)
            self.notification_service.show_notification(
                "Offline Mode",
                "Application is now working offline",
                NotificationType.INFO
            )
        else:
            self.network_service.set_offline_mode(False)
            self.notification_service.show_notification(
                "Online Mode",
                "Application is now working online",
                NotificationType.INFO
            )
    
    def _on_connection_changed(self, is_connected: bool):
        """Handle network connection changes."""
        # Update status bar
        self.status_bar.set_online_status(is_connected)
        
        # Show notification
        if is_connected:
            self.notification_service.show_notification(
                "Network Connected",
                "Internet connection is available",
                NotificationType.SUCCESS
            )
        else:
            self.notification_service.show_notification(
                "Network Disconnected",
                "No internet connection available",
                NotificationType.WARNING
            )
        
        # Update offline action
        self.offline_action.setChecked(not is_connected)
        
        # Handle email operations
        if not is_connected:
            # Pause active operations
            for operation in self.operation_service.get_active_operations():
                if operation.type in [
                    'send', 'fetch', 'sync', 'search'
                ]:
                    self.operation_service.cancel_operation(operation.id)
    
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
        
        # Create email analysis tab
        self.email_analysis_tab = EmailAnalysisTab(self)
        layout.addWidget(self.email_analysis_tab)
        
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
        
        # AI menu
        ai_menu = menubar.addMenu("&AI")
        
        # Gemini API key action
        gemini_api_action = QAction("Configure Gemini API Key...", self)
        gemini_api_action.setStatusTip("Set up or validate your Gemini API key")
        gemini_api_action.triggered.connect(self.configure_gemini_api)
        ai_menu.addAction(gemini_api_action)
        
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
    
    def authenticate_account(self, email: str):
        """Authenticate an email account and update UI."""
        try:
            # Get account credentials
            credentials = self.credential_service.get_email_credentials(email)
            if not credentials:
                logger.error(f"No credentials found for {email}")
                return False
            
            # Initialize email manager with account
            account_data = self.account_manager.get_account(email)
            if not account_data:
                logger.error(f"No account data found for {email}")
                return False
            
            # Create new email manager instance if needed
            if not self.email_manager:
                self.email_manager = EmailManager(self.credential_service, self.operation_service)
            
            # Initialize account
            self.email_manager.initialize_account(account_data, credentials)
            
            # Update UI components
            self.email_analysis_tab.set_email_manager(self.email_manager)
            
            # Show success notification
            self.notification_service.show_notification(
                "Connected",
                f"Successfully connected to {email}",
                NotificationType.SUCCESS
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating account {email}: {str(e)}")
            self.notification_service.show_notification(
                "Authentication Error",
                f"Failed to connect to {email}: {str(e)}",
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
            
            # Update email analysis tab with accounts
            self.email_analysis_tab.set_accounts(accounts)
            
            if not accounts:
                # Show welcome message if no accounts
                self.notification_service.show_notification(
                    "Welcome",
                    "Add an email account to get started by clicking File > Add Email Account",
                    NotificationType.INFO,
                    duration=None  # Persistent until dismissed
                )
                # Disable email-related UI elements
                self.email_analysis_tab.setEnabled(False)
                return
            
            # Enable UI if we have accounts
            self.email_analysis_tab.setEnabled(True)
            
            if auto_connect:
                # Connect to the first account
                first_account = accounts[0]
                if first_account:
                    self.authenticate_account(first_account['email'])
                    # Set the first account as active in the email analysis tab
                    self.email_analysis_tab.set_active_account(0)
        
        except Exception as e:
            logger.error(f"Error loading accounts: {str(e)}")
            self.notification_service.show_notification(
                "Error",
                f"Failed to load email accounts: {str(e)}",
                NotificationType.ERROR
            )
    
    def show_add_account_dialog(self):
        """Show dialog to add a new email account."""
        try:
            dialog = EmailAccountDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_accounts()
        except Exception as e:
            logger.error(f"Error showing add account dialog: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                "Failed to open account setup. Please try again."
            )
    
    def show_manage_accounts_dialog(self):
        """Show the manage accounts dialog."""
        try:
            dialog = ManageAccountsDialog(self)
            dialog.exec()
            
            # Refresh email accounts if needed
            self.load_accounts()
        except Exception as e:
            logger.error(f"Error showing manage accounts dialog: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                "Failed to open account management. Please try again."
            )
    
    def refresh_accounts(self):
        # Move to background thread
        self.loading_indicator.start()
        threading.Thread(target=self._async_refresh).start()
    
    def configure_gemini_api(self):
        """Configure and validate Gemini API key."""
        # Get current API key if exists
        current_key = self.ai_service.api_key_service.get_api_key('gemini') or ""
        
        # Show input dialog
        api_key, ok = QInputDialog.getText(
            self,
            "Gemini API Key Configuration",
            "Enter your Gemini API key:\n(Get it from https://makersuite.google.com/app/apikey)",
            QLineEdit.EchoMode.Password,
            current_key
        )
        
        if ok and api_key:
            # Show loading indicator
            self.loading_indicator.start()
            
            try:
                # Test the API key
                if self.ai_service.test_api_key(api_key):
                    # Save the valid key
                    self.ai_service.update_api_key(api_key)
                    
                    QMessageBox.information(
                        self,
                        "Success",
                        "Gemini API key validated and saved successfully!"
                    )
                    
                    # Show success notification
                    self.notification_service.show_notification(
                        "API Key Updated",
                        "Gemini API key has been validated and saved.",
                        NotificationType.SUCCESS
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Invalid API Key",
                        "The provided API key is invalid. Please check your key and try again."
                    )
            except Exception as e:
                logger.error(f"Error validating Gemini API key: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"An error occurred while validating the API key: {str(e)}"
                )
            finally:
                self.loading_indicator.stop()