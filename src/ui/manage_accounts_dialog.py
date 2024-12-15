from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QPushButton, 
                           QTableWidget, QTableWidgetItem, QHBoxLayout,
                           QMessageBox, QStatusBar, QDialogButtonBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from .email_account_dialog import EmailAccountDialog
from account_manager import AccountManager
from utils.logger import logger
from utils.error_handler import handle_errors

class ManageAccountsDialog(QDialog):
    """Dialog for managing email accounts."""
    
    def __init__(self, parent=None):
        """Initialize dialog."""
        super().__init__(parent)
        self.account_manager = AccountManager()
        self.setup_ui()
        self.load_accounts()
    
    def setup_ui(self):
        """Set up the dialog UI components."""
        self.setWindowTitle("Manage Email Accounts")
        layout = QVBoxLayout(self)
        
        # Create account list widget
        self.account_list = QTableWidget()
        self.account_list.setColumnCount(3)
        self.account_list.setHorizontalHeaderLabels(['Email', 'Server Settings', 'Status'])
        self.account_list.horizontalHeader().setStretchLastSection(True)
        self.account_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.account_list.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.account_list.itemSelectionChanged.connect(self.on_account_selected)
        layout.addWidget(self.account_list)
        
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
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Add dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Status bar
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        
        self.setMinimumWidth(800)
        self.setMinimumHeight(400)
    
    def load_accounts(self):
        """Load and display existing email accounts."""
        try:
            # Clear existing items
            self.account_list.setRowCount(0)
            
            # Get accounts from account manager
            accounts = self.account_manager.get_all_accounts()
            
            if not accounts:
                self.status_bar.showMessage("No email accounts configured")
                return
            
            # Add accounts to table
            for account in accounts:
                row = self.account_list.rowCount()
                self.account_list.insertRow(row)
                
                # Email column
                email_item = QTableWidgetItem(account['email'])
                email_item.setData(Qt.ItemDataRole.UserRole, account)  # Store full account data
                self.account_list.setItem(row, 0, email_item)
                
                # Server settings column
                server_info = f"IMAP: {account['imap_server']}:{account['imap_port']}"
                if account.get('imap_ssl', True):
                    server_info += " (SSL)"
                server_info += f"\nSMTP: {account['smtp_server']}:{account['smtp_port']}"
                if account.get('smtp_ssl', True):
                    server_info += " (SSL/TLS)"
                server_item = QTableWidgetItem(server_info)
                self.account_list.setItem(row, 1, server_item)
                
                # Status column
                try:
                    credentials = self.account_manager.get_email_credentials(account['email'])
                    if credentials:
                        status = "Configured"
                        if credentials.get('type') == 'oauth':
                            status += " (OAuth)"
                    else:
                        status = "No Credentials"
                except Exception as e:
                    logger.error(f"Error checking credentials for {account['email']}: {str(e)}")
                    status = "Error"
                
                status_item = QTableWidgetItem(status)
                self.account_list.setItem(row, 2, status_item)
            
            # Adjust column widths
            self.account_list.resizeColumnsToContents()
            
            # Update status
            self.status_bar.showMessage(f"Loaded {len(accounts)} account(s)")
            
        except Exception as e:
            logger.error(f"Error loading accounts: {str(e)}")
            self.status_bar.showMessage("Error loading accounts")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load accounts: {str(e)}"
            )
    
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
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to add account: {str(e)}"
            )
    
    def edit_account(self):
        """Edit the selected email account."""
        try:
            selected_items = self.account_list.selectedItems()
            if not selected_items:
                return
            
            # Get account data from the first column (email)
            account_data = self.account_list.item(selected_items[0].row(), 0).data(Qt.ItemDataRole.UserRole)
            if not account_data:
                raise ValueError("No account data found")
            
            dialog = EmailAccountDialog(self, account_data)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_accounts()  # Refresh the account list
                self.status_bar.showMessage("Account updated successfully")
        except Exception as e:
            logger.error(f"Error editing account: {str(e)}")
            self.status_bar.showMessage("Error editing account")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to edit account: {str(e)}"
            )
    
    @handle_errors
    def remove_account(self, event=None):
        """Remove the selected email account."""
        try:
            selected_items = self.account_list.selectedItems()
            if not selected_items:
                logger.debug("No account selected for removal")
                return
            
            # Get account data
            email = self.account_list.item(selected_items[0].row(), 0).text()
            
            # Confirm deletion
            reply = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to remove the account {email}?\n\n"
                "This will delete all account data and credentials.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                logger.info(f"Removing account: {email}")
                
                # First remove credentials
                try:
                    self.account_manager.credential_manager.remove_credentials(email)
                    logger.info(f"Credentials removed for account: {email}")
                except Exception as e:
                    logger.error(f"Error removing credentials for {email}: {str(e)}")
                    # Continue with account removal even if credential removal fails
                
                # Then remove account configuration
                if self.account_manager.remove_account(email):
                    self.load_accounts()  # Refresh the account list
                    self.status_bar.showMessage(f"Account {email} removed successfully")
                    logger.info(f"Account removed successfully: {email}")
                else:
                    raise Exception(f"Failed to remove account: {email}")
                    
        except Exception as e:
            error_msg = f"Error removing account: {str(e)}"
            logger.error(error_msg)
            self.status_bar.showMessage("Error removing account")
            QMessageBox.critical(
                self,
                "Error",
                error_msg
            )
    
    def showEvent(self, event):
        """Handle dialog show event."""
        super().showEvent(event)
        self.load_accounts()  # Refresh accounts when dialog is shown
        
    def closeEvent(self, event):
        """Handle dialog close event."""
        super().closeEvent(event)
        # You can add cleanup code here if needed 