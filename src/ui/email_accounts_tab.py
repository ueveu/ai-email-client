from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                           QLabel, QScrollArea, QFrame, QMessageBox)
from PyQt6.QtCore import Qt
from config import Config
from ui.email_account_dialog import EmailAccountDialog
from resources import Resources

class EmailAccountsTab(QWidget):
    """Tab for managing email accounts."""
    
    def __init__(self):
        """Initialize the email accounts tab."""
        super().__init__()
        
        self.config = Config()
        if "accounts" not in self.config.settings:
            self.config.settings["accounts"] = []
            self.config._save_settings(self.config.settings)
            
        self.setup_ui()
        self.refresh_accounts()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Header section
        header_layout = QHBoxLayout()
        header_label = QLabel("Email Accounts")
        header_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 10px;
        """)
        header_layout.addWidget(header_label)
        
        # Add account button
        add_button = QPushButton("Add Account")
        add_button.setStyleSheet("""
            QPushButton {
                background-color: #4285f4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3367d6;
            }
        """)
        add_button.clicked.connect(self.add_account)
        header_layout.addStretch()
        header_layout.addWidget(add_button)
        
        layout.addLayout(header_layout)
        
        # Scroll area for accounts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.accounts_widget = QWidget()
        self.accounts_layout = QVBoxLayout(self.accounts_widget)
        self.accounts_layout.setContentsMargins(0, 0, 0, 0)
        self.accounts_layout.setSpacing(10)
        
        scroll.setWidget(self.accounts_widget)
        layout.addWidget(scroll)
        
        # Add stretch to push everything to the top
        layout.addStretch()
    
    def refresh_accounts(self):
        """Refresh the list of email accounts."""
        # Clear existing account widgets
        while self.accounts_layout.count():
            child = self.accounts_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Add account widgets
        accounts = self.config.settings.get("accounts", [])
        if not accounts:
            # Show empty state
            empty_label = QLabel(
                "No email accounts configured yet.\n"
                "Click 'Add Account' to get started."
            )
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("""
                color: #666;
                font-size: 14px;
                margin: 20px;
            """)
            self.accounts_layout.addWidget(empty_label)
        else:
            for account in accounts:
                self.add_account_widget(account)
    
    def add_account_widget(self, account):
        """Add a widget for an email account."""
        account_frame = QFrame()
        account_frame.setFrameShape(QFrame.Shape.StyledPanel)
        account_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        
        layout = QHBoxLayout(account_frame)
        
        # Account info
        info_layout = QVBoxLayout()
        
        # Email and name
        email_label = QLabel(f"{account['name']} <{account['email']}>")
        email_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        info_layout.addWidget(email_label)
        
        # Server info
        server_info = []
        if account.get('imap_server'):
            server_info.append(f"IMAP: {account['imap_server']}:{account['imap_port']}")
        if account.get('smtp_server'):
            server_info.append(f"SMTP: {account['smtp_server']}:{account['smtp_port']}")
        
        server_label = QLabel(" | ".join(server_info))
        server_label.setStyleSheet("color: #aaa; font-size: 12px;")
        info_layout.addWidget(server_label)
        
        layout.addLayout(info_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(lambda: self.edit_account(account))
        edit_button.setStyleSheet("""
            QPushButton {
                background-color: #fbbc05;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #f9ab00;
            }
        """)
        button_layout.addWidget(edit_button)
        
        remove_button = QPushButton("Remove")
        remove_button.clicked.connect(lambda: self.remove_account(account))
        remove_button.setStyleSheet("""
            QPushButton {
                background-color: #ea4335;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d33828;
            }
        """)
        button_layout.addWidget(remove_button)
        
        layout.addLayout(button_layout)
        self.accounts_layout.addWidget(account_frame)
    
    def add_account(self):
        """Show dialog to add a new email account."""
        dialog = EmailAccountDialog(self)
        if dialog.exec() == EmailAccountDialog.DialogCode.Accepted:
            account_data = dialog.get_account_data()
            
            # Add account to config
            accounts = self.config.settings.get("accounts", [])
            accounts.append(account_data)
            self.config.settings["accounts"] = accounts
            self.config._save_settings(self.config.settings)
            
            self.refresh_accounts()
    
    def edit_account(self, account):
        """Show dialog to edit an existing email account."""
        dialog = EmailAccountDialog(self, account)
        if dialog.exec() == EmailAccountDialog.DialogCode.Accepted:
            account_data = dialog.get_account_data()
            
            # Update account in config
            accounts = self.config.settings.get("accounts", [])
            for i, acc in enumerate(accounts):
                if acc["email"] == account["email"]:
                    accounts[i] = account_data
                    break
                    
            self.config.settings["accounts"] = accounts
            self.config._save_settings(self.config.settings)
            
            self.refresh_accounts()
    
    def remove_account(self, account):
        """Remove an email account."""
        reply = QMessageBox.question(
            self,
            "Remove Account",
            f"Are you sure you want to remove the account {account['email']}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Remove account from config
            accounts = self.config.settings.get("accounts", [])
            accounts = [acc for acc in accounts if acc["email"] != account["email"]]
            self.config.settings["accounts"] = accounts
            self.config._save_settings(self.config.settings)
            
            self.refresh_accounts()