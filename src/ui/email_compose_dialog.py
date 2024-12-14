from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                           QLineEdit, QTextEdit, QPushButton, QMessageBox,
                           QComboBox, QSplitter)
from PyQt6.QtCore import Qt, pyqtSignal
from utils.logger import logger
from .attachment_view import AttachmentView

class EmailComposeDialog(QDialog):
    """Dialog for composing new emails or replying to existing ones."""
    
    email_sent = pyqtSignal(dict)  # Emitted when email is sent successfully
    
    def __init__(self, parent=None, reply_to=None, reply_all=False, forward=False):
        super().__init__(parent)
        self.reply_to = reply_to
        self.reply_all = reply_all
        self.forward = forward
        self.setup_ui()
        self.setup_email_content()
    
    def setup_ui(self):
        """Set up the UI components."""
        self.setWindowTitle("Compose Email")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Email fields
        fields_layout = QVBoxLayout()
        
        # To field
        to_layout = QHBoxLayout()
        to_label = QLabel("To:")
        self.to_input = QLineEdit()
        to_layout.addWidget(to_label)
        to_layout.addWidget(self.to_input)
        fields_layout.addLayout(to_layout)
        
        # CC field
        cc_layout = QHBoxLayout()
        cc_label = QLabel("CC:")
        self.cc_input = QLineEdit()
        cc_layout.addWidget(cc_label)
        cc_layout.addWidget(self.cc_input)
        fields_layout.addLayout(cc_layout)
        
        # BCC field
        bcc_layout = QHBoxLayout()
        bcc_label = QLabel("BCC:")
        self.bcc_input = QLineEdit()
        bcc_layout.addWidget(bcc_label)
        bcc_layout.addWidget(self.bcc_input)
        fields_layout.addLayout(bcc_layout)
        
        # Subject field
        subject_layout = QHBoxLayout()
        subject_label = QLabel("Subject:")
        self.subject_input = QLineEdit()
        subject_layout.addWidget(subject_label)
        subject_layout.addWidget(self.subject_input)
        fields_layout.addLayout(subject_layout)
        
        layout.addLayout(fields_layout)
        
        # Create splitter for message body and attachments
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Message body
        self.body_input = QTextEdit()
        splitter.addWidget(self.body_input)
        
        # Attachment view
        self.attachment_view = AttachmentView()
        splitter.addWidget(self.attachment_view)
        
        # Set initial splitter sizes (70% body, 30% attachments)
        splitter.setSizes([700, 300])
        layout.addWidget(splitter)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_email)
        button_layout.addWidget(self.send_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def setup_email_content(self):
        """Set up email content for replies or forwards."""
        if not self.reply_to:
            return
        
        if self.forward:
            self.subject_input.setText(f"Fwd: {self.reply_to['subject']}")
            self.body_input.setText(f"\n\n---------- Forwarded message ----------\n"
                                  f"From: {self.reply_to['from']}\n"
                                  f"Date: {self.reply_to['date']}\n"
                                  f"Subject: {self.reply_to['subject']}\n"
                                  f"To: {', '.join(self.reply_to['recipients']['to'])}\n\n"
                                  f"{self.reply_to['body']}")
            
            # Copy attachments for forwarding
            if 'attachments' in self.reply_to:
                self.attachment_view.set_attachments(self.reply_to['attachments'])
            
        else:  # Reply or Reply All
            self.subject_input.setText(
                f"Re: {self.reply_to['subject'].removeprefix('Re: ')}"
            )
            
            if self.reply_all:
                # Add all recipients except ourselves
                all_recipients = (
                    self.reply_to['recipients']['to'] +
                    self.reply_to['recipients']['cc']
                )
                # Remove the original sender (we're replying to them)
                if self.reply_to['from'] in all_recipients:
                    all_recipients.remove(self.reply_to['from'])
                self.cc_input.setText(", ".join(all_recipients))
            
            self.to_input.setText(self.reply_to['from'])
            self.body_input.setText(f"\n\nOn {self.reply_to['date']}, "
                                  f"{self.reply_to['from']} wrote:\n"
                                  f"> " + self.reply_to['body'].replace("\n", "\n> "))
    
    def send_email(self):
        """Validate and send the email."""
        # Validate required fields
        if not self.to_input.text().strip():
            QMessageBox.warning(self, "Error", "Please specify at least one recipient.")
            return
        
        if not self.subject_input.text().strip():
            reply = QMessageBox.question(
                self,
                "No Subject",
                "Send email without a subject?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        # Prepare email data
        email_data = {
            'to': [addr.strip() for addr in self.to_input.text().split(',')],
            'cc': [addr.strip() for addr in self.cc_input.text().split(',') if addr.strip()],
            'bcc': [addr.strip() for addr in self.bcc_input.text().split(',') if addr.strip()],
            'subject': self.subject_input.text().strip(),
            'body': self.body_input.toPlainText(),
            'attachments': self.attachment_view.attachments
        }
        
        # Emit signal with email data
        self.email_sent.emit(email_data)
        self.accept()
    
    def dragEnterEvent(self, event):
        """Handle drag enter events for attachments."""
        self.attachment_view.dragEnterEvent(event)
    
    def dropEvent(self, event):
        """Handle drop events for attachments."""
        self.attachment_view.dropEvent(event) 