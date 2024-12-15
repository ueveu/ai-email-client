from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                           QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from account_manager import AccountManager
from ui.email_account_dialog import EmailAccountDialog
from utils.logger import logger

class ManageAccountsDialog(QDialog):
    """Dialog for managing email accounts."""
    
    def __init__(self, parent=None):
        """Initialize the dialog."""
        super().__init__(parent)
        self.account_manager = AccountManager()
        self.setup_ui()
        self.load_accounts()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Manage Email Accounts")
        self.setMinimumSize(600, 400)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Create accounts table
        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(3)
        self.accounts_table.setHorizontalHeaderLabels(['Email', 'Server Settings', 'Status'])
        self.accounts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.accounts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.accounts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.accounts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.accounts_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.accounts_table)
        
        # Buttons layout
        button_layout = QHBoxLayout()
        
        # Add Account button
        self.add_btn = QPushButton("Add Account")
        self.add_btn.setIcon(QIcon("resources/icons/add.png"))
        self.add_btn.clicked.connect(self.add_account)
        button_layout.addWidget(self.add_btn)
        
        # Edit Account button
        self.edit_btn = QPushButton("Edit Account")
        self.edit_btn.setIcon(QIcon("resources/icons/edit.png"))
        self.edit_btn.clicked.connect(self.edit_account)
        button_layout.addWidget(self.edit_btn)
        
        # Remove Account button
        self.remove_btn = QPushButton("Remove Account")
        self.remove_btn.setIcon(QIcon("resources/icons/remove.png"))
        self.remove_btn.clicked.connect(self.remove_account)
        button_layout.addWidget(self.remove_btn)
        
        # Close button
        self.close_btn = QPushButton("Close")
        self.close_btn.setIcon(QIcon("resources/icons/close.png"))
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        # Update button states
        self.update_button_states()
    
    def load_accounts(self):
        """Load and display accounts in the table."""
        try:
            # Clear existing items
            self.accounts_table.setRowCount(0)
            
            # Get all accounts
            accounts = self.account_manager.get_all_accounts()
            
            # Add accounts to table
            for account in accounts:
                row = self.accounts_table.rowCount()
                self.accounts_table.insertRow(row)
                
                # Email column
                email_item = QTableWidgetItem(account['email'])
                email_item.setFlags(email_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.accounts_table.setItem(row, 0, email_item)
                
                # Server settings column
                server_info = f"IMAP: {account.get('imap_server', 'N/A')}\nSMTP: {account.get('smtp_server', 'N/A')}"
                server_item = QTableWidgetItem(server_info)
                server_item.setFlags(server_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.accounts_table.setItem(row, 1, server_item)
                
                # Status column
                status_item = QTableWidgetItem("Connected")  # You can update this based on actual connection status
                status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.accounts_table.setItem(row, 2, status_item)
            
            # Update button states
            self.update_button_states()
            
        except Exception as e:
            logger.error(f"Error loading accounts: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                "Failed to load email accounts. Please try again."
            )
    
    def update_button_states(self):
        """Update button enabled states based on selection."""
        has_selection = bool(self.accounts_table.selectedItems())
        self.edit_btn.setEnabled(has_selection)
        self.remove_btn.setEnabled(has_selection)
    
    def add_account(self):
        """Open dialog to add a new account."""
        dialog = EmailAccountDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_accounts()
    
    def edit_account(self):
        """Open dialog to edit selected account."""
        selected_row = self.accounts_table.currentRow()
        if selected_row >= 0:
            email = self.accounts_table.item(selected_row, 0).text()
            account_data = self.account_manager.get_account(email)
            if account_data:
                dialog = EmailAccountDialog(self, account_data)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.load_accounts()
    
    def remove_account(self):
        """Remove selected account."""
        selected_row = self.accounts_table.currentRow()
        if selected_row >= 0:
            email = self.accounts_table.item(selected_row, 0).text()
            
            reply = QMessageBox.question(
                self,
                "Confirm Removal",
                f"Are you sure you want to remove the account {email}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if self.account_manager.remove_account(email):
                    self.load_accounts()
                else:
                    QMessageBox.critical(
                        self,
                        "Error",
                        "Failed to remove account. Please try again."
                    )
    
    def showEvent(self, event):
        """Handle dialog show event."""
        super().showEvent(event)
        self.load_accounts()  # Refresh accounts when dialog is shown
        
    def closeEvent(self, event):
        """Handle dialog close event."""
        super().closeEvent(event)
        # You can add cleanup code here if needed 