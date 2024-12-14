from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                           QTreeWidget, QTreeWidgetItem, QTextEdit, QPushButton,
                           QLabel, QComboBox, QProgressBar, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QClipboard, QGuiApplication
from config import Config
from email_manager import EmailManager
from ai.reply_generator import ReplyGenerator
from datetime import datetime
import logging

class EmailAnalysisTab(QWidget):
    """Tab for analyzing emails and generating AI replies."""
    
    def __init__(self, ai_provider):
        """Initialize the email analysis tab."""
        super().__init__()
        self.config = Config()
        self.email_manager = None
        self.reply_generator = ReplyGenerator(ai_provider)
        self.current_email = None
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Account selector
        account_layout = QHBoxLayout()
        account_layout.addWidget(QLabel("Email Account:"))
        self.account_selector = QComboBox()
        self.account_selector.currentIndexChanged.connect(self.on_account_changed)
        account_layout.addWidget(self.account_selector)
        account_layout.addStretch()
        layout.addLayout(account_layout)
        
        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Email list (left side)
        self.email_tree = QTreeWidget()
        self.email_tree.setHeaderLabels(["Subject", "From", "Date"])
        self.email_tree.itemClicked.connect(self.on_email_selected)
        splitter.addWidget(self.email_tree)
        
        # Right side container
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Email content
        right_layout.addWidget(QLabel("Email Content:"))
        self.email_content = QTextEdit()
        self.email_content.setReadOnly(True)
        right_layout.addWidget(self.email_content)
        
        # Sentiment analysis
        right_layout.addWidget(QLabel("Sentiment Analysis:"))
        self.sentiment_text = QTextEdit()
        self.sentiment_text.setReadOnly(True)
        self.sentiment_text.setMaximumHeight(100)
        right_layout.addWidget(self.sentiment_text)
        
        # AI Reply section
        right_layout.addWidget(QLabel("AI Generated Replies:"))
        self.reply_suggestions = QTextEdit()
        self.reply_suggestions.setReadOnly(True)
        right_layout.addWidget(self.reply_suggestions)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        right_layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh Emails")
        self.refresh_btn.clicked.connect(self.refresh_emails)
        button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        
        self.generate_reply_btn = QPushButton("Generate Reply")
        self.generate_reply_btn.clicked.connect(self.generate_reply)
        button_layout.addWidget(self.generate_reply_btn)
        
        self.copy_reply_btn = QPushButton("Copy to Clipboard")
        self.copy_reply_btn.clicked.connect(self.copy_reply)
        button_layout.addWidget(self.copy_reply_btn)
        
        right_layout.addLayout(button_layout)
        
        splitter.addWidget(right_widget)
        layout.addWidget(splitter)
        
        # Update account list
        self.refresh_accounts()
        
        # Set initial button states
        self.update_button_states()
    
    def refresh_accounts(self):
        """Refresh the account selector with available accounts."""
        self.account_selector.clear()
        accounts = self.config.settings.get("accounts", [])
        
        for account in accounts:
            self.account_selector.addItem(
                f"{account['name']} <{account['email']}>",
                account
            )
    
    def on_account_changed(self, index):
        """Handle account selection change."""
        if index >= 0:
            account_data = self.account_selector.itemData(index)
            if account_data:
                self.email_manager = EmailManager(account_data)
                self.refresh_emails()
            else:
                self.email_manager = None
                self.email_tree.clear()
        
        self.update_button_states()
    
    def refresh_emails(self):
        """Fetch and display emails for the selected account."""
        if not self.email_manager:
            return
            
        try:
            self.email_tree.clear()
            self.progress_bar.setRange(0, 0)
            self.progress_bar.show()
            
            # Connect to email server
            if self.email_manager.connect_imap():
                # Fetch emails
                emails = self.email_manager.fetch_emails(limit=50)
                
                # Add to tree
                for email in emails:
                    item = QTreeWidgetItem([
                        email["subject"],
                        email["from"],
                        email["date"].strftime("%Y-%m-%d %H:%M")
                    ])
                    item.setData(0, Qt.ItemDataRole.UserRole, email)
                    self.email_tree.addTopLevelItem(item)
            else:
                QMessageBox.warning(
                    self,
                    "Connection Error",
                    "Could not connect to email server. Please check your settings."
                )
        except Exception as e:
            logging.error(f"Error refreshing emails: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Error refreshing emails: {str(e)}"
            )
        finally:
            self.progress_bar.hide()
            self.update_button_states()
    
    def on_email_selected(self, item):
        """Handle email selection from the tree."""
        self.current_email = item.data(0, Qt.ItemDataRole.UserRole)
        if self.current_email:
            # Show email content
            self.email_content.setText(self.current_email["body"])
            
            # Analyze sentiment
            self.analyze_sentiment()
            
            # Clear previous replies
            self.reply_suggestions.clear()
        
        self.update_button_states()
    
    def analyze_sentiment(self):
        """Analyze sentiment of the selected email."""
        if not self.current_email:
            return
            
        try:
            self.sentiment_text.setText("Analyzing sentiment...")
            result = self.reply_generator.analyze_sentiment(self.current_email["body"])
            
            if result["success"]:
                self.sentiment_text.setText(result["analysis"])
            else:
                self.sentiment_text.setText(f"Error: {result.get('error', 'Unknown error')}")
        except Exception as e:
            logging.error(f"Error analyzing sentiment: {str(e)}")
            self.sentiment_text.setText(f"Error analyzing sentiment: {str(e)}")
    
    def generate_reply(self):
        """Generate AI reply for the selected email."""
        if not self.current_email:
            return
            
        try:
            self.progress_bar.setRange(0, 0)
            self.progress_bar.show()
            self.reply_suggestions.setText("Generating reply suggestions...")
            
            # Get suggestions
            suggestions = self.reply_generator.generate_reply(
                {
                    "subject": self.current_email["subject"],
                    "body": self.current_email["body"],
                    "from_email": self.current_email["from"],
                    "date": self.current_email["date"]
                }
            )
            
            # Display suggestions
            if suggestions:
                self.reply_suggestions.setText("\n\n---\n\n".join(suggestions))
            else:
                self.reply_suggestions.setText("No reply suggestions generated.")
                
        except Exception as e:
            logging.error(f"Error generating reply: {str(e)}")
            self.reply_suggestions.setText(f"Error generating reply: {str(e)}")
        finally:
            self.progress_bar.hide()
    
    def copy_reply(self):
        """Copy selected reply to clipboard."""
        text = self.reply_suggestions.textCursor().selectedText()
        if not text:
            text = self.reply_suggestions.toPlainText()
            
        if text:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(text)
            
            QMessageBox.information(
                self,
                "Success",
                "Reply copied to clipboard!"
            )
    
    def update_button_states(self):
        """Update button enabled states."""
        has_account = bool(self.email_manager)
        has_email = bool(self.current_email)
        has_reply = bool(self.reply_suggestions.toPlainText())
        
        self.refresh_btn.setEnabled(has_account)
        self.generate_reply_btn.setEnabled(has_email)
        self.copy_reply_btn.setEnabled(has_reply) 