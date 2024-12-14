from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                           QPushButton, QSpinBox, QCheckBox, QMessageBox,
                           QHBoxLayout, QLabel)
from PyQt6.QtCore import Qt
from email_providers import EmailProviders, Provider
from security.credential_manager import CredentialManager
from utils.logger import logger
from utils.error_handler import handle_errors

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
        self.credential_manager = CredentialManager()
        self.setup_ui()
        
        if account_data:
            self.load_account_data(account_data)
    
    def setup_ui(self):
        """Set up the dialog UI components."""
        self.setWindowTitle("Email Account Settings")
        layout = QVBoxLayout(self)
        
        # Create form layout for inputs
        form = QFormLayout()
        
        # Email input
        self.email_input = QLineEdit()
        self.email_input.textChanged.connect(self.on_email_changed)
        form.addRow("Email:", self.email_input)
        
        # Quick setup buttons for providers
        provider_layout = QHBoxLayout()
        
        gmail_btn = QPushButton("Gmail Setup")
        gmail_btn.clicked.connect(lambda: self.quick_setup(Provider.GMAIL))
        provider_layout.addWidget(gmail_btn)
        
        outlook_btn = QPushButton("Outlook Setup")
        outlook_btn.clicked.connect(lambda: self.quick_setup(Provider.OUTLOOK))
        provider_layout.addWidget(outlook_btn)
        
        yahoo_btn = QPushButton("Yahoo Setup")
        yahoo_btn.clicked.connect(lambda: self.quick_setup(Provider.YAHOO))
        provider_layout.addWidget(yahoo_btn)
        
        form.addRow("Quick Setup:", provider_layout)
        
        # Server settings
        self.imap_server = QLineEdit()
        form.addRow("IMAP Server:", self.imap_server)
        
        self.imap_port = QSpinBox()
        self.imap_port.setRange(1, 65535)
        self.imap_port.setValue(993)
        form.addRow("IMAP Port:", self.imap_port)
        
        self.imap_ssl = QCheckBox("Use SSL")
        self.imap_ssl.setChecked(True)
        form.addRow("", self.imap_ssl)
        
        self.smtp_server = QLineEdit()
        form.addRow("SMTP Server:", self.smtp_server)
        
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(587)
        form.addRow("SMTP Port:", self.smtp_port)
        
        self.smtp_ssl = QCheckBox("Use SSL")
        self.smtp_ssl.setChecked(True)
        form.addRow("", self.smtp_ssl)
        
        # Password field (hidden for OAuth providers)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_label = QLabel("Password:")
        form.addRow(self.password_label, self.password_input)
        
        layout.addLayout(form)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_btn)
        
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    @handle_errors
    def quick_setup(self, provider: Provider):
        """
        Configure settings for a specific provider.
        
        Args:
            provider (Provider): Email provider to configure
        """
        logger.logger.debug(f"Starting quick setup for provider: {provider.value}")
        
        config = EmailProviders.get_provider_config(provider)
        if not config:
            logger.logger.error(f"No configuration found for provider: {provider.value}")
            return
        
        logger.logger.debug(f"Provider config loaded: {config.name}")
        
        # Set server settings
        self.imap_server.setText(config.imap_server)
        self.imap_port.setValue(config.imap_port)
        self.imap_ssl.setChecked(config.imap_ssl)
        self.smtp_server.setText(config.smtp_server)
        self.smtp_port.setValue(config.smtp_port)
        self.smtp_ssl.setChecked(config.smtp_ssl)
        
        logger.logger.debug("Server settings configured")
        
        # Handle OAuth for Gmail
        if provider == Provider.GMAIL:
            try:
                logger.logger.debug("Starting Gmail OAuth flow")
                # Hide password field for OAuth
                self.password_label.hide()
                self.password_input.hide()
                
                # Start OAuth flow - email will be obtained during authentication
                tokens = EmailProviders.authenticate_gmail()
                if tokens and 'email' in tokens:
                    email = tokens['email']
                    self.email_input.setText(email)  # Set the email from OAuth response
                    
                    logger.logger.debug("OAuth authentication successful, storing tokens")
                    QMessageBox.information(
                        self,
                        "Authentication Successful",
                        f"Gmail account {email} authenticated successfully!"
                    )
                    # Store the tokens
                    self.credential_manager.store_oauth_tokens(email, tokens)
                    
                    # Save account data and close dialog
                    self.account_data = {
                        'email': email,
                        'imap_server': self.imap_server.text(),
                        'imap_port': self.imap_port.value(),
                        'imap_ssl': self.imap_ssl.isChecked(),
                        'smtp_server': self.smtp_server.text(),
                        'smtp_port': self.smtp_port.value(),
                        'smtp_ssl': self.smtp_ssl.isChecked()
                    }
                    logger.logger.debug(f"Account data prepared: {self.account_data}")
                    logger.logger.debug("Accepting dialog to save account")
                    self.accept()
                else:
                    logger.logger.error("No tokens or email received from OAuth authentication")
                    QMessageBox.warning(
                        self,
                        "Authentication Failed",
                        "Failed to authenticate Gmail account. Please try again."
                    )
            except Exception as e:
                logger.logger.error(f"Gmail OAuth error: {str(e)}", exc_info=True)
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
            # For non-OAuth providers, we need an email address
            email = self.email_input.text()
            if not email:
                QMessageBox.warning(
                    self,
                    "Email Required",
                    f"Please enter your {provider.value} email address first."
                )
                self.email_input.setFocus()
                return
            
            # Show password field for non-OAuth providers
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
    
    def on_email_changed(self, email):
        """
        Handle email input changes and auto-configure if possible.
        
        Args:
            email (str): Current email input
        """
        if not email:
            return
        
        # Try to detect provider and auto-configure
        provider = EmailProviders.detect_provider(email)
        if provider != Provider.CUSTOM:
            config = EmailProviders.get_provider_config(provider)
            if config:
                self.imap_server.setText(config.imap_server)
                self.imap_port.setValue(config.imap_port)
                self.imap_ssl.setChecked(config.imap_ssl)
                self.smtp_server.setText(config.smtp_server)
                self.smtp_port.setValue(config.smtp_port)
                self.smtp_ssl.setChecked(config.smtp_ssl)
                
                # Handle OAuth visibility
                if provider == Provider.GMAIL:
                    self.password_label.hide()
                    self.password_input.hide()
                else:
                    self.password_label.show()
                    self.password_input.show()
    
    def load_account_data(self, account_data):
        """
        Load existing account data into the form.
        
        Args:
            account_data (dict): Account configuration data
        """
        self.email_input.setText(account_data['email'])
        self.imap_server.setText(account_data['imap_server'])
        self.imap_port.setValue(account_data['imap_port'])
        self.imap_ssl.setChecked(account_data['imap_ssl'])
        self.smtp_server.setText(account_data['smtp_server'])
        self.smtp_port.setValue(account_data['smtp_port'])
        self.smtp_ssl.setChecked(account_data['smtp_ssl'])
        
        # Handle OAuth vs password
        provider = EmailProviders.detect_provider(account_data['email'])
        if provider == Provider.GMAIL:
            self.password_label.hide()
            self.password_input.hide()
            
            # Check if we need to re-authenticate
            tokens = self.credential_manager.get_oauth_tokens(account_data['email'])
            if not tokens:
                reply = QMessageBox.question(
                    self,
                    "Re-authentication Required",
                    "Your Gmail account needs to be re-authenticated.\n\n"
                    "Would you like to authenticate now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.quick_setup(Provider.GMAIL)
        else:
            credentials = self.credential_manager.get_email_credentials(account_data['email'])
            if credentials and 'password' in credentials:
                self.password_input.setText(credentials['password'])
    
    @handle_errors
    def test_connection(self):
        """Test the email account connection with current settings."""
        # TODO: Implement connection testing
        pass
    
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
                tokens = self.credential_manager.get_oauth_tokens(email)
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
                self.credential_manager.store_email_credentials(
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