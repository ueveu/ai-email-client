from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                            QLineEdit, QFormLayout, QPushButton, QSpinBox,
                            QCheckBox, QMessageBox, QProgressDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import imaplib
import smtplib
import ssl
from email.mime.text import MIMEText
from security.credential_manager import CredentialManager

class ConnectionTester(QThread):
    """
    Thread for testing email server connections without blocking the UI.
    """
    finished = pyqtSignal(bool, str, str)  # Success, Server Type, Message
    
    def __init__(self, server_type, settings):
        super().__init__()
        self.server_type = server_type
        self.settings = settings
    
    def run(self):
        try:
            if self.server_type == "IMAP":
                self._test_imap()
            else:
                self._test_smtp()
        except Exception as e:
            self.finished.emit(False, self.server_type, str(e))
    
    def _test_imap(self):
        try:
            if self.settings['imap_ssl']:
                server = imaplib.IMAP4_SSL(
                    self.settings['imap_server'],
                    self.settings['imap_port']
                )
            else:
                server = imaplib.IMAP4(
                    self.settings['imap_server'],
                    self.settings['imap_port']
                )
            
            server.login(self.settings['email'], self.settings['password'])
            server.select()  # Select INBOX to verify full connection
            server.logout()
            
            self.finished.emit(True, "IMAP", "IMAP connection successful")
        except Exception as e:
            self.finished.emit(False, "IMAP", f"IMAP connection failed: {str(e)}")
    
    def _test_smtp(self):
        try:
            if self.settings['smtp_ssl']:
                server = smtplib.SMTP_SSL(
                    self.settings['smtp_server'],
                    self.settings['smtp_port']
                )
            else:
                server = smtplib.SMTP(
                    self.settings['smtp_server'],
                    self.settings['smtp_port']
                )
                server.starttls()
            
            server.login(self.settings['email'], self.settings['password'])
            server.quit()
            
            self.finished.emit(True, "SMTP", "SMTP connection successful")
        except Exception as e:
            self.finished.emit(False, "SMTP", f"SMTP connection failed: {str(e)}")

