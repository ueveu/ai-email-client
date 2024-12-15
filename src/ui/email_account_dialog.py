from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                           QPushButton, QSpinBox, QCheckBox, QMessageBox,
                           QHBoxLayout, QLabel, QInputDialog, QGroupBox,
                           QStatusBar, QButtonGroup, QRadioButton, QDialogButtonBox,
                           QTabWidget, QTableWidget, QTableWidgetItem)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
import re
from email_providers import EmailProviders, Provider
from services.credential_service import CredentialService
from utils.logger import logger
from utils.error_handler import handle_errors
import imaplib
import smtplib
import ssl
from PyQt6.QtWidgets import QApplication
from account_manager import AccountManager

class EmailAccountDialog(QDialog):
    """Dialog for managing email account settings."""
    
    def __init__(self, parent=None, account_data=None):
        """
        Initialize dialog.
        
        Args:
            parent: Parent widget
            account_data (dict, optional): Existing account data for editing
        """
        super().__init__(parent)
        self.account_manager = AccountManager()
        self.credential_service = CredentialService()
        self.account_data = account_data
        self.setup_ui()
        
        # Load existing accounts
        self.load_accounts()
        
        if account_data:
            self.load_account_data(account_data)
    
    def setup_ui(self):
        """Set up the dialog UI components."""
        self.setWindowTitle("Manage Email Accounts")
        layout = QVBoxLayout(self)
        
        # Create tab widget for better organization
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create account list widget
        self.account_list = QTableWidget()
        self.account_list.setColumnCount(3)
        self.account_list.setHorizontalHeaderLabels(['Email', 'Server Settings', 'Status'])
        self.account_list.horizontalHeader().setStretchLastSection(True)
        self.account_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.account_list.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.account_list.itemSelectionChanged.connect(self.on_account_selected)
        
        # Add account list to first tab
        self.tab_widget.addTab(self.account_list, "Accounts")
        
        # Button layout
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
        self.edit_btn.setEnabled(False)
        button_layout.addWidget(self.edit_btn)
        
        # Remove Account button
        self.remove_btn = QPushButton("Remove Account")
        self.remove_btn.setIcon(QIcon("resources/icons/delete.png"))
        self.remove_btn.clicked.connect(self.remove_account)
        self.remove_btn.setEnabled(False)
        button_layout.addWidget(self.remove_btn)
        
        # Close button
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        # Status bar
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
    
    def load_accounts(self):
        """Load and display existing email accounts."""
        try:
            # Clear existing items
            self.account_list.setRowCount(0)
            
            # Get accounts from account manager
            accounts = self.account_manager.get_all_accounts()
            
            # Add accounts to table
            for account in accounts:
                row = self.account_list.rowCount()
                self.account_list.insertRow(row)
                
                # Email column
                email_item = QTableWidgetItem(account['email'])
                email_item.setData(Qt.ItemDataRole.UserRole, account)  # Store full account data
                self.account_list.setItem(row, 0, email_item)
                
                # Server settings column
                server_info = f"IMAP: {account['imap_server']}:{account['imap_port']}\n"
                server_info += f"SMTP: {account['smtp_server']}:{account['smtp_port']}"
                server_item = QTableWidgetItem(server_info)
                self.account_list.setItem(row, 1, server_item)
                
                # Status column
                status_item = QTableWidgetItem("Connected")  # You can update this based on actual connection status
                self.account_list.setItem(row, 2, status_item)
            
            # Adjust column widths
            self.account_list.resizeColumnsToContents()
            
            # Update status
            self.status_bar.showMessage(f"Loaded {len(accounts)} account(s)")
            
        except Exception as e:
            logger.error(f"Error loading accounts: {str(e)}")
            self.status_bar.showMessage("Error loading accounts")
    
    def on_account_selected(self):
        """Handle account selection."""
        selected = len(self.account_list.selectedItems()) > 0
        self.edit_btn.setEnabled(selected)
        self.remove_btn.setEnabled(selected)
    
    def add_account(self):
        """Add a new email account."""
        try:
            dialog = EmailAccountDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_accounts()  # Refresh the account list
                self.status_bar.showMessage("Account added successfully")
        except Exception as e:
            logger.error(f"Error adding account: {str(e)}")
            self.status_bar.showMessage("Error adding account")
    
    def edit_account(self):
        """Edit the selected email account."""
        try:
            selected_items = self.account_list.selectedItems()
            if not selected_items:
                    return
                
            # Get account data from the first column (email)
            account_data = self.account_list.item(selected_items[0].row(), 0).data(Qt.ItemDataRole.UserRole)
            
            dialog = EmailAccountDialog(self, account_data)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_accounts()  # Refresh the account list
                self.status_bar.showMessage("Account updated successfully")
        except Exception as e:
            logger.error(f"Error editing account: {str(e)}")
            self.status_bar.showMessage("Error editing account")
    
    def remove_account(self):
        """Remove the selected email account."""
        try:
            selected_items = self.account_list.selectedItems()
            if not selected_items:
                return

            # Get account data
            account_data = self.account_list.item(selected_items[0].row(), 0).data(Qt.ItemDataRole.UserRole)
            
            # Confirm deletion
            reply = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to remove the account {account_data['email']}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if self.account_manager.remove_account(account_data['email']):
                    self.load_accounts()  # Refresh the account list
                    self.status_bar.showMessage("Account removed successfully")
            else:
                    self.status_bar.showMessage("Failed to remove account")
        except Exception as e:
            logger.error(f"Error removing account: {str(e)}")
            self.status_bar.showMessage("Error removing account") 