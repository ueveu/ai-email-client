from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                           QTableWidget, QTableWidgetItem, QHBoxLayout,
                           QMessageBox, QSplitter, QHeaderView)
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
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        
        # Create accounts panel
        accounts_panel = QWidget()
        accounts_layout = QVBoxLayout(accounts_panel)
        
        # Create accounts table
        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(3)
        self.accounts_table.setHorizontalHeaderLabels(["Email", "Server Settings", "Status"])
        self.accounts_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.accounts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.accounts_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        accounts_layout.addWidget(self.accounts_table)
        
        # Create button layout
        button_layout = QHBoxLayout()
        
        # Add account button
        self.add_account_btn = QPushButton("Add Account")
        self.add_account_btn.clicked.connect(self.add_account)
        button_layout.addWidget(self.add_account_btn)
        
        # Edit account button
        self.edit_account_btn = QPushButton("Edit Account")
        self.edit_account_btn.clicked.connect(self.edit_account)
        self.edit_account_btn.setEnabled(False)
        button_layout.addWidget(self.edit_account_btn)
        
        # Remove account button
        self.remove_account_btn = QPushButton("Remove Account")
        self.remove_account_btn.clicked.connect(self.remove_account)
        self.remove_account_btn.setEnabled(False)
        button_layout.addWidget(self.remove_account_btn)
        
        button_layout.addStretch()
        accounts_layout.addLayout(button_layout)
        
        # Add accounts panel to main layout
        layout.addWidget(accounts_panel)
        
        # Connect signals
        self.accounts_table.itemSelectionChanged.connect(self.on_selection_changed)
    
    def on_selection_changed(self):
        """Handle selection changes in the accounts table."""
        has_selection = bool(self.accounts_table.selectedItems())
        self.edit_account_btn.setEnabled(has_selection)
        self.remove_account_btn.setEnabled(has_selection)
    
    def load_accounts(self, accounts):
        """
        Load accounts into the table.
        
        Args:
            accounts (list): List of account data dictionaries
        """
        logger.debug(f"Loading {len(accounts)} accounts into table")
        self.accounts = accounts
        self.accounts_table.setRowCount(0)
        
        for account in accounts:
            logger.debug(f"Adding account to table: {account['email']}")
            row = self.accounts_table.rowCount()
            self.accounts_table.insertRow(row)
            
            # Add account data
            self.accounts_table.setItem(row, 0, QTableWidgetItem(account['email']))
            server_text = f"IMAP: {account['imap_server']}, SMTP: {account['smtp_server']}"
            self.accounts_table.setItem(row, 1, QTableWidgetItem(server_text))
            
            # Check account status
            has_credentials = bool(self.credential_manager.get_email_credentials(account['email']))
            status = "Connected" if has_credentials else "Not Connected"
            self.accounts_table.setItem(row, 2, QTableWidgetItem(status))
        
        self.accounts_table.resizeColumnsToContents()
        logger.debug("Finished loading accounts into table")
    
    def add_account(self):
        """Opens dialog to add a new email account."""
        dialog = EmailAccountDialog(self)
        if dialog.exec():
            account_data = dialog.account_data
            self.account_added.emit(account_data)
            
            # Refresh table
            if account_data:
                self.accounts.append(account_data)
                self.load_accounts(self.accounts)
    
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
            
            # Update accounts list and refresh table
            for i, acc in enumerate(self.accounts):
                if acc['email'] == email:
                    self.accounts[i] = updated_data
                    break
            self.load_accounts(self.accounts)
    
    @handle_errors
    def remove_account(self, email: str):
        """Remove an email account with confirmation."""
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the account {email}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.account_manager.remove_account(email):
                logger.info(f"Account {email} removed successfully")
                self.account_removed.emit(email)
                QMessageBox.information(
                    self,
                    "Account Removed",
                    f"The account {email} has been removed successfully."
                )
            else:
                logger.error(f"Failed to remove account {email}")
                QMessageBox.critical(
                    self,
                    "Removal Failed",
                    f"Failed to remove the account {email}. Please try again."
                )