    def __init__(self):
        super().__init__()
        try:
            # Initialize services
            self.notification_service = NotificationService()
            self.credential_service = CredentialService()
            self.operation_service = EmailOperationService(self.notification_service)
            self.account_manager = AccountManager(self.credential_service)
            self.email_manager = EmailManager(self.credential_service, self.operation_service)
            self.current_account = None
            self.current_folder = "INBOX"  # Default folder
            
            # Set up UI
            self.setup_ui()
            
            # Load accounts after UI setup
            self.load_accounts()
            
            # Create test account if no accounts exist
            if not self.account_manager.get_all_accounts():
                self.create_test_account()
            
            # Set up auto-refresh timer
            self.refresh_timer = QTimer(self)
            self.refresh_timer.timeout.connect(self.refresh_emails)
            self.refresh_timer.start(300000)  # Refresh every 5 minutes
            
        except Exception as e:
            logger.critical(f"Failed to initialize main window: {str(e)}")
            QMessageBox.critical(
                self,
                "Initialization Error",
                f"Failed to initialize application: {str(e)}\n\nPlease restart the application."
            )
            raise
    
    def create_test_account(self):
        """Create a test account for development."""
        try:
            # Show dialog to get test account credentials
            dialog = QDialog(self)
            dialog.setWindowTitle("Add Test Email Account")
            dialog.setMinimumWidth(400)
            
            layout = QVBoxLayout(dialog)
            
            # Email input
            email_label = QLabel("Email:")
            email_input = QLineEdit()
            layout.addWidget(email_label)
            layout.addWidget(email_input)
            
            # Password input
            password_label = QLabel("Password/App Password:")
            password_input = QLineEdit()
            password_input.setEchoMode(QLineEdit.EchoMode.Password)
            layout.addWidget(password_label)
            layout.addWidget(password_input)
            
            # Buttons
            button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | 
                QDialogButtonBox.StandardButton.Cancel
            )
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                email = email_input.text()
                password = password_input.text()
                
                if not email or not password:
                    raise ValueError("Email and password are required")
                
                # Detect provider
                provider = EmailProviders.detect_provider(email)
                if not provider:
                    raise ValueError("Unsupported email provider")
                
                # Create account configuration
                account_data = {
                    'email': email,
                    'imap_server': provider.imap_server,
                    'imap_port': provider.imap_port,
                    'imap_ssl': provider.imap_ssl,
                    'smtp_server': provider.smtp_server,
                    'smtp_port': provider.smtp_port,
                    'smtp_ssl': provider.smtp_ssl
                }
                
                # Add account
                if not self.account_manager.add_account(account_data):
                    raise Exception("Failed to add account")
                
                # Store credentials
                credentials = {
                    'type': 'password',
                    'password': password
                }
                if not self.credential_service.store_email_credentials(email, credentials):
                    raise Exception("Failed to store credentials")
                
                # Reload accounts
                self.load_accounts()
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Success",
                    "Test account added successfully!"
                )
                
        except Exception as e:
            logger.error(f"Error creating test account: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create test account: {str(e)}"
            ) 