from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                           QPushButton, QSpinBox, QCheckBox, QMessageBox,
                           QHBoxLayout, QLabel, QInputDialog, QGroupBox,
                           QStatusBar, QButtonGroup, QRadioButton, QDialogButtonBox,
                           QApplication, QFrame, QWidget)
from PyQt6.QtCore import Qt, QSize
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
        """Initialize dialog."""
        super().__init__(parent)
        self.credential_service = CredentialService()
        self.account_manager = AccountManager(self.credential_service)
        self.account_data = account_data
        
        # Set dark theme for the entire dialog
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                border-radius: 10px;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                color: #e0e0e0;
                font-weight: bold;
                border: 2px solid #2d5a7c;
                border-radius: 12px;
                margin-top: 1.5ex;
                padding: 15px;
                background-color: #252525;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 15px;
                color: #e0e0e0;
                font-size: 15px;
                font-weight: bold;
            }
            QLineEdit, QSpinBox {
                background-color: #333333;
                color: #e0e0e0;
                border: 2px solid #2d5a7c;
                border-radius: 8px;
                padding: 10px;
                min-height: 24px;
                font-size: 13px;
            }
            QLineEdit:focus, QSpinBox:focus {
                border-color: #3498db;
                background-color: #383838;
            }
            QLineEdit:hover, QSpinBox:hover {
                background-color: #383838;
            }
            QPushButton {
                background-color: #2d5a7c;
                color: #e0e0e0;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-weight: bold;
                font-size: 13px;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
            QPushButton:pressed {
                background-color: #2980b9;
            }
            QCheckBox {
                color: #e0e0e0;
                spacing: 8px;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #2d5a7c;
                border-radius: 6px;
                background-color: #333333;
            }
            QCheckBox::indicator:hover {
                background-color: #383838;
            }
            QCheckBox::indicator:checked {
                background-color: #3498db;
                image: url(resources/icons/check.png);
            }
            QStatusBar {
                color: #e0e0e0;
                border-top: 1px solid #2d5a7c;
                background-color: #252525;
                padding: 8px;
                font-size: 13px;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #252525;
                width: 12px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #2d5a7c;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #3498db;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        self.setup_ui()
        
        if account_data:
            self.load_account_data(account_data)
    
    def setup_ui(self):
        """Set up the dialog UI components."""
        self.setWindowTitle("Add Email Account")
        layout = QVBoxLayout(self)
        layout.setSpacing(25)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Welcome message
        welcome_label = QLabel("Choose your email provider")
        welcome_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #e0e0e0;
            margin: 10px;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome_label)
        
        # Provider buttons
        provider_layout = QHBoxLayout()
        provider_layout.setSpacing(25)
        
        # Common button style for provider buttons
        provider_button_style = """
            QPushButton {
                min-width: 180px;
                min-height: 160px;
                font-size: 18px;
                border: 2px solid #2d5a7c;
                border-radius: 15px;
                background-color: #252525;
                color: #e0e0e0;
                text-align: center;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton:hover {
                background-color: #2d5a7c;
                border-color: #3498db;
            }
            QPushButton:pressed {
                background-color: #3498db;
            }
        """
        
        # Gmail button with OAuth
        gmail_layout = QVBoxLayout()
        gmail_btn = QPushButton("\n\n\nGmail")
        gmail_btn.setIcon(QIcon("resources/icons/gmail.png"))
        gmail_btn.setIconSize(QSize(72, 72))
        gmail_btn.setStyleSheet(provider_button_style)
        gmail_btn.clicked.connect(lambda: self.set_provider(EmailProviders.GMAIL))
        gmail_layout.addWidget(gmail_btn)
        
        gmail_oauth_btn = QPushButton("Sign in with Google")
        gmail_oauth_btn.setStyleSheet("""
            QPushButton {
                background-color: #4285f4;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2b62a5;
            }
        """)
        gmail_oauth_btn.clicked.connect(lambda: self.start_oauth(EmailProviders.GMAIL))
        gmail_layout.addWidget(gmail_oauth_btn)
        provider_layout.addLayout(gmail_layout)
        
        # Outlook button with OAuth
        outlook_layout = QVBoxLayout()
        outlook_btn = QPushButton("\n\n\nOutlook")
        outlook_btn.setIcon(QIcon("resources/icons/outlook.png"))
        outlook_btn.setIconSize(QSize(72, 72))
        outlook_btn.setStyleSheet(provider_button_style)
        outlook_btn.clicked.connect(lambda: self.set_provider(EmailProviders.OUTLOOK))
        outlook_layout.addWidget(outlook_btn)
        
        outlook_oauth_btn = QPushButton("Sign in with Microsoft")
        outlook_oauth_btn.setStyleSheet("""
            QPushButton {
                background-color: #00a4ef;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton:hover {
                background-color: #0078d4;
            }
            QPushButton:pressed {
                background-color: #006abc;
            }
        """)
        outlook_oauth_btn.clicked.connect(lambda: self.start_oauth(EmailProviders.OUTLOOK))
        outlook_layout.addWidget(outlook_oauth_btn)
        provider_layout.addLayout(outlook_layout)
        
        # Yahoo button (no OAuth)
        yahoo_layout = QVBoxLayout()
        yahoo_btn = QPushButton("\n\n\nYahoo")
        yahoo_btn.setIcon(QIcon("resources/icons/yahoo.png"))
        yahoo_btn.setIconSize(QSize(72, 72))
        yahoo_btn.setStyleSheet(provider_button_style)
        yahoo_btn.clicked.connect(lambda: self.set_provider(EmailProviders.YAHOO))
        yahoo_layout.addWidget(yahoo_btn)
        yahoo_layout.addSpacing(52)  # Add spacing to align with other buttons
        provider_layout.addLayout(yahoo_layout)
        
        layout.addLayout(provider_layout)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #2d5a7c; margin: 20px 0;")
        layout.addWidget(line)
        
        # Account details group
        details_group = QGroupBox("Account Details")
        details_layout = QFormLayout()
        details_layout.setSpacing(20)
        details_layout.setContentsMargins(25, 35, 25, 25)
        
        # Email field with icon
        email_layout = QHBoxLayout()
        email_icon = QLabel()
        email_icon.setPixmap(QIcon("resources/icons/email.png").pixmap(QSize(24, 24)))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@gmail.com")
        self.email_input.setMinimumWidth(400)
        email_layout.addWidget(email_icon)
        email_layout.addWidget(self.email_input)
        details_layout.addRow("Email:", email_layout)
        
        # Password field with icon and show/hide button
        password_layout = QHBoxLayout()
        password_icon = QLabel()
        password_icon.setPixmap(QIcon("resources/icons/password.png").pixmap(QSize(24, 24)))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumWidth(400)
        
        show_password_btn = QPushButton()
        show_password_btn.setIcon(QIcon("resources/icons/eye.png"))
        show_password_btn.setCheckable(True)
        show_password_btn.setFixedSize(44, 44)
        show_password_btn.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 8px;
                padding: 8px;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: #383838;
            }
            QPushButton:checked {
                background-color: #2d5a7c;
            }
        """)
        show_password_btn.clicked.connect(lambda checked: self.password_input.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        ))
        
        password_layout.addWidget(password_icon)
        password_layout.addWidget(self.password_input)
        password_layout.addWidget(show_password_btn)
        details_layout.addRow("Password:", password_layout)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Server settings group
        server_group = QGroupBox("Server Settings (Advanced)")
        server_layout = QFormLayout()
        server_layout.setSpacing(20)
        server_layout.setContentsMargins(25, 35, 25, 25)
        
        # IMAP settings with icon
        imap_layout = QHBoxLayout()
        imap_icon = QLabel()
        imap_icon.setPixmap(QIcon("resources/icons/server.png").pixmap(QSize(24, 24)))
        self.imap_server = QLineEdit()
        self.imap_server.setMinimumWidth(250)
        
        self.imap_port = QSpinBox()
        self.imap_port.setRange(1, 65535)
        self.imap_port.setValue(993)
        self.imap_port.setFixedWidth(100)
        
        self.imap_ssl = QCheckBox("Use SSL")
        self.imap_ssl.setChecked(True)
        
        imap_layout.addWidget(imap_icon)
        imap_layout.addWidget(self.imap_server)
        imap_layout.addWidget(QLabel("Port:"))
        imap_layout.addWidget(self.imap_port)
        imap_layout.addWidget(self.imap_ssl)
        server_layout.addRow("IMAP Server:", imap_layout)
        
        # SMTP settings with icon
        smtp_layout = QHBoxLayout()
        smtp_icon = QLabel()
        smtp_icon.setPixmap(QIcon("resources/icons/server.png").pixmap(QSize(24, 24)))
        self.smtp_server = QLineEdit()
        self.smtp_server.setMinimumWidth(250)
        
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(587)
        self.smtp_port.setFixedWidth(100)
        
        self.smtp_ssl = QCheckBox("Use SSL/TLS")
        self.smtp_ssl.setChecked(True)
        
        smtp_layout.addWidget(smtp_icon)
        smtp_layout.addWidget(self.smtp_server)
        smtp_layout.addWidget(QLabel("Port:"))
        smtp_layout.addWidget(self.smtp_port)
        smtp_layout.addWidget(self.smtp_ssl)
        server_layout.addRow("SMTP Server:", smtp_layout)
        
        server_group.setLayout(server_layout)
        layout.addWidget(server_group)
        
        # Test connection button
        test_btn = QPushButton("Test Connection")
        test_btn.setIcon(QIcon("resources/icons/test.png"))
        test_btn.setStyleSheet("""
            QPushButton {
                padding: 15px 30px;
                font-size: 15px;
                background-color: #2d5a7c;
                margin: 15px 0;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
            QPushButton:pressed {
                background-color: #2980b9;
            }
        """)
        test_btn.clicked.connect(self.test_connection)
        layout.addWidget(test_btn)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.setStyleSheet("""
            QPushButton {
                min-width: 120px;
                padding: 12px 24px;
                font-size: 14px;
            }
            QPushButton[text="OK"] {
                background-color: #3498db;
            }
            QPushButton[text="OK"]:hover {
                background-color: #2980b9;
            }
            QPushButton[text="OK"]:pressed {
                background-color: #2472a4;
            }
            QPushButton[text="Cancel"] {
                background-color: #2d5a7c;
            }
            QPushButton[text="Cancel"]:hover {
                background-color: #34495e;
            }
            QPushButton[text="Cancel"]:pressed {
                background-color: #2c3e50;
            }
        """)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #252525;
                color: #e0e0e0;
                border-top: 1px solid #2d5a7c;
                padding: 8px;
                font-size: 13px;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)
        layout.addWidget(self.status_bar)
        
        self.setMinimumWidth(800)
        self.setMinimumHeight(900)
        
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
    
    def set_provider(self, provider: Provider):
        """Set email provider and server settings."""
        if not provider:
            return
            
        # Set server settings
        self.imap_server.setText(provider.imap_server)
        self.imap_port.setValue(provider.imap_port)
        self.imap_ssl.setChecked(provider.imap_ssl)
        
        self.smtp_server.setText(provider.smtp_server)
        self.smtp_port.setValue(provider.smtp_port)
        self.smtp_ssl.setChecked(provider.smtp_ssl)
        
        # Set email domain hint
        if provider == EmailProviders.GMAIL:
            self.email_input.setPlaceholderText("your.name@gmail.com")
        elif provider == EmailProviders.OUTLOOK:
            self.email_input.setPlaceholderText("your.name@outlook.com")
        elif provider == EmailProviders.YAHOO:
            self.email_input.setPlaceholderText("your.name@yahoo.com")
        
        # Show provider-specific help
        if provider == EmailProviders.GMAIL:
            self.status_bar.showMessage("For Gmail, you need to use an App Password. Go to Google Account settings to generate one.")
        elif provider == EmailProviders.OUTLOOK:
            self.status_bar.showMessage("For Outlook, use your Microsoft account email and password.")
        elif provider == EmailProviders.YAHOO:
            self.status_bar.showMessage("For Yahoo Mail, you may need to generate an App Password in account security settings.")
    
    def start_oauth(self, provider: Provider):
        """Start OAuth authentication flow."""
        try:
            self.status_bar.showMessage(f"Starting {provider.name} OAuth authentication...")
            QApplication.processEvents()
            
            # Get OAuth credentials
            credentials = self.credential_service.start_oauth_flow(provider)
            if not credentials:
                raise Exception("OAuth authentication failed")
            
            # Set email from OAuth response
            email = credentials.get('email')
            if not email:
                raise Exception("Could not get email from OAuth response")
            
            self.email_input.setText(email)
            self.set_provider(provider)
            
            # Store credentials
            if not self.credential_service.store_email_credentials(email, credentials):
                raise Exception("Failed to store OAuth credentials")
            
            # Store account data
            account_data = self.get_account_data()
            self.account_manager.add_account(account_data)
            
            self.status_bar.showMessage("OAuth authentication successful!")
            QMessageBox.information(
                self,
                "Success",
                f"Successfully authenticated with {provider.name}!"
            )
            
            super().accept()
            
        except Exception as e:
            logger.error(f"OAuth error: {str(e)}")
            self.status_bar.showMessage(f"OAuth error: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"OAuth authentication failed: {str(e)}"
            )