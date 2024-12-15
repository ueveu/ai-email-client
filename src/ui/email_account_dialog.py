from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                           QPushButton, QSpinBox, QCheckBox, QMessageBox,
                           QHBoxLayout, QLabel, QInputDialog, QGroupBox,
                           QStatusBar, QButtonGroup, QRadioButton, QDialogButtonBox,
                           QApplication)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
import re
from email_providers import EmailProviders, Provider
from services.credential_service import CredentialService
from account_manager import AccountManager
from utils.logger import logger
from utils.error_handler import handle_errors
import imaplib
import smtplib
import ssl

class EmailAccountDialog(QDialog):
    """Dialog for adding or editing an email account."""
    
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
        
        if account_data:
            self.load_account_data(account_data)
    
    def setup_ui(self):
        """Set up the dialog UI components."""
        self.setWindowTitle("Email Account")
        layout = QVBoxLayout(self)
        
        # Create form layout
        form_layout = QFormLayout()
        
        # Email field
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@gmail.com")
        form_layout.addRow("Email:", self.email_input)
        
        # Password field
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Password:", self.password_input)
        
        # Server settings group
        server_group = QGroupBox("Server Settings")
        server_layout = QFormLayout()
        
        # IMAP settings
        self.imap_server = QLineEdit()
        self.imap_port = QSpinBox()
        self.imap_port.setRange(1, 65535)
        self.imap_port.setValue(993)
        self.imap_ssl = QCheckBox("Use SSL")
        self.imap_ssl.setChecked(True)
        
        server_layout.addRow("IMAP Server:", self.imap_server)
        server_layout.addRow("IMAP Port:", self.imap_port)
        server_layout.addRow("", self.imap_ssl)
        
        # SMTP settings
        self.smtp_server = QLineEdit()
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(587)
        self.smtp_ssl = QCheckBox("Use SSL/TLS")
        self.smtp_ssl.setChecked(True)
        
        server_layout.addRow("SMTP Server:", self.smtp_server)
        server_layout.addRow("SMTP Port:", self.smtp_port)
        server_layout.addRow("", self.smtp_ssl)
        
        server_group.setLayout(server_layout)
        
        # Add form and server settings to main layout
        layout.addLayout(form_layout)
        layout.addWidget(server_group)
        
        # Add test connection button
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self.test_connection)
        layout.addWidget(test_btn)
        
        # Add dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Add status bar
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        
        self.setMinimumWidth(400)
        
        # Connect email field to auto-detect provider
        self.email_input.textChanged.connect(self.auto_detect_provider)
    
    def auto_detect_provider(self, email):
        """Auto-detect email provider and set server settings."""
        if not email or '@' not in email:
            return
            
        provider = EmailProviders.detect_provider(email)
        if provider:
            # Set IMAP settings
            self.imap_server.setText(provider.imap_server)
            self.imap_port.setValue(provider.imap_port)
            self.imap_ssl.setChecked(provider.imap_ssl)
            
            # Set SMTP settings
            self.smtp_server.setText(provider.smtp_server)
            self.smtp_port.setValue(provider.smtp_port)
            self.smtp_ssl.setChecked(provider.smtp_ssl)
    
    def load_account_data(self, account_data):
        """Load existing account data into the form."""
        self.email_input.setText(account_data['email'])
        self.email_input.setEnabled(False)  # Don't allow email change when editing
        
        self.imap_server.setText(account_data['imap_server'])
        self.imap_port.setValue(account_data['imap_port'])
        self.imap_ssl.setChecked(account_data.get('imap_ssl', True))
        
        self.smtp_server.setText(account_data['smtp_server'])
        self.smtp_port.setValue(account_data['smtp_port'])
        self.smtp_ssl.setChecked(account_data.get('smtp_ssl', True))
    
    def get_account_data(self):
        """Get account data from the form."""
        return {
            'email': self.email_input.text(),
            'imap_server': self.imap_server.text(),
            'imap_port': self.imap_port.value(),
            'imap_ssl': self.imap_ssl.isChecked(),
            'smtp_server': self.smtp_server.text(),
            'smtp_port': self.smtp_port.value(),
            'smtp_ssl': self.smtp_ssl.isChecked()
        }
    
    def accept(self):
        """Handle dialog acceptance."""
        account_data = self.get_account_data()
        
        # Validate required fields
        if not all([account_data['email'], account_data['imap_server'], 
                   account_data['smtp_server'], self.password_input.text()]):
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please fill in all required fields."
            )
            return
        
        try:
            # Test connection before saving
            self.status_bar.showMessage("Testing connection...")
            QApplication.processEvents()  # Update UI
            
            if not self.test_connection(show_success_message=False):
                # Connection test failed, don't save
                return
            
            # Store account data
            if self.account_data:  # Editing existing account
                self.account_manager.update_account(account_data['email'], account_data)
            else:  # Adding new account
                self.account_manager.add_account(account_data)
            
            # Store credentials
            credentials = {
                'type': 'password',
                'password': self.password_input.text()
            }
            if not self.credential_service.store_email_credentials(account_data['email'], credentials):
                raise Exception("Failed to store credentials")
            
            self.status_bar.showMessage("Account saved successfully")
            super().accept()
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            QMessageBox.warning(
                self,
                "Validation Error",
                str(e)
            )
        except Exception as e:
            logger.error(f"Error saving account: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save account: {str(e)}"
            )
    
    @handle_errors
    def test_connection(self, show_success_message=True):
        """
        Test the email server connection.
        
        Args:
            show_success_message (bool): Whether to show success message
            
        Returns:
            bool: True if connection test was successful
        """
        account_data = self.get_account_data()
        password = self.password_input.text()
        
        if not all([account_data['email'], account_data['imap_server'], 
                   account_data['smtp_server'], password]):
            self.status_bar.showMessage("Please fill in all required fields")
            return False
        
        self.status_bar.showMessage("Testing connection...")
        QApplication.processEvents()  # Update UI
        
        try:
            # Test IMAP connection
            if account_data['imap_ssl']:
                imap = imaplib.IMAP4_SSL(account_data['imap_server'], 
                                       account_data['imap_port'])
            else:
                imap = imaplib.IMAP4(account_data['imap_server'], 
                                   account_data['imap_port'])
            
            try:
                imap.login(account_data['email'], password)
                imap.logout()
            except Exception as e:
                raise Exception(f"IMAP authentication failed: {str(e)}")
            
            # Test SMTP connection
            context = ssl.create_default_context()
            
            if account_data['smtp_ssl']:
                smtp = smtplib.SMTP(account_data['smtp_server'], 
                                  account_data['smtp_port'])
                smtp.starttls(context=context)
            else:
                smtp = smtplib.SMTP(account_data['smtp_server'], 
                                  account_data['smtp_port'])
            
            try:
                smtp.login(account_data['email'], password)
                smtp.quit()
            except Exception as e:
                raise Exception(f"SMTP authentication failed: {str(e)}")
            
            self.status_bar.showMessage("Connection test successful!")
            
            if show_success_message:
                QMessageBox.information(
                    self,
                    "Connection Test",
                    "Successfully connected to both IMAP and SMTP servers!"
                )
            
            return True
            
        except Exception as e:
            self.status_bar.showMessage("Connection test failed")
            
            # Show detailed error message
            error_msg = str(e)
            if "Authentication failed" in error_msg:
                error_msg += "\n\nPlease check your email and password."
                if "@gmail.com" in account_data['email'].lower():
                    error_msg += "\n\nFor Gmail accounts, you need to use an App Password. " \
                               "Go to your Google Account settings to generate one."
            
            QMessageBox.critical(
                self,
                "Connection Test Failed",
                f"Error: {error_msg}"
            )
            return False 