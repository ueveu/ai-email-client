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
        self.email_manager = None  # Will be set when account is selected
        
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
        """Authenticate and connect to an email account."""
        try:
            # Get account credentials
            account_data = self.account_manager.get_account(email)
            if not account_data:
                logger.error(f"No account data found for {email}")
                return
            
            # Create email manager instance
            self.email_manager = EmailManager(
                account_data,
                self.credential_service,
                self.operation_service
            )
            
            # Set email manager in analysis tab
            self.email_analysis_tab.set_email_manager(self.email_manager)
            
            # Show success notification
            self.notification_service.show_notification(
                "Connected",
                f"Successfully connected to {email}",
                NotificationType.SUCCESS
            )
            
        except Exception as e:
            logger.error(f"Error authenticating account: {str(e)}")
            self.notification_service.show_notification(
                "Connection Error",
                f"Failed to connect to {email}: {str(e)}",
                NotificationType.ERROR
            )
    
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
    
    def _setup_network_monitoring(self):
        """Set up network connectivity monitoring."""
        # Create timer for network checks
        self.network_timer = QTimer(self)
        self.network_timer.timeout.connect(self._check_network_status)
        self.network_timer.start(30000)  # Check every 30 seconds
        
        # Initial check
        self._check_network_status()
    
    def _check_network_status(self):
        """Check network connectivity status."""
        is_online = self.network_service.check_connectivity()
        
        # Update UI
        self.status_bar.set_online_status(is_online)
        
        if not is_online and not self.offline_action.isChecked():
            # Automatically switch to offline mode
            self.offline_action.setChecked(True)
            self.toggle_offline_mode()
            
            # Notify user
            self.notification_service.add_notification(
                "Network Connection Lost",
                "Switched to offline mode. Using cached emails.",
                "warning"
            )
        elif is_online and self.offline_action.isChecked():
            # Ask user if they want to go back online
            reply = QMessageBox.question(
                self,
                "Network Connection Available",
                "Network connection is available. Would you like to go back online?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.offline_action.setChecked(False)
                self.toggle_offline_mode()
    
    def toggle_offline_mode(self):
        """Toggle offline mode."""
        is_offline = self.offline_action.isChecked()
        
        # Update email manager
        if hasattr(self.email_tab, 'email_manager'):
            self.email_tab.email_manager.set_offline_mode(is_offline)
        
        # Update UI
        self.status_bar.set_online_status(not is_offline)
        
        # Refresh emails in current view
        self.email_tab.refresh_emails()
        
        # Show notification
        mode = "offline" if is_offline else "online"
        self.notification_service.add_notification(
            f"Switched to {mode} mode",
            f"Now working in {mode} mode",
            "info"
        )
    
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