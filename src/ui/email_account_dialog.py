from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                            QLineEdit, QFormLayout, QPushButton, QSpinBox,
                            QCheckBox, QMessageBox, QProgressDialog, QGroupBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import imaplib
import smtplib
import ssl
from email.mime.text import MIMEText
from security.credential_manager import CredentialManager
from email_providers import EmailProviders, Provider
from utils.error_handler import handle_errors
from utils.logger import logger
import socket
import re

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
        """Test IMAP connection with detailed error handling and status reporting."""
        try:
            # Create progress steps
            self.finished.emit(False, "IMAP", "Connecting to server...")
            
            # Set timeout for operations
            socket.setdefaulttimeout(30)  # 30 seconds timeout
            
            if self.settings['imap_ssl']:
                # Create SSL context with modern security settings
                context = ssl.create_default_context()
                context.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3
                
                server = imaplib.IMAP4_SSL(
                    self.settings['imap_server'],
                    self.settings['imap_port'],
                    ssl_context=context
                )
            else:
                server = imaplib.IMAP4(
                    self.settings['imap_server'],
                    self.settings['imap_port']
                )
            
            self.finished.emit(False, "IMAP", "Authenticating...")
            
            try:
                server.login(self.settings['email'], self.settings['password'])
            except imaplib.IMAP4.error as e:
                if "AUTHENTICATIONFAILED" in str(e):
                    raise Exception("Authentication failed. Please check your email and password.")
                elif "INVALID" in str(e):
                    raise Exception("Invalid credentials. Please verify your login details.")
                else:
                    raise
            
            self.finished.emit(False, "IMAP", "Checking mailbox access...")
            
            # Test mailbox access
            try:
                server.select('INBOX')
            except imaplib.IMAP4.error:
                raise Exception("Could not access INBOX. Please check mailbox permissions.")
            
            # Test basic operations
            try:
                # List folders to verify permissions
                server.list()
                # Check INBOX status
                server.status('INBOX', '(MESSAGES)')
            except imaplib.IMAP4.error:
                raise Exception("Limited mailbox access. Please check account permissions.")
            
            server.logout()
            self.finished.emit(True, "IMAP", "IMAP connection successful! All tests passed.")
            
        except socket.gaierror:
            self.finished.emit(False, "IMAP", "Could not resolve server address. Please check server settings.")
        except socket.timeout:
            self.finished.emit(False, "IMAP", "Connection timed out. Please check your internet connection and server settings.")
        except ssl.SSLError as e:
            self.finished.emit(False, "IMAP", f"SSL/TLS error: {str(e)}. Please check your security settings.")
        except ConnectionRefusedError:
            self.finished.emit(False, "IMAP", "Connection refused. Please verify server and port settings.")
        except Exception as e:
            self.finished.emit(False, "IMAP", str(e))
        finally:
            # Reset timeout to default
            socket.setdefaulttimeout(None)
    
    def _test_smtp(self):
        """Test SMTP connection with detailed error handling and status reporting."""
        try:
            # Create progress steps
            self.finished.emit(False, "SMTP", "Connecting to server...")
            
            # Set timeout for operations
            socket.setdefaulttimeout(30)  # 30 seconds timeout
            
            # Create SSL context with modern security settings
            context = ssl.create_default_context()
            context.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3
            
            try:
                if self.settings['smtp_ssl']:
                    self.finished.emit(False, "SMTP", "Establishing secure connection (SSL)...")
                    server = smtplib.SMTP_SSL(
                        self.settings['smtp_server'],
                        self.settings['smtp_port'],
                        context=context,
                        timeout=30
                    )
                else:
                    server = smtplib.SMTP(
                        self.settings['smtp_server'],
                        self.settings['smtp_port'],
                        timeout=30
                    )
                    self.finished.emit(False, "SMTP", "Starting TLS encryption...")
                    server.starttls(context=context)
            except ssl.SSLError as e:
                if "WRONG_VERSION_NUMBER" in str(e):
                    raise Exception(
                        "SSL/TLS version error. Try " + 
                        ("disabling" if self.settings['smtp_ssl'] else "enabling") +
                        " SSL/TLS or using a different port."
                    )
                raise
            
            self.finished.emit(False, "SMTP", "Authenticating...")
            
            try:
                server.login(self.settings['email'], self.settings['password'])
            except smtplib.SMTPAuthenticationError:
                raise Exception("Authentication failed. Please check your email and password.")
            except smtplib.SMTPNotSupportedError:
                raise Exception("Authentication method not supported. Try enabling/disabling SSL/TLS.")
            
            # Test sending capability
            self.finished.emit(False, "SMTP", "Verifying send capability...")
            
            try:
                server.verify(self.settings['email'])
            except (smtplib.SMTPServerDisconnected, smtplib.SMTPResponseException):
                raise Exception("Could not verify sending capability. Please check server permissions.")
            
            server.quit()
            self.finished.emit(True, "SMTP", "SMTP connection successful! All tests passed.")
            
        except socket.gaierror:
            self.finished.emit(False, "SMTP", "Could not resolve server address. Please check server settings.")
        except socket.timeout:
            self.finished.emit(False, "SMTP", "Connection timed out. Please check your internet connection and server settings.")
        except ssl.SSLError as e:
            self.finished.emit(False, "SMTP", f"SSL/TLS error: {str(e)}. Please check your security settings.")
        except ConnectionRefusedError:
            self.finished.emit(False, "SMTP", "Connection refused. Please verify server and port settings.")
        except smtplib.SMTPConnectError:
            self.finished.emit(False, "SMTP", "Failed to connect to server. Please check server settings and firewall rules.")
        except smtplib.SMTPHeloError:
            self.finished.emit(False, "SMTP", "Server rejected HELO. Please check if server allows connections from your IP.")
        except smtplib.SMTPException as e:
            self.finished.emit(False, "SMTP", f"SMTP error: {str(e)}")
        except Exception as e:
            self.finished.emit(False, "SMTP", str(e))
        finally:
            # Reset timeout to default
            socket.setdefaulttimeout(None)

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
        """Sets up the UI components."""
        layout = QVBoxLayout(self)
        
        # Set window title based on mode
        self.setWindowTitle("Edit Email Account" if self.account_data else "Add Email Account")
        
        # Quick Setup Section (only show for new accounts)
        if not self.account_data:
            quick_setup = QGroupBox("Quick Setup")
            quick_layout = QVBoxLayout()
            
            # Provider login buttons
            provider_buttons = QHBoxLayout()
            
            # Gmail button with logo
            gmail_btn = QPushButton("Login with Gmail")
            gmail_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    border: 1px solid #dadce0;
                    border-radius: 4px;
                    padding: 8px 16px;
                    color: #3c4043;
                }
                QPushButton:hover {
                    background-color: #f8f9fa;
                    border-color: #d2e3fc;
                }
            """)
            gmail_btn.clicked.connect(lambda: self.provider_login(Provider.GMAIL))
            provider_buttons.addWidget(gmail_btn)
            
            # Outlook button with logo
            outlook_btn = QPushButton("Login with Outlook")
            outlook_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    border: 1px solid #dadce0;
                    border-radius: 4px;
                    padding: 8px 16px;
                    color: #3c4043;
                }
                QPushButton:hover {
                    background-color: #f8f9fa;
                    border-color: #d2e3fc;
                }
            """)
            outlook_btn.clicked.connect(lambda: self.provider_login(Provider.OUTLOOK))
            provider_buttons.addWidget(outlook_btn)
            
            # Yahoo button with logo
            yahoo_btn = QPushButton("Login with Yahoo")
            yahoo_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    border: 1px solid #dadce0;
                    border-radius: 4px;
                    padding: 8px 16px;
                    color: #3c4043;
                }
                QPushButton:hover {
                    background-color: #f8f9fa;
                    border-color: #d2e3fc;
                }
            """)
            yahoo_btn.clicked.connect(lambda: self.provider_login(Provider.YAHOO))
            provider_buttons.addWidget(yahoo_btn)
            
            quick_layout.addLayout(provider_buttons)
            
            # Add a label with instructions
            instructions = QLabel(
                "Click one of the buttons above to log in to your email provider.\n"
                "You will be redirected to the provider's login page."
            )
            instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
            quick_layout.addWidget(instructions)
            
            quick_setup.setLayout(quick_layout)
            layout.addWidget(quick_setup)
        
        # Manual Setup Section
        manual_setup = QGroupBox("Account Settings")
        form_layout = QFormLayout()
        
        # Email account details
        self.email_input = QLineEdit()
        self.email_input.textChanged.connect(self.on_email_changed)
        # Disable email field in edit mode
        if self.account_data:
            self.email_input.setEnabled(False)
            self.email_input.setToolTip("Email address cannot be changed")
        
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
        
        manual_setup.setLayout(form_layout)
        layout.addWidget(manual_setup)
        
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
        
        # Update button labels for edit mode
        if self.account_data:
            self.save_button.setText("Update")
            self.test_button.setText("Verify Connections")
    
    @handle_errors
    def provider_login(self, provider: Provider):
        """
        Handle direct login for a provider.
        Opens the provider's OAuth login page in the default browser.
        
        Args:
            provider (Provider): Email provider to login with
        """
        config = EmailProviders.get_provider_config(provider)
        if not config:
            return
        
        # Pre-configure server settings
        self.imap_server.setText(config.imap_server)
        self.imap_port.setValue(config.imap_port)
        self.imap_ssl.setChecked(config.imap_ssl)
        self.smtp_server.setText(config.smtp_server)
        self.smtp_port.setValue(config.smtp_port)
        self.smtp_ssl.setChecked(config.smtp_ssl)
        
        # Open provider's login page
        EmailProviders.open_provider_setup(provider)
        
        # Show instructions
        QMessageBox.information(
            self,
            "Login Instructions",
            f"1. Log in to your {config.name} account in the browser\n"
            f"2. Allow the requested permissions\n"
            f"3. Copy the app password and paste it here\n\n"
            f"Note: If you have 2-factor authentication enabled,\n"
            f"you'll need to use an App Password."
        )
    
    @handle_errors
    def on_email_changed(self, email):
        """Auto-configure settings based on email address."""
        if not email:
            return
        
        config = EmailProviders.get_config_for_email(email)
        if config:
            # Auto-fill server settings
            self.imap_server.setText(config.imap_server)
            self.imap_port.setValue(config.imap_port)
            self.imap_ssl.setChecked(config.imap_ssl)
            self.smtp_server.setText(config.smtp_server)
            self.smtp_port.setValue(config.smtp_port)
            self.smtp_ssl.setChecked(config.smtp_ssl)
    
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
        """Get account data from form fields."""
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
    
    @handle_errors
    def validate_server_settings(self):
        """
        Validate server settings before saving/testing.
        
        Returns:
            tuple: (bool, str) - (is_valid, error_message)
        """
        settings = self.get_account_data()
        
        # Validate email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", settings['email']):
            return False, "Invalid email address format"
        
        # Validate server addresses
        if not settings['imap_server']:
            return False, "IMAP server address is required"
        if not settings['smtp_server']:
            return False, "SMTP server address is required"
        
        # Validate ports
        if not (0 < settings['imap_port'] <= 65535):
            return False, "Invalid IMAP port number"
        if not (0 < settings['smtp_port'] <= 65535):
            return False, "Invalid SMTP port number"
        
        # Validate SSL settings based on common ports
        if settings['imap_port'] == 993 and not settings['imap_ssl']:
            return False, "Port 993 requires SSL to be enabled for IMAP"
        if settings['smtp_port'] == 465 and not settings['smtp_ssl']:
            return False, "Port 465 requires SSL to be enabled for SMTP"
        
        # Validate password
        if not settings['password']:
            return False, "Password is required"
        if len(settings['password']) < 8:
            return False, "Password must be at least 8 characters long"
        
        return True, ""
    
    @handle_errors
    def validate_and_accept(self):
        """Validate the form data before accepting."""
        # Validate server settings
        is_valid, error_message = self.validate_server_settings()
        if not is_valid:
            QMessageBox.warning(self, "Validation Error", error_message)
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
            
            # Show success message
            action = "updated" if self.account_data else "added"
            QMessageBox.information(
                self,
                "Success",
                f"Account successfully {action}!"
            )
            
            self.account_data = account_data
            self.accept()
            
        except Exception as e:
            logger.log_error(e, {'context': 'Storing credentials'})
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to store credentials securely: {str(e)}"
            )
    
    @handle_errors
    def test_connection(self, server_type):
        """Test connection to email server with detailed progress feedback."""
        # Validate server settings first
        is_valid, error_message = self.validate_server_settings()
        if not is_valid:
            QMessageBox.warning(self, "Validation Error", error_message)
            return
        
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
            self.test_imap_btn.setEnabled(False)
        else:
            self.smtp_tester = tester
            self.test_smtp_btn.setEnabled(False)
        
        # Show progress dialog with detailed status
        self.progress = QProgressDialog(
            f"Initializing {server_type} test...",
            "Cancel",
            0,
            0,
            self
        )
        self.progress.setWindowTitle(f"Testing {server_type} Connection")
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress.setAutoClose(True)
        self.progress.setMinimumDuration(0)
        self.progress.canceled.connect(self.cancel_test)
        self.progress.show()
        
        # Start the test
        tester.start()
    
    def cancel_test(self):
        """Cancel ongoing connection test."""
        if self.imap_tester and self.imap_tester.isRunning():
            self.imap_tester.terminate()
            self.imap_tester = None
            self.test_imap_btn.setEnabled(True)
        
        if self.smtp_tester and self.smtp_tester.isRunning():
            self.smtp_tester.terminate()
            self.smtp_tester = None
            self.test_smtp_btn.setEnabled(True)
    
    def handle_test_result(self, success, server_type, message):
        """Handle the connection test result with detailed feedback."""
        # Update progress dialog
        if self.progress and self.progress.isVisible():
            self.progress.setLabelText(message)
            
            if success or "failed" in message.lower() or "error" in message.lower():
                self.progress.cancel()
        
        # Re-enable test buttons
        if server_type == "IMAP":
            self.test_imap_btn.setEnabled(True)
            self.imap_tester = None
        else:
            self.test_smtp_btn.setEnabled(True)
            self.smtp_tester = None
        
        # Show result
        if success:
            QMessageBox.information(
                self,
                f"{server_type} Test Successful",
                message,
                QMessageBox.StandardButton.Ok
            )
        else:
            QMessageBox.warning(
                self,
                f"{server_type} Test Failed",
                message,
                QMessageBox.StandardButton.Ok
            )
    
    @handle_errors
    def test_all_connections(self, *args):
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