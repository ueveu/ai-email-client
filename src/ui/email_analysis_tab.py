from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                           QTreeWidget, QTreeWidgetItem, QTextEdit, QPushButton,
                           QLabel, QComboBox, QApplication, QMessageBox,
                           QRadioButton, QButtonGroup)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QClipboard
from .folder_tree import FolderTree
from .attachment_view import AttachmentView
from email_manager import EmailManager
from utils.logger import logger
from services.ai_service import AIService
from .loading_spinner import LoadingSpinner

class EmailAnalysisTab(QWidget):
    """
    Tab for analyzing emails and generating AI replies.
    Displays email folders, list, content, and suggested replies.
    """
    
    def __init__(self, parent=None):
        """Initialize the email analysis tab."""
        super().__init__(parent)
        self.email_manager = None
        self.current_folder = None
        self.ai_service = AIService()
        self.loading_spinner = LoadingSpinner(self)
        logger.logger.debug("Initializing EmailAnalysisTab")
        self.setup_ui()
    
    def setup_ui(self):
        """Sets up the UI components for email analysis."""
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
        
        # Folder tree (leftmost)
        self.folder_tree = FolderTree()
        self.folder_tree.folder_selected.connect(self.on_folder_selected)
        splitter.addWidget(self.folder_tree)
        
        # Email list (middle)
        self.email_tree = QTreeWidget()
        self.email_tree.setHeaderLabels(["Subject", "From", "Date"])
        self.email_tree.itemClicked.connect(self.on_email_selected)
        splitter.addWidget(self.email_tree)
        
        # Right side container with vertical splitter
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Email content and attachments container
        email_content_widget = QWidget()
        email_content_layout = QVBoxLayout(email_content_widget)
        
        # Email content
        self.email_content = QTextEdit()
        self.email_content.setReadOnly(True)
        email_content_layout.addWidget(QLabel("Email Content:"))
        email_content_layout.addWidget(self.email_content)
        
        # Attachment view
        self.attachment_view = AttachmentView()
        self.attachment_view.attachment_saved.connect(self.on_attachment_saved)
        email_content_layout.addWidget(self.attachment_view)
        
        right_splitter.addWidget(email_content_widget)
        
        # AI Reply section
        reply_widget = QWidget()
        reply_layout = QVBoxLayout(reply_widget)
        
        # Tone selection
        tone_layout = QHBoxLayout()
        tone_layout.addWidget(QLabel("Reply Tone:"))
        self.tone_group = QButtonGroup(self)
        
        for tone in ['Professional', 'Friendly', 'Formal', 'Casual']:
            radio = QRadioButton(tone)
            if tone == 'Professional':
                radio.setChecked(True)
            self.tone_group.addButton(radio)
            tone_layout.addWidget(radio)
        
        tone_layout.addStretch()
        reply_layout.addLayout(tone_layout)
        
        reply_layout.addWidget(QLabel("AI Generated Replies:"))
        self.reply_suggestions = QTextEdit()
        self.reply_suggestions.setReadOnly(True)
        reply_layout.addWidget(self.reply_suggestions)
        
        # Feedback section
        feedback_layout = QHBoxLayout()
        self.feedback_combo = QComboBox()
        self.feedback_combo.addItems([
            "Select Feedback",
            "Very Helpful",
            "Somewhat Helpful",
            "Not Helpful",
            "Needs Improvement"
        ])
        feedback_layout.addWidget(self.feedback_combo)
        
        self.submit_feedback_btn = QPushButton("Submit Feedback")
        self.submit_feedback_btn.clicked.connect(self.submit_feedback)
        self.submit_feedback_btn.setEnabled(False)
        feedback_layout.addWidget(self.submit_feedback_btn)
        
        reply_layout.addLayout(feedback_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.generate_reply_btn = QPushButton("Generate Reply")
        self.generate_reply_btn.clicked.connect(self.generate_reply)
        self.copy_reply_btn = QPushButton("Copy to Clipboard")
        self.copy_reply_btn.clicked.connect(self.copy_reply)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_view)
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.generate_reply_btn)
        button_layout.addWidget(self.copy_reply_btn)
        reply_layout.addLayout(button_layout)
        
        right_splitter.addWidget(reply_widget)
        splitter.addWidget(right_splitter)
        
        layout.addWidget(splitter)
        
        # Set initial splitter sizes (25% folders, 35% email list, 40% content)
        splitter.setSizes([250, 350, 400])
        right_splitter.setSizes([600, 400])  # 60% content, 40% replies
        
        # Connect feedback combo box
        self.feedback_combo.currentIndexChanged.connect(self._on_feedback_selected)
    
    def set_email_manager(self, email_manager):
        """Set the email manager and initialize the view."""
        logger.logger.debug(f"Setting email manager: {email_manager}")
        self.email_manager = email_manager
        if self.email_manager:
            # Initialize with INBOX folder
            self.current_folder = 'INBOX'
            self.refresh_view()
        else:
            logger.logger.warning("Email manager is None")
    
    def refresh_view(self):
        """Refresh the entire view including folders and emails."""
        logger.logger.debug("Refreshing view")
        if not self.email_manager:
            logger.logger.warning("No email manager available")
            return
        
        try:
            # Update folder tree
            folders = self.email_manager.list_folders()
            logger.logger.debug(f"Found {len(folders)} folders")
            status_data = {}
            for folder in folders:
                status = self.email_manager.get_folder_status(folder['name'])
                if status:
                    status_data[folder['name']] = status
            
            self.folder_tree.update_folders(folders, status_data)
            
            # Refresh emails in current folder
            if self.current_folder:
                self.refresh_emails()
            else:
                logger.logger.debug("No folder selected for refresh")
        except Exception as e:
            logger.logger.error(f"Error refreshing view: {str(e)}")
    
    def on_account_changed(self, index):
        """Handle account selection change."""
        # Clear current view
        self.email_content.clear()
        self.reply_suggestions.clear()
        self.attachment_view.set_attachments([])
        self.refresh_view()
    
    def on_folder_selected(self, folder_name):
        """Handle folder selection."""
        logger.logger.debug(f"Selected folder: {folder_name}")
        self.current_folder = folder_name
        self.refresh_emails()
    
    def refresh_emails(self):
        """Fetch and display emails for the current folder."""
        logger.logger.debug("Refreshing emails")
        self.email_tree.clear()
        
        if not self.email_manager:
            logger.logger.warning("No email manager available")
            return
        
        if not self.current_folder:
            logger.logger.warning("No folder selected")
            return
        
        try:
            # Fetch emails from the selected folder
            logger.logger.debug(f"Fetching emails from folder: {self.current_folder}")
            emails = self.email_manager.fetch_emails(
                folder=self.current_folder,
                limit=50,
                offset=0
            )
            logger.logger.debug(f"Fetched {len(emails)} emails")
            
            # Add emails to the tree
            for email_data in emails:
                try:
                    logger.logger.debug(f"Adding email: {email_data.get('subject', 'No subject')} from {email_data.get('from', 'Unknown')}")
                    item = QTreeWidgetItem([
                        email_data.get("subject", "No subject"),
                        email_data.get("from", "Unknown"),
                        email_data.get("date", "").strftime("%Y-%m-%d %H:%M") if email_data.get("date") else ""
                    ])
                    item.setData(0, Qt.ItemDataRole.UserRole, email_data)
                    self.email_tree.addTopLevelItem(item)
                except Exception as e:
                    logger.logger.error(f"Error adding email to tree: {str(e)}")
                    logger.logger.error(f"Email data: {email_data}")
            
            logger.logger.debug(f"Email tree now has {self.email_tree.topLevelItemCount()} items")
        except Exception as e:
            logger.logger.error(f"Error refreshing emails: {str(e)}")
    
    def on_email_selected(self, item):
        """Handle email selection from the tree widget."""
        email_data = item.data(0, Qt.ItemDataRole.UserRole)
        if email_data:
            self.email_content.setText(email_data["body"])
            self.reply_suggestions.clear()
            
            # Update attachment view
            attachments = email_data.get("attachments", [])
            self.attachment_view.set_attachments(attachments)
    
    def on_attachment_saved(self, save_path):
        """Handle successful attachment save."""
        logger.logger.info(f"Attachment saved to: {save_path}")
    
    def generate_reply(self):
        """Generate AI reply for the selected email."""
        if not self.email_content.toPlainText():
            logger.warning("No email selected for reply generation")
            return
        
        try:
            # Show loading spinner
            self.loading_spinner.start()
            
            # Get selected email data
            selected_items = self.email_tree.selectedItems()
            if not selected_items:
                logger.warning("No email selected")
                return
            
            email_data = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
            if not email_data:
                logger.warning("No email data found")
                return
            
            # Get AI service from parent window
            ai_service = self.parent().ai_service
            if not ai_service or not ai_service.model:
                QMessageBox.warning(
                    self,
                    "AI Service Not Available",
                    "Please configure your Gemini API key in the AI menu first."
                )
                return
            
            # Get selected tone
            tone = self.tone_group.checkedButton().text().lower()
            
            # Prepare context for AI
            context = {
                'conversation_history': self._get_conversation_history(email_data),
                'relationship': self._determine_relationship(email_data),
                'tone': tone
            }
            
            # Generate reply suggestions
            suggestions = ai_service.generate_reply(
                email_data.get('body', ''),
                context=context,
                num_suggestions=3
            )
            
            if suggestions:
                # Display suggestions
                self.reply_suggestions.clear()
                self.reply_suggestions.append("AI Generated Reply Suggestions:\n")
                for i, suggestion in enumerate(suggestions, 1):
                    self.reply_suggestions.append(f"\nSuggestion {i}:\n{'-' * 40}\n{suggestion}\n")
                
                # Enable copy button and feedback
                self.copy_reply_btn.setEnabled(True)
                self.feedback_combo.setEnabled(True)
                self.feedback_combo.setCurrentIndex(0)
            else:
                self.reply_suggestions.setText("Failed to generate reply suggestions.")
                self.copy_reply_btn.setEnabled(False)
                self.feedback_combo.setEnabled(False)
        
        except Exception as e:
            logger.error(f"Error generating reply: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to generate reply: {str(e)}"
            )
        finally:
            self.loading_spinner.stop()
    
    def copy_reply(self):
        """Copy selected reply suggestion to clipboard."""
        if self.reply_suggestions.toPlainText():
            # Get selected text or all text if nothing is selected
            cursor = self.reply_suggestions.textCursor()
            text = cursor.selectedText() or self.reply_suggestions.toPlainText()
            
            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            
            # Show success message in status bar
            if hasattr(self.parent(), 'status_bar'):
                self.parent().status_bar.showMessage("Reply copied to clipboard", 3000)
    
    def _get_conversation_history(self, email_data: dict) -> str:
        """Get conversation history for context."""
        try:
            # Get references and in-reply-to headers
            references = email_data.get('references', [])
            in_reply_to = email_data.get('in_reply_to', [])
            
            # Combine all message IDs
            message_ids = list(set(references + in_reply_to))
            
            if not message_ids:
                return ""
            
            # Get related emails from email manager
            history = []
            for msg_id in message_ids:
                related_email = self.email_manager.get_email_by_message_id(msg_id)
                if related_email:
                    history.append(
                        f"On {related_email['date']}, {related_email['from']} wrote:\n"
                        f"{related_email['body']}\n"
                    )
            
            return "\n".join(history)
        
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return ""
    
    def _determine_relationship(self, email_data: dict) -> str:
        """Determine relationship context with sender."""
        try:
            sender = email_data.get('from', '')
            
            # Check if sender is in contacts (if implemented)
            if hasattr(self.email_manager, 'is_contact'):
                if self.email_manager.is_contact(sender):
                    return 'known_contact'
            
            # Check domain
            sender_domain = sender.split('@')[-1].lower()
            our_domain = self.email_manager.get_account_domain().lower()
            
            if sender_domain == our_domain:
                return 'internal'
            
            return 'external'
        
        except Exception as e:
            logger.error(f"Error determining relationship: {str(e)}")
            return 'unknown'
    
    def _on_feedback_selected(self, index):
        """Handle feedback selection."""
        self.submit_feedback_btn.setEnabled(index > 0)
    
    def submit_feedback(self):
        """Submit user feedback for AI-generated replies."""
        try:
            # Get selected email data
            selected_items = self.email_tree.selectedItems()
            if not selected_items:
                return
            
            email_data = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
            if not email_data:
                return
            
            # Get selected feedback
            feedback = self.feedback_combo.currentText()
            if feedback == "Select Feedback":
                return
            
            # Get selected tone
            tone = self.tone_group.checkedButton().text().lower()
            
            # Get AI service
            ai_service = self.parent().ai_service
            if not ai_service:
                return
            
            # Prepare context for learning
            context = {
                'email_id': email_data.get('message_id'),
                'subject': email_data.get('subject'),
                'tone': tone,
                'relationship': self._determine_relationship(email_data)
            }
            
            # Get selected reply (if any text is selected)
            cursor = self.reply_suggestions.textCursor()
            selected_reply = cursor.selectedText()
            
            # If no text is selected, use the entire content
            if not selected_reply:
                selected_reply = self.reply_suggestions.toPlainText()
            
            # Submit feedback for learning
            ai_service.learn_from_selection(
                selected_reply,
                context,
                feedback
            )
            
            # Show success message
            self.parent().status_bar.showMessage("Feedback submitted successfully", 3000)
            
            # Reset feedback controls
            self.feedback_combo.setCurrentIndex(0)
            self.submit_feedback_btn.setEnabled(False)
            
        except Exception as e:
            logger.error(f"Error submitting feedback: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to submit feedback: {str(e)}"
            )