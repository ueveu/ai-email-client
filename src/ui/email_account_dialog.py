from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                           QPushButton, QSpinBox, QCheckBox, QMessageBox,
                           QHBoxLayout, QLabel, QInputDialog, QGroupBox,
                           QStatusBar)
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

class EmailAccountDialog(QDialog):
    """Dialog for adding or editing email account settings."""
    
    def __init__(self, parent=None, account_data=None):
        """
        Initialize dialog.
        
        Args:
            parent: Parent widget
            account_data (dict, optional): Existing account data for editing
        """
        super().__init__(parent)
        self.account_data = account_data
        self.credential_service = CredentialService()
        self.setup_ui()
        
        if account_data:
            self.load_account_data(account_data)
    
    def setup_ui(self):
        """Set up the dialog UI components."""
        self.setWindowTitle("Email Account Settings")
        layout = QVBoxLayout(self)
        
        # Create form layout for inputs
        form = QFormLayout()
        
        # Quick setup section with improved styling and tooltips
        quick_setup_group = QGroupBox("Quick Setup")
        quick_setup_layout = QVBoxLayout()
        
        quick_setup_label = QLabel("Choose your email provider for automatic setup:")
        quick_setup_label.setWordWrap(True)
        quick_setup_layout.addWidget(quick_setup_label)
        
        provider_layout = QHBoxLayout()
        
        # Gmail button with icon and tooltip
        gmail_btn = QPushButton("Gmail")
        gmail_btn.setIcon(QIcon("resources/icons/gmail.png"))  # You'll need to add these icons
        gmail_btn.setToolTip("Set up Gmail account with OAuth authentication")
        gmail_btn.clicked.connect(lambda: self.quick_setup_with_domain(Provider.GMAIL))
        provider_layout.addWidget(gmail_btn)
        
        outlook_btn = QPushButton("Outlook")
        outlook_btn.setIcon(QIcon("resources/icons/outlook.png"))
        outlook_btn.setToolTip("Set up Outlook/Hotmail account with OAuth authentication")
        outlook_btn.clicked.connect(lambda: self.quick_setup_with_domain(Provider.OUTLOOK))
        provider_layout.addWidget(outlook_btn)
        
        yahoo_btn = QPushButton("Yahoo")
        yahoo_btn.setIcon(QIcon("resources/icons/yahoo.png"))
        yahoo_btn.setToolTip("Set up Yahoo Mail account with OAuth authentication")
        yahoo_btn.clicked.connect(lambda: self.quick_setup_with_domain(Provider.YAHOO))
        provider_layout.addWidget(yahoo_btn)
        
        quick_setup_layout.addLayout(provider_layout)
        quick_setup_group.setLayout(quick_setup_layout)
        layout.addWidget(quick_setup_group)
        
        # Manual setup section
        manual_setup_group = QGroupBox("Manual Setup")
        manual_form = QFormLayout()
        
        # Email input with improved validation feedback
        email_layout = QHBoxLayout()
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your.name@example.com")
        self.email_input.textChanged.connect(self.validate_email)
        self.email_input.setToolTip("Enter your email address")
        email_layout.addWidget(self.email_input)
        
        self.validation_indicator = QLabel()
        self.validation_indicator.setFixedWidth(20)
        email_layout.addWidget(self.validation_indicator)
        
        manual_form.addRow("Email:", email_layout)
        
        # Server settings with collapsible advanced section
        server_settings = QGroupBox("Server Settings")
        server_form = QFormLayout()
        
        # IMAP settings
        imap_group = QGroupBox("IMAP (Incoming Mail)")
        imap_layout = QFormLayout()
        
        self.imap_server = QLineEdit()
        self.imap_server.setPlaceholderText("imap.example.com")
        self.imap_server.setToolTip("Enter your IMAP server address")
        imap_layout.addRow("Server:", self.imap_server)
        
        self.imap_port = QSpinBox()
        self.imap_port.setRange(1, 65535)
        self.imap_port.setValue(993)
        self.imap_port.setToolTip("Common ports: 993 (SSL) or 143 (non-SSL)")
        imap_layout.addRow("Port:", self.imap_port)
        
        self.imap_ssl = QCheckBox("Use SSL/TLS")
        self.imap_ssl.setChecked(True)
        self.imap_ssl.setToolTip("Enable for secure connection (recommended)")
        imap_layout.addRow("", self.imap_ssl)
        
        imap_group.setLayout(imap_layout)
        server_form.addRow(imap_group)
        
        # SMTP settings
        smtp_group = QGroupBox("SMTP (Outgoing Mail)")
        smtp_layout = QFormLayout()
        
        self.smtp_server = QLineEdit()
        self.smtp_server.setPlaceholderText("smtp.example.com")
        self.smtp_server.setToolTip("Enter your SMTP server address")
        smtp_layout.addRow("Server:", self.smtp_server)
        
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(587)
        self.smtp_port.setToolTip("Common ports: 587 (TLS) or 465 (SSL)")
        smtp_layout.addRow("Port:", self.smtp_port)
        
        self.smtp_ssl = QCheckBox("Use SSL/TLS")
        self.smtp_ssl.setChecked(True)
        self.smtp_ssl.setToolTip("Enable for secure connection (recommended)")
        smtp_layout.addRow("", self.smtp_ssl)
        
        smtp_group.setLayout(smtp_layout)
        server_form.addRow(smtp_group)
        
        server_settings.setLayout(server_form)
        manual_form.addRow(server_settings)
        
        # Password field with show/hide toggle
        password_layout = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter your password or app password")
        self.password_input.setToolTip("For Gmail, Outlook, and Yahoo, use an app password")
        password_layout.addWidget(self.password_input)
        
        self.show_password_btn = QPushButton()
        self.show_password_btn.setIcon(QIcon("resources/icons/eye.png"))
        self.show_password_btn.setCheckable(True)
        self.show_password_btn.setToolTip("Show/hide password")
        self.show_password_btn.clicked.connect(self.toggle_password_visibility)
        password_layout.addWidget(self.show_password_btn)
        
        manual_form.addRow("Password:", password_layout)
        
        manual_setup_group.setLayout(manual_form)
        layout.addWidget(manual_setup_group)
        
        # Buttons with improved layout and feedback
        button_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.setIcon(QIcon("resources/icons/test.png"))
        self.test_btn.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_btn)
        
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.setIcon(QIcon("resources/icons/save.png"))
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setIcon(QIcon("resources/icons/cancel.png"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Status bar for feedback
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        
        # Set default focus
        self.email_input.setFocus()
    
    def toggle_password_visibility(self):
        """Toggle password field visibility."""
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_password_btn.setIcon(QIcon("resources/icons/eye-slash.png"))
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_password_btn.setIcon(QIcon("resources/icons/eye.png"))
    
    def validate_email(self, email: str) -> bool:
        """
        Validate email format with improved visual feedback.
        
        Args:
            email: Email address to validate
            
        Returns:
            bool: True if email is valid
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        is_valid = bool(re.match(pattern, email))
        
        if not email:
            self.validation_indicator.clear()
            self.status_bar.clearMessage()
        elif is_valid:
            self.validation_indicator.setPixmap(QIcon("resources/icons/check.png").pixmap(16, 16))
            self.status_bar.clearMessage()
            
            # Auto-detect provider and suggest quick setup
            provider = EmailProviders.detect_provider(email)
            if provider != Provider.CUSTOM:
                self.status_bar.showMessage(
                    f"Tip: Click the {provider.value} button above for automatic setup",
                    5000
                )
        else:
            self.validation_indicator.setPixmap(QIcon("resources/icons/error.png").pixmap(16, 16))
            self.status_bar.showMessage("Invalid email format", 3000)
        
        return is_valid
    
    @handle_errors
    def quick_setup_with_domain(self, provider: Provider):
        """
        Configure settings for a specific provider with domain handling.
        
        Args:
            provider (Provider): Email provider to configure
        """
        logger.debug(f"Starting quick setup for provider: {provider.value}")
        
        # Get provider configuration
        config = EmailProviders.get_provider_config(provider)
        if not config:
            logger.error(f"No configuration found for provider: {provider.value}")
            return
        
        # Get username for email address
        username, ok = QInputDialog.getText(
            self,
            f"Enter {provider.value} Username",
            f"Enter your {provider.value} username (without @{config.domain}):"
        )
        
        if not ok or not username:
            return
        
        # Construct email address
        email = f"{username}@{config.domain}"
        if not self.validate_email(email):
            QMessageBox.warning(
                self,
                "Invalid Username",
                "Please enter a valid username without special characters."
            )
            return
        
        # Set email in input field
        self.email_input.setText(email)
        
        # Configure server settings
        self.imap_server.setText(config.imap_server)
        self.imap_port.setValue(config.imap_port)
        self.imap_ssl.setChecked(config.imap_ssl)
        self.smtp_server.setText(config.smtp_server)
        self.smtp_port.setValue(config.smtp_port)
        self.smtp_ssl.setChecked(config.smtp_ssl)
        
        logger.debug("Server settings configured")
        
        # Handle OAuth for Gmail
        if provider == Provider.GMAIL:
            try:
                logger.debug("Starting Gmail OAuth flow")
                # Hide password field for OAuth
                self.password_label.hide()
                self.password_input.hide()
                
                # Start OAuth flow
                tokens = EmailProviders.authenticate_oauth(email, provider)
                if tokens and 'access_token' in tokens:
                    logger.debug("OAuth authentication successful, storing tokens")
                    
                    # Verify email if available from userinfo
                    if 'email' in tokens and tokens.get('email_verified', False):
                        email = tokens['email']
                        self.email_input.setText(email)
                    
                    # Store the tokens
                    self.credential_service.store_oauth_tokens(email, tokens)
                    
                    # Save account data and close dialog
                    self.account_data = {
                        'email': email,
                        'imap_server': self.imap_server.text(),
                        'imap_port': self.imap_port.value(),
                        'imap_ssl': self.imap_ssl.isChecked(),
                        'smtp_server': self.smtp_server.text(),
                        'smtp_port': self.smtp_port.value(),
                        'smtp_ssl': self.smtp_ssl.isChecked(),
                        'provider': provider.value,
                        'oauth_tokens': tokens
                    }
                    logger.debug(f"Account data prepared: {self.account_data}")
                    
                    QMessageBox.information(
                        self,
                        "Authentication Successful",
                        f"Gmail account {email} authenticated successfully!"
                    )
                    
                    logger.debug("Accepting dialog to save account")
                    self.accept()
                else:
                    logger.error("Invalid OAuth tokens received")
                    QMessageBox.warning(
                        self,
                        "Authentication Failed",
                        "Failed to authenticate Gmail account. Please try again."
                    )
            except Exception as e:
                logger.error(f"Gmail OAuth error: {str(e)}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Authentication Failed",
                    f"Failed to authenticate Gmail account: {str(e)}\n\n"
                    "Please make sure you have:\n"
                    "1. Enabled IMAP in Gmail settings\n"
                    "2. Allowed less secure app access or using 2FA\n"
                    "3. Valid internet connection"
                )
                return
        else:
            # For non-OAuth providers, show password field
            self.password_label.show()
            self.password_input.show()
            
            # Open provider setup in browser
            EmailProviders.open_provider_setup(provider, email)
            
            # Show app password instructions if available
            if config.app_password_url:
                reply = QMessageBox.question(
                    self,
                    "App Password Required",
                    "This provider requires an app password for secure access.\n\n"
                    "Would you like to set up an app password now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    EmailProviders.open_app_password_setup(provider)
    
    @handle_errors
    def test_connection(self):
        """Test the email account connection with visual feedback."""
        email = self.email_input.text()
        if not self.validate_email(email):
            self.status_bar.showMessage("Please enter a valid email address", 3000)
            return
        
        # Show testing status
        self.status_bar.showMessage("Testing connection...", 0)
        self.test_btn.setEnabled(False)
        QApplication.processEvents()  # Ensure UI updates
        
        try:
            # Test IMAP connection
            imap_host = self.imap_server.text()
            imap_port = self.imap_port.value()
            use_ssl = self.imap_ssl.isChecked()
            
            if use_ssl:
                imap = imaplib.IMAP4_SSL(imap_host, imap_port)
            else:
                imap = imaplib.IMAP4(imap_host, imap_port)
            
            # Try to login if password is provided
            if self.password_input.text():
                imap.login(email, self.password_input.text())
            
            imap.logout()
            
            # Test SMTP connection
            smtp_host = self.smtp_server.text()
            smtp_port = self.smtp_port.value()
            
            if use_ssl:
                smtp = smtplib.SMTP_SSL(smtp_host, smtp_port)
            else:
                smtp = smtplib.SMTP(smtp_host, smtp_port)
                smtp.starttls()
            
            # Try to login if password is provided
            if self.password_input.text():
                smtp.login(email, self.password_input.text())
            
            smtp.quit()
            
            # Show success message
            self.status_bar.showMessage("Connection test successful!", 5000)
            QMessageBox.information(
                self,
                "Connection Test",
                "Successfully connected to both IMAP and SMTP servers!"
            )
            
        except (imaplib.IMAP4.error, ssl.SSLError) as e:
            error_msg = str(e)
            if "AUTHENTICATIONFAILED" in error_msg:
                self.status_bar.showMessage("Authentication failed - check your password", 5000)
                QMessageBox.warning(
                    self,
                    "IMAP Authentication Failed",
                    "Failed to authenticate with the IMAP server.\n\n"
                    "If you're using Gmail, Outlook, or Yahoo, make sure to:\n"
                    "1. Use an app password instead of your regular password\n"
                    "2. Enable IMAP access in your email settings\n"
                    "3. Allow less secure app access if required"
                )
            else:
                self.status_bar.showMessage("IMAP connection failed", 5000)
                QMessageBox.critical(
                    self,
                    "IMAP Connection Failed",
                    f"Failed to connect to IMAP server: {error_msg}\n\n"
                    "Please check:\n"
                    "1. Server address and port are correct\n"
                    "2. SSL/TLS settings are correct\n"
                    "3. Your internet connection is working"
                )
        except smtplib.SMTPAuthenticationError as e:
            self.status_bar.showMessage("SMTP authentication failed", 5000)
            QMessageBox.warning(
                self,
                "SMTP Authentication Failed",
                "Failed to authenticate with the SMTP server.\n\n"
                "If you're using Gmail, Outlook, or Yahoo, make sure to:\n"
                "1. Use an app password instead of your regular password\n"
                "2. Enable SMTP access in your email settings\n"
                "3. Allow less secure app access if required"
            )
        except (smtplib.SMTPException, ssl.SSLError) as e:
            self.status_bar.showMessage("SMTP connection failed", 5000)
            QMessageBox.critical(
                self,
                "SMTP Connection Failed",
                f"Failed to connect to SMTP server: {str(e)}\n\n"
                "Please check:\n"
                "1. Server address and port are correct\n"
                "2. SSL/TLS settings are correct\n"
                "3. Your internet connection is working"
            )
        except Exception as e:
            self.status_bar.showMessage("Connection test failed", 5000)
            QMessageBox.critical(
                self,
                "Connection Test Failed",
                f"An unexpected error occurred: {str(e)}"
            )
        finally:
            self.test_btn.setEnabled(True)
    
    def load_account_data(self, account_data: dict):
        """Load existing account data into the form."""
        self.email_input.setText(account_data.get('email', ''))
        self.imap_server.setText(account_data.get('imap_server', ''))
        self.imap_port.setValue(account_data.get('imap_port', 993))
        self.imap_ssl.setChecked(account_data.get('imap_ssl', True))
        self.smtp_server.setText(account_data.get('smtp_server', ''))
        self.smtp_port.setValue(account_data.get('smtp_port', 587))
        self.smtp_ssl.setChecked(account_data.get('smtp_ssl', True))
    
    def accept(self):
        """Handle dialog acceptance and save account data."""
        email = self.email_input.text()
        logger.logger.debug(f"Dialog accept called for email: {email}")
        
        provider = EmailProviders.detect_provider(email) if email else Provider.CUSTOM
        logger.logger.debug(f"Detected provider: {provider.value}")
        
        # For manual setup, email is required
        if not self.account_data:  # If not already set by quick setup
            if not email:
                logger.logger.warning("No email address provided for manual setup")
                QMessageBox.warning(self, "Validation Error", "Email address is required for manual setup.")
                return
            
            if provider == Provider.GMAIL:
                # Check for OAuth tokens
                tokens = self.credential_service.get_oauth_tokens(email)
                if not tokens:
                    logger.logger.warning(f"No OAuth tokens found for {email}")
                    QMessageBox.warning(
                        self,
                        "Authentication Required",
                        "Please authenticate your Gmail account using the Gmail Setup button."
                    )
                    return
                logger.logger.debug("OAuth tokens verified")
            else:
                # Check for password
                if not self.password_input.text():
                    logger.logger.warning("No password provided for non-OAuth account")
                    QMessageBox.warning(self, "Validation Error", "Password is required.")
                    return
                
                # Store password securely
                logger.logger.debug("Storing password securely")
                self.credential_service.store_email_credentials(
                    email,
                    {'password': self.password_input.text()}
                )
            
            # Save account data
            self.account_data = {
                'email': email,
                'imap_server': self.imap_server.text(),
                'imap_port': self.imap_port.value(),
                'imap_ssl': self.imap_ssl.isChecked(),
                'smtp_server': self.smtp_server.text(),
                'smtp_port': self.smtp_port.value(),
                'smtp_ssl': self.smtp_ssl.isChecked()
            }
            logger.logger.debug(f"Final account data prepared: {self.account_data}")
        
        logger.logger.debug("Calling parent accept()")
        super().accept() 