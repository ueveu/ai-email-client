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
from ui.folder_tree import FolderTree

class MainWindow(QMainWindow):
    """
    Main window of the AI Email Assistant application.
    Manages tabs, menus, and overall application state.
    """
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        self.email_manager = None
        self.config = Config()
        self.credential_manager = CredentialManager()
        self.setup_ui()
        self.load_accounts()
    
    def setup_ui(self):
        """Set up the main window UI components."""
        logger.logger.debug("Setting up MainWindow UI")
        
        # Set window properties
        self.setWindowTitle("AI Email Assistant")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create and add tabs
        self.email_accounts_tab = EmailAccountsTab(self)
        self.email_analysis_tab = EmailAnalysisTab(self)
        
        self.tab_widget.addTab(self.email_accounts_tab, "Email Accounts")
        self.tab_widget.addTab(self.email_analysis_tab, "Email Analysis")
        
        # Connect signals
        logger.logger.debug("Connecting signals")
        self.email_accounts_tab.account_added.connect(self.on_account_added)
        self.email_accounts_tab.account_removed.connect(self.on_account_removed)
        self.email_accounts_tab.account_updated.connect(self.on_account_updated)
        
        # Connect account selection signal
        self.email_accounts_tab.accounts_table.itemSelectionChanged.connect(self.on_account_selection_changed)
        
        # Create status bar
        self.statusBar().showMessage("Ready")
    
    def load_accounts(self):
        """Load email accounts from configuration."""
        try:
            logger.logger.debug("Loading accounts from configuration")
            accounts = self.config.get_accounts()
            logger.logger.info(f"Loaded {len(accounts)} email accounts")
            
            # Update accounts tab
            self.email_accounts_tab.load_accounts(accounts)
            
            # Update analysis tab account selector
            self.email_analysis_tab.account_selector.clear()
            for account in accounts:
                self.email_analysis_tab.account_selector.addItem(
                    account['email'],
                    account
                )
            
            # If we have accounts but no email manager, initialize with first account
            if accounts and not self.email_manager:
                self.initialize_email_manager(accounts[0])
            
        except Exception as e:
            logger.logger.error(f"Error loading accounts: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                "Failed to load email accounts. Please check the configuration."
            )
    
    def initialize_email_manager(self, account_data):
        """Initialize email manager with account data."""
        try:
            logger.logger.debug(f"Initializing email manager for {account_data['email']}")
            
            # Get credentials
            credentials = self.credential_manager.get_email_credentials(account_data['email'])
            if not credentials or 'password' not in credentials:
                logger.logger.warning(f"No credentials found for {account_data['email']}")
                return
            
            # Create account data with password
            account_with_password = account_data.copy()
            account_with_password['password'] = credentials['password']
            
            # Create email manager
            self.email_manager = EmailManager(account_with_password)
            
            # Test connection
            if not self.email_manager.connect_imap():
                logger.logger.error("Failed to connect to IMAP server")
                QMessageBox.warning(
                    self,
                    "Connection Failed",
                    "Failed to connect to email server. Please check your settings."
                )
                self.email_manager = None
                return
            
            # Set email manager in analysis tab
            self.email_analysis_tab.set_email_manager(self.email_manager)
            logger.logger.info(f"Email manager initialized for {account_data['email']}")
            
        except Exception as e:
            logger.logger.error(f"Error initializing email manager: {str(e)}")
            self.email_manager = None
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to initialize email manager: {str(e)}"
            )
    
    def on_account_selection_changed(self):
        """Handle account selection change in accounts tab."""
        selected_items = self.email_accounts_tab.accounts_table.selectedItems()
        if not selected_items:
            return
        
        row = selected_items[0].row()
        email = self.email_accounts_tab.accounts_table.item(row, 0).text()
        
        # Find account data
        for account in self.config.get_accounts():
            if account['email'] == email:
                self.initialize_email_manager(account)
                break
    
    @handle_errors
    def on_account_added(self, account_data):
        """Handle new account addition."""
        try:
            logger.logger.debug(f"Adding new account: {account_data['email']}")
            
            # Add to configuration
            self.config.add_account(account_data)
            logger.logger.debug("Account added to configuration")
            
            # Reload accounts
            self.load_accounts()
            
            # Initialize email manager if this is the first account
            if len(self.config.get_accounts()) == 1:
                self.initialize_email_manager(account_data)
            
            logger.logger.info(f"Added new account: {account_data['email']}")
            self.statusBar().showMessage("Account added successfully", 3000)
            
        except Exception as e:
            logger.logger.error(f"Error adding account: {str(e)}")
            raise
    
    @handle_errors
    def on_account_removed(self, email):
        """Handle account removal."""
        try:
            self.config.remove_account(email)
            self.credential_manager.delete_email_credentials(email)
            
            # If the removed account was selected, clear the email manager
            if self.email_manager and self.email_manager.account_data['email'] == email:
                self.email_manager = None
                self.email_analysis_tab.set_email_manager(None)
            
            # Reload accounts
            self.load_accounts()
            
            logger.logger.info(f"Removed account: {email}")
            self.statusBar().showMessage("Account removed successfully", 3000)
            
        except Exception as e:
            logger.logger.error(f"Error removing account: {str(e)}")
            raise
    
    @handle_errors
    def on_account_updated(self, email, new_data):
        """Handle account update."""
        try:
            self.config.update_account(email, new_data)
            
            # If the updated account is currently selected, reinitialize email manager
            if self.email_manager and self.email_manager.account_data['email'] == email:
                self.initialize_email_manager(new_data)
            
            # Reload accounts
            self.load_accounts()
            
            logger.logger.info(f"Updated account: {email}")
            self.statusBar().showMessage("Account updated successfully", 3000)
            
        except Exception as e:
            logger.logger.error(f"Error updating account: {str(e)}")
            raise
    
    @handle_errors
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
    def create_menu_bar(self):
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
    def show_about(self):
        """Show the about dialog."""
        QMessageBox.about(
            self,
            "About " + Resources.APP_NAME,
            f"{Resources.APP_NAME} v{Resources.APP_VERSION}\n\n"
            "An AI-powered email assistant that helps manage emails\n"
            "and generate intelligent replies."
        ) 
    
    @handle_errors
    def handle_folder_created(self, folder_name: str):
        """Handle folder creation request."""
        logger.logger.debug(f"Creating folder: {folder_name}")
        
        if not self.email_manager.create_folder(folder_name):
            QMessageBox.warning(
                self,
                "Folder Creation Failed",
                f"Failed to create folder '{folder_name}'. Please try again."
            )
            return
        
        # Refresh folder list
        self.email_accounts_tab.refresh_folders()
    
    @handle_errors
    def handle_folder_deleted(self, folder_name: str):
        """Handle folder deletion request."""
        logger.logger.debug(f"Deleting folder: {folder_name}")
        
        if not self.email_manager.delete_folder(folder_name):
            QMessageBox.warning(
                self,
                "Folder Deletion Failed",
                f"Failed to delete folder '{folder_name}'. Please try again."
            )
            return
        
        # Refresh folder list
        self.email_accounts_tab.refresh_folders()
    
    @handle_errors
    def handle_folder_renamed(self, old_name: str, new_name: str):
        """Handle folder renaming request."""
        logger.logger.debug(f"Renaming folder from {old_name} to {new_name}")
        
        if not self.email_manager.rename_folder(old_name, new_name):
            QMessageBox.warning(
                self,
                "Folder Rename Failed",
                f"Failed to rename folder from '{old_name}' to '{new_name}'. Please try again."
            )
            return
        
        # Refresh folder list
        self.email_accounts_tab.refresh_folders() 
    
    def setup_folder_tree(self):
        """Set up the folder tree widget."""
        self.folder_tree = FolderTree(self)
        self.folder_tree.folder_selected.connect(self.on_folder_selected)
        self.folder_tree.folder_created.connect(self.on_folder_created)
        self.folder_tree.folder_deleted.connect(self.on_folder_deleted)
        self.folder_tree.folder_renamed.connect(self.on_folder_renamed)
        self.folder_tree.email_moved.connect(self.on_email_moved)
        
        # Add refresh button to toolbar
        refresh_action = QAction(QIcon.fromTheme('view-refresh'), 'Refresh Folders', self)
        refresh_action.triggered.connect(self.refresh_folders)
        self.toolbar.addAction(refresh_action)
    
    def refresh_folders(self):
        """Refresh folder list and status."""
        if self.email_manager:
            self.folder_tree.start_sync()
            if self.email_manager.sync_folders():
                folders = self.email_manager.list_folders()
                self.folder_tree.update_folders(folders)
                self.folder_tree.finish_sync()
            else:
                QMessageBox.warning(
                    self,
                    "Sync Failed",
                    "Failed to synchronize folders. Please check your connection."
                )
    
    def on_email_moved(self, message_id: str, target_folder: str):
        """
        Handle moving an email to a different folder.
        
        Args:
            message_id (str): ID of the email to move
            target_folder (str): Name of the target folder
        """
        if not self.email_manager:
            return
        
        try:
            # Move the email
            if self.email_manager.move_email(message_id, target_folder):
                # Update folder status
                source_folder = self.folder_tree.selected_folder
                if source_folder:
                    source_status = self.email_manager.get_folder_status(source_folder)
                    self.folder_tree.update_folder_status(source_folder, source_status)
                
                target_status = self.email_manager.get_folder_status(target_folder)
                self.folder_tree.update_folder_status(target_folder, target_status)
                
                # Refresh email list if we're in the source or target folder
                current_folder = self.folder_tree.selected_folder
                if current_folder in [source_folder, target_folder]:
                    self.load_emails(current_folder)
            else:
                QMessageBox.warning(
                    self,
                    "Move Failed",
                    f"Failed to move email to {target_folder}."
                )
        except Exception as e:
            logger.logger.error(f"Error moving email: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while moving the email: {str(e)}"
            ) 