class EmailAccountDialog(QDialog):
    def __init__(self, parent=None, account_data=None):
        super().__init__(parent)
        self.account_data = account_data or {}
        self.credential_manager = CredentialManager()
        self.setWindowTitle("Email Account Settings")
        self.setModal(True)
        
        # Initialize connection testers
        self.imap_tester = None
        self.smtp_tester = None
        
        self.setup_ui()
        
        if account_data:
            self.load_account_data()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create form layout for input fields
        form_layout = QFormLayout()
        
        # Email account details
        self.email_input = QLineEdit()
        self.name_input = QLineEdit()
        form_layout.addRow("Email Address:", self.email_input)
        form_layout.addRow("Display Name:", self.name_input)
        
        # IMAP settings
        form_layout.addRow(QLabel("IMAP Settings"))
        self.imap_server = QLineEdit()
        self.imap_port = QSpinBox()
        self.imap_port.setRange(1, 65535)
        self.imap_port.setValue(993)
        self.imap_ssl = QCheckBox("Use SSL")
        self.imap_ssl.setChecked(True)
        
        form_layout.addRow("IMAP Server:", self.imap_server)
        form_layout.addRow("IMAP Port:", self.imap_port)
        form_layout.addRow("", self.imap_ssl)
        
        # Add IMAP test button
        self.test_imap_btn = QPushButton("Test IMAP Connection")
        self.test_imap_btn.clicked.connect(lambda: self.test_connection("IMAP"))
        form_layout.addRow("", self.test_imap_btn)
        
        # SMTP settings
        form_layout.addRow(QLabel("SMTP Settings"))
        self.smtp_server = QLineEdit()
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(587)
        self.smtp_ssl = QCheckBox("Use SSL/TLS")
        self.smtp_ssl.setChecked(True)
        
        form_layout.addRow("SMTP Server:", self.smtp_server)
        form_layout.addRow("SMTP Port:", self.smtp_port)
        form_layout.addRow("", self.smtp_ssl)
        
        # Add SMTP test button
        self.test_smtp_btn = QPushButton("Test SMTP Connection")
        self.test_smtp_btn.clicked.connect(lambda: self.test_connection("SMTP"))
        form_layout.addRow("", self.test_smtp_btn)
        
        # Password field
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Password:", self.password_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.test_button = QPushButton("Test All Connections")
        self.test_button.clicked.connect(self.test_all_connections)
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.validate_and_accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.test_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def load_account_data(self):
        """Load existing account data into the form fields."""
        self.email_input.setText(self.account_data.get('email', ''))
        self.name_input.setText(self.account_data.get('name', ''))
        self.imap_server.setText(self.account_data.get('imap_server', ''))
        self.imap_port.setValue(self.account_data.get('imap_port', 993))
        self.imap_ssl.setChecked(self.account_data.get('imap_ssl', True))
        self.smtp_server.setText(self.account_data.get('smtp_server', ''))
        self.smtp_port.setValue(self.account_data.get('smtp_port', 587))
        self.smtp_ssl.setChecked(self.account_data.get('smtp_ssl', True))
        
        # Load password from secure storage
        if 'email' in self.account_data:
            credentials = self.credential_manager.get_email_credentials(self.account_data['email'])
            if credentials and 'password' in credentials:
                self.password_input.setText(credentials['password'])
    
    def get_account_data(self):
        return {
            'email': self.email_input.text(),
            'name': self.name_input.text(),
            'imap_server': self.imap_server.text(),
            'imap_port': self.imap_port.value(),
            'imap_ssl': self.imap_ssl.isChecked(),
            'smtp_server': self.smtp_server.text(),
            'smtp_port': self.smtp_port.value(),
            'smtp_ssl': self.smtp_ssl.isChecked(),
            'password': self.password_input.text()
        }
    
    def validate_and_accept(self):
        """Validate the form data before accepting."""
        if not self.email_input.text():
            QMessageBox.warning(self, "Validation Error", "Email address is required.")
            return
        
        if not self.imap_server.text():
            QMessageBox.warning(self, "Validation Error", "IMAP server is required.")
            return
        
        if not self.smtp_server.text():
            QMessageBox.warning(self, "Validation Error", "SMTP server is required.")
            return
        
        if not self.password_input.text():
            QMessageBox.warning(self, "Validation Error", "Password is required.")
            return
        
        # Store credentials securely
        account_data = self.get_account_data()
        try:
            # Store password securely
            self.credential_manager.store_email_credentials(
                account_data['email'],
                {'password': account_data['password']}
            )
            
            # Remove password from account data (it's now stored securely)
            del account_data['password']
            
            self.account_data = account_data
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to store credentials securely: {str(e)}"
            )
    
    def test_connection(self, server_type):
        """Test connection to email server."""
        settings = self.get_account_data()
        
        # Validate required fields
        if not settings['email'] or not settings['password']:
            QMessageBox.warning(self, "Validation Error", 
                              "Email and password are required for testing.")
            return
        
        if server_type == "IMAP" and not settings['imap_server']:
            QMessageBox.warning(self, "Validation Error", 
                              "IMAP server address is required.")
            return
        
        if server_type == "SMTP" and not settings['smtp_server']:
            QMessageBox.warning(self, "Validation Error", 
                              "SMTP server address is required.")
            return
        
        # Create and start the connection tester
        tester = ConnectionTester(server_type, settings)
        tester.finished.connect(self.handle_test_result)
        
        # Store the tester reference
        if server_type == "IMAP":
            self.imap_tester = tester
        else:
            self.smtp_tester = tester
        
        # Show progress dialog
        progress = QProgressDialog(
            f"Testing {server_type} connection...",
            "Cancel",
            0,
            0,
            self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setAutoClose(True)
        progress.canceled.connect(tester.terminate)
        progress.show()
        
        # Start the test
        tester.start()
    
    def test_all_connections(self):
        """Test both IMAP and SMTP connections."""
        self.test_connection("IMAP")
        self.test_connection("SMTP")
    
    def handle_test_result(self, success, server_type, message):
        """Handle the connection test result."""
        if success:
            QMessageBox.information(self, f"{server_type} Test", message)
        else:
            QMessageBox.warning(self, f"{server_type} Test Failed", message)
        
        # Clean up the tester
        if server_type == "IMAP":
            self.imap_tester = None
        else:
            self.smtp_tester = None 