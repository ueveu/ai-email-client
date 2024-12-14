from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                           QTabWidget, QMenuBar, QMessageBox)
from PyQt6.QtCore import Qt
from ui.email_accounts_tab import EmailAccountsTab
from ui.email_analysis_tab import EmailAnalysisTab
from resources import Resources
from config import Config
from email_manager import EmailManager
from security.credential_manager import CredentialManager
from utils.error_handler import handle_errors
from utils.logger import logger

class MainWindow(QMainWindow):
    """
    Main application window that contains all UI elements and manages
    the overall application layout.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(Resources.APP_NAME)
        self.setMinimumSize(800, 600)
        self.setWindowIcon(Resources.get_app_icon())
        
        # Initialize managers
        self.config = Config()
        self.credential_manager = CredentialManager()
        self.email_manager = None
        
        # Create the central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Initialize UI components
        self.setup_menu_bar()
        self.setup_tabs()
        
        # Load accounts into UI
        self.load_accounts()
        
        logger.logger.info("MainWindow initialized successfully")
    
    def handle_error(self, error_type, error_message):
        """
        Handle errors reported by the error handler.
        
        Args:
            error_type (str): Type of the error
            error_message (str): Error message
        """
        logger.logger.error(f"Error in MainWindow: {error_type} - {error_message}")
        
        # Show error in status bar if available
        self.statusBar().showMessage(f"Error: {error_message}", 5000)
    
    @handle_errors
    def setup_menu_bar(self):
        """Creates the application menu bar with basic options."""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction("Settings")
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)
        
        # Add status bar
        self.statusBar()
    
    @handle_errors
    def setup_tabs(self):
        """Creates the main tab widget with different sections of the application."""
        self.tab_widget = QTabWidget()
        
        # Add tabs for different functionalities
        self.email_accounts_tab = EmailAccountsTab()
        self.email_analysis_tab = EmailAnalysisTab()
        
        self.tab_widget.addTab(self.email_accounts_tab, "Email Accounts")
        self.tab_widget.addTab(self.email_analysis_tab, "Email Analysis")
        
        self.layout.addWidget(self.tab_widget)
        
        # Connect signals
        self.email_accounts_tab.account_added.connect(self.on_account_added)
        self.email_accounts_tab.account_removed.connect(self.on_account_removed)
        self.email_accounts_tab.account_updated.connect(self.on_account_updated)
        self.email_analysis_tab.account_selector.currentIndexChanged.connect(
            self.on_account_selected
        )
    
    @handle_errors
    def load_accounts(self):
        """Load configured email accounts into the UI."""
        try:
            accounts = self.config.get_accounts()
            
            # Update accounts tab
            self.email_accounts_tab.load_accounts(accounts)
            
            # Update account selector in analysis tab
            self.email_analysis_tab.account_selector.clear()
            for account in accounts:
                self.email_analysis_tab.account_selector.addItem(
                    account['email'],
                    account
                )
            
            logger.logger.info(f"Loaded {len(accounts)} email accounts")
            
        except Exception as e:
            logger.log_error(e, {'context': 'Loading accounts'})
            raise
    
    @handle_errors
    def on_account_added(self, account_data):
        """Handle new account addition."""
        try:
            self.config.add_account(account_data)
            self.load_accounts()
            logger.logger.info(f"Added new account: {account_data['email']}")
            self.statusBar().showMessage("Account added successfully", 3000)
            
        except Exception as e:
            logger.log_error(e, {
                'context': 'Adding account',
                'account': account_data['email']
            })
            raise
    
    @handle_errors
    def on_account_removed(self, email):
        """Handle account removal."""
        try:
            self.config.remove_account(email)
            self.credential_manager.delete_email_credentials(email)
            self.load_accounts()
            
            # If the removed account was selected, clear the email manager
            if self.email_manager and self.email_manager.account_data['email'] == email:
                self.email_manager = None
                self.email_analysis_tab.set_email_manager(None)
            
            logger.logger.info(f"Removed account: {email}")
            self.statusBar().showMessage("Account removed successfully", 3000)
            
        except Exception as e:
            logger.log_error(e, {
                'context': 'Removing account',
                'account': email
            })
            raise
    
    @handle_errors
    def on_account_updated(self, email, account_data):
        """
        Handle account updates.
        
        Args:
            email (str): Original email address of the account
            account_data (dict): Updated account configuration
        """
        try:
            # Update the configuration
            self.config.update_account(email, account_data)
            
            # If the updated account is currently selected, update the email manager
            if (self.email_manager and 
                self.email_manager.account_data['email'] == email):
                # Get credentials for the updated account
                credentials = self.credential_manager.get_email_credentials(account_data['email'])
                if credentials and 'password' in credentials:
                    # Create new account data with password
                    account_with_password = account_data.copy()
                    account_with_password['password'] = credentials['password']
                    
                    # Create new email manager with updated settings
                    self.email_manager = EmailManager(account_with_password)
                    self.email_analysis_tab.set_email_manager(self.email_manager)
            
            # Reload all accounts to update the UI
            self.load_accounts()
            
            logger.logger.info(f"Updated account: {email}")
            self.statusBar().showMessage("Account updated successfully", 3000)
            
        except Exception as e:
            logger.log_error(e, {
                'context': 'Updating account',
                'account': email
            })
            raise
    
    @handle_errors
    def on_account_selected(self, index):
        """Handle account selection in the analysis tab."""
        try:
            if index < 0:
                self.email_manager = None
                self.email_analysis_tab.set_email_manager(None)
                return
            
            # Get account data and credentials
            account_data = self.email_analysis_tab.account_selector.currentData()
            if not account_data:
                return
            
            credentials = self.credential_manager.get_email_credentials(account_data['email'])
            if not credentials or 'password' not in credentials:
                return
            
            # Create account data with password
            account_with_password = account_data.copy()
            account_with_password['password'] = credentials['password']
            
            # Create and set email manager
            self.email_manager = EmailManager(account_with_password)
            self.email_analysis_tab.set_email_manager(self.email_manager)
            
            logger.logger.info(f"Selected account: {account_data['email']}")
            
        except Exception as e:
            logger.log_error(e, {
                'context': 'Selecting account',
                'index': index
            })
            raise
    
    @handle_errors
    def show_about(self):
        """Show the about dialog."""
        QMessageBox.about(
            self,
            "About " + Resources.APP_NAME,
            f"{Resources.APP_NAME} v{Resources.APP_VERSION}\n\n"
            "An AI-powered email assistant that helps manage emails\n"
            "and generate intelligent replies."
        ) 