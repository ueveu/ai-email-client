from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                           QTabWidget, QMenuBar)
from PyQt6.QtCore import Qt
from ui.email_accounts_tab import EmailAccountsTab
from ui.email_analysis_tab import EmailAnalysisTab
from resources import Resources
from config import Config
from email_manager import EmailManager
from security.credential_manager import CredentialManager

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
    
    def setup_menu_bar(self):
        """Creates the application menu bar with basic options."""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction("Settings")
        file_menu.addSeparator()
        file_menu.addAction("Exit")
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction("About")
    
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
        self.email_analysis_tab.account_selector.currentIndexChanged.connect(
            self.on_account_selected
        )
    
    def load_accounts(self):
        """Load configured email accounts into the UI."""
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
    
    def on_account_added(self, account_data):
        """Handle new account addition."""
        self.config.add_account(account_data)
        self.load_accounts()
    
    def on_account_removed(self, email):
        """Handle account removal."""
        self.config.remove_account(email)
        self.credential_manager.delete_email_credentials(email)
        self.load_accounts()
    
    def on_account_selected(self, index):
        """Handle account selection in the analysis tab."""
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