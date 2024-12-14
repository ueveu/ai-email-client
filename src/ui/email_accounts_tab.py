from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                           QTableWidget, QTableWidgetItem, QHBoxLayout,
                           QMessageBox)
from PyQt6.QtCore import pyqtSignal
from ui.email_account_dialog import EmailAccountDialog
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
        self.setup_ui()
    
    def setup_ui(self):
        """Sets up the UI components for the email accounts tab."""
        layout = QVBoxLayout(self)
        
        # Create account list table
        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(3)
        self.accounts_table.setHorizontalHeaderLabels(["Email", "Server", "Status"])
        self.accounts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.accounts_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
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
        
        # Add widgets to main layout
        layout.addWidget(self.accounts_table)
        layout.addLayout(button_layout)
        
        # Connect selection signal
        self.accounts_table.itemSelectionChanged.connect(self.on_selection_changed)
    
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
    
    @handle_errors
    def refresh_folders(self):
        """Refresh the folder list in the folder tree."""
        if hasattr(self, 'folder_tree'):
            folders = self.parent.email_manager.list_folders()
            self.folder_tree.update_folders(folders)
    
    @handle_errors
    def on_account_selection_changed(self):
        """Update folder tree when account selection changes."""
        selected_items = self.accounts_table.selectedItems()
        if not selected_items:
            # Clear folder tree if no account selected
            self.folder_tree.clear()
            return
        
        # Get selected account email
        email = selected_items[0].text()
        account_data = next((acc for acc in self.accounts if acc['email'] == email), None)
        if not account_data:
            return
        
        # Update folder tree if email manager exists
        if hasattr(self.parent, 'email_manager'):
            folders = self.parent.email_manager.list_folders()
            self.folder_tree.update_folders(folders)