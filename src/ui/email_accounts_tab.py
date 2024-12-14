from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                           QTableWidget, QTableWidgetItem, QHBoxLayout,
                           QMessageBox, QSplitter)
from PyQt6.QtCore import pyqtSignal, Qt
from ui.email_account_dialog import EmailAccountDialog
from ui.folder_tree import FolderTree
from ui.email_list_view import EmailListView
from utils.logger import logger
from utils.error_handler import handle_errors
from security.credential_manager import CredentialManager

class EmailAccountsTab(QWidget):
    """
    Tab for managing email accounts, including adding, editing,
    and removing email accounts with their IMAP/SMTP settings.
    """
    
    account_added = pyqtSignal(dict)  # Emitted when account is added
    account_removed = pyqtSignal(str)  # Emitted when account is removed (email)
    account_updated = pyqtSignal(str, dict)  # Emitted when account is updated (email, data)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.accounts = []  # List of account data dictionaries
        self.parent = parent  # Store reference to main window
        self.credential_manager = CredentialManager()
        self.setup_ui()
    
    def setup_ui(self):
        """Sets up the UI components for the email accounts tab."""
        layout = QVBoxLayout(self)
        
        # Create horizontal layout for accounts and folders
        h_layout = QHBoxLayout()
        
        # Create left panel for accounts
        accounts_panel = QWidget()
        accounts_layout = QVBoxLayout(accounts_panel)
        
        # Create account list table
        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(3)
        self.accounts_table.setHorizontalHeaderLabels(["Email", "Server", "Status"])
        self.accounts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.accounts_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        accounts_layout.addWidget(self.accounts_table)
        
        # Create button layout
        button_layout = QHBoxLayout()
        
        # Create buttons
        self.add_account_btn = QPushButton("Add Account")
        self.add_account_btn.clicked.connect(self.add_account)
        
        self.edit_account_btn = QPushButton("Edit Account")
        self.edit_account_btn.clicked.connect(self.edit_account)
        self.edit_account_btn.setEnabled(False)
        
        self.remove_account_btn = QPushButton("Remove Account")
        self.remove_account_btn.clicked.connect(self.remove_account)
        self.remove_account_btn.setEnabled(False)
        
        # Add buttons to layout
        button_layout.addWidget(self.add_account_btn)
        button_layout.addWidget(self.edit_account_btn)
        button_layout.addWidget(self.remove_account_btn)
        button_layout.addStretch()
        
        accounts_layout.addLayout(button_layout)
        
        # Create right panel with splitter for folders and emails
        right_panel = QSplitter(Qt.Orientation.Vertical)
        
        # Create folder tree
        self.folder_tree = FolderTree()
        right_panel.addWidget(self.folder_tree)
        
        # Create email list
        self.email_list = EmailListView()
        right_panel.addWidget(self.email_list)
        
        # Set initial splitter sizes (30% folders, 70% emails)
        right_panel.setSizes([300, 700])
        
        # Add panels to horizontal layout with splitter
        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        h_splitter.addWidget(accounts_panel)
        h_splitter.addWidget(right_panel)
        h_splitter.setSizes([300, 900])  # 25% accounts, 75% folders/emails
        
        # Add splitter to main layout
        layout.addWidget(h_splitter)
        
        # Connect signals
        self.accounts_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.folder_tree.folder_selected.connect(self.on_folder_selected)
        self.folder_tree.folder_created.connect(self.on_folder_created)
        self.folder_tree.folder_deleted.connect(self.on_folder_deleted)
        self.folder_tree.folder_renamed.connect(self.on_folder_renamed)
        self.email_list.email_moved.connect(self.on_email_moved)
    
    @handle_errors
    def on_folder_selected(self, folder_name):
        """Handle folder selection."""
        logger.logger.debug(f"Selected folder: {folder_name}")
        if hasattr(self.parent, 'email_manager'):
            # Fetch emails from selected folder
            emails = self.parent.email_manager.fetch_emails(folder=folder_name)
            self.email_list.update_emails(emails, folder_name)
            
            # Update folder status
            status = self.parent.email_manager.get_folder_status(folder_name)
            if status:
                self.folder_tree.update_folder_status(folder_name, status)
    
    @handle_errors
    def on_folder_created(self, folder_name):
        """Handle folder creation."""
        if hasattr(self.parent, 'email_manager'):
            if self.parent.email_manager.create_folder(folder_name):
                self.refresh_folders()
    
    @handle_errors
    def on_folder_deleted(self, folder_name):
        """Handle folder deletion."""
        if hasattr(self.parent, 'email_manager'):
            if self.parent.email_manager.delete_folder(folder_name):
                self.refresh_folders()
    
    @handle_errors
    def on_folder_renamed(self, old_name, new_name):
        """Handle folder renaming."""
        if hasattr(self.parent, 'email_manager'):
            if self.parent.email_manager.rename_folder(old_name, new_name):
                self.refresh_folders()
    
    @handle_errors
    def on_email_moved(self, message_id, target_folder):
        """Handle email movement between folders."""
        if hasattr(self.parent, 'email_manager'):
            if self.parent.email_manager.move_email(message_id, target_folder):
                # Refresh current folder
                current_folder = self.folder_tree.selected_folder
                if current_folder:
                    self.on_folder_selected(current_folder)
                
                # Update folder status
                self.refresh_folder_status()
    
    @handle_errors
    def refresh_folder_status(self):
        """Refresh status for all folders."""
        if not hasattr(self.parent, 'email_manager'):
            return
            
        for folder_name in self.folder_tree.folder_items:
            status = self.parent.email_manager.get_folder_status(folder_name)
            if status:
                self.folder_tree.update_folder_status(folder_name, status)
    
    @handle_errors
    def refresh_folders(self):
        """Refresh the folder list and status."""
        if hasattr(self.parent, 'email_manager'):
            folders = self.parent.email_manager.list_folders()
            self.folder_tree.update_folders(folders)
            self.refresh_folder_status()
            
            # Update available folders in email list
            self.email_list.update_folder_list(folders)
    
    def load_accounts(self, accounts):
        """
        Load accounts into the table.
        
        Args:
            accounts (list): List of account data dictionaries
        """
        logger.logger.debug(f"Loading {len(accounts)} accounts into table")
        self.accounts = accounts
        self.accounts_table.setRowCount(0)
        
        for account in accounts:
            logger.logger.debug(f"Adding account to table: {account['email']}")
            row = self.accounts_table.rowCount()
            self.accounts_table.insertRow(row)
            
            # Add account data
            self.accounts_table.setItem(row, 0, QTableWidgetItem(account['email']))
            server_text = f"IMAP: {account['imap_server']}, SMTP: {account['smtp_server']}"
            self.accounts_table.setItem(row, 1, QTableWidgetItem(server_text))
            self.accounts_table.setItem(row, 2, QTableWidgetItem("Connected"))  # TODO: Check actual status
        
        self.accounts_table.resizeColumnsToContents()
        logger.logger.debug("Finished loading accounts into table")
    
    def add_account(self):
        """Opens dialog to add a new email account."""
        dialog = EmailAccountDialog(self)
        if dialog.exec():
            account_data = dialog.account_data
            self.account_added.emit(account_data)
    
    def edit_account(self):
        """Opens dialog to edit the selected account."""
        row = self.accounts_table.currentRow()
        if row < 0:
            return
        
        email = self.accounts_table.item(row, 0).text()
        account_data = next((acc for acc in self.accounts if acc['email'] == email), None)
        if not account_data:
            return
        
        dialog = EmailAccountDialog(self, account_data)
        if dialog.exec():
            updated_data = dialog.account_data
            self.account_updated.emit(email, updated_data)
    
    @handle_errors
    def remove_account(self):
        """Removes the selected account after confirmation and cleanup."""
        row = self.accounts_table.currentRow()
        if row < 0:
            return
        
        email = self.accounts_table.item(row, 0).text()
        
        # Ask for confirmation with detailed warning
        reply = QMessageBox.warning(
            self,
            "Confirm Account Removal",
            f"Are you sure you want to remove the account {email}?\n\n"
            "This will:\n"
            "• Delete all account settings\n"
            "• Remove stored credentials\n"
            "• Close any active connections\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Close any active connections
                if hasattr(self.parent(), 'email_manager'):
                    email_manager = self.parent().email_manager
                    if email_manager and email_manager.account_data['email'] == email:
                        email_manager.close_connections()
                        self.parent().email_manager = None
                
                # Remove credentials first
                self.credential_manager.delete_email_credentials(email)
                
                # Emit signal to remove account from config
                self.account_removed.emit(email)
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Account Removed",
                    f"The account {email} has been successfully removed."
                )
                
            except Exception as e:
                logger.log_error(e, {
                    'context': 'Removing account',
                    'account': email
                })
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to remove account completely: {str(e)}\n"
                    "Some data might need to be cleaned up manually."
                )
    
    def on_selection_changed(self):
        """Handle table selection changes."""
        has_selection = len(self.accounts_table.selectedItems()) > 0
        self.edit_account_btn.setEnabled(has_selection)
        self.remove_account_btn.setEnabled(has_selection)