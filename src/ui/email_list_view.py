from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
                            QAbstractItemView, QMessageBox, QApplication)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont
from datetime import datetime
from utils import logger
from .loading_spinner import LoadingSpinner

class EmailListView(QWidget):
    """Widget for displaying a list of emails."""
    
    email_selected = pyqtSignal(dict)  # Emitted when an email is selected
    email_double_clicked = pyqtSignal(dict)  # Emitted when an email is double-clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.email_manager = None
        self.emails = []
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        
        # Email list table
        self.email_table = QTreeWidget()
        self.email_table.setHeaderLabels(["Subject", "From", "Date"])
        self.email_table.itemClicked.connect(self.on_email_clicked)
        self.email_table.itemDoubleClicked.connect(self.on_email_double_clicked)
        self.email_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.email_table)
        
        # Loading spinner
        self.loading_spinner = LoadingSpinner(self)
        self.loading_spinner.hide()
        
    def set_email_manager(self, email_manager):
        """Set the email manager instance."""
        self.email_manager = email_manager
        
    def clear(self):
        """Clear the email list."""
        self.email_table.clear()
        self.emails = []
        
    def set_emails(self, emails: list):
        """Set and display emails in the list."""
        self.emails = emails
        self.email_table.clear()
        
        try:
            # Show loading state
            self.loading_spinner.start()
            QApplication.processEvents()
            
            for email_data in emails:
                try:
                    # Parse date string if needed
                    date = email_data.get('date')
                    if isinstance(date, str):
                        try:
                            # Try various date formats
                            date = datetime.strptime(date, '%a, %d %b %Y %H:%M:%S %z')
                        except ValueError:
                            try:
                                date = datetime.strptime(date, '%d %b %Y %H:%M:%S %z')
                            except ValueError:
                                date = datetime.now()
                    
                    # Create item with proper formatting
                    subject = email_data.get('subject', 'No subject')
                    sender = email_data.get('from', 'Unknown')
                    date_str = date.strftime("%Y-%m-%d %H:%M") if date else ""
                    
                    item = QTreeWidgetItem([subject, sender, date_str])
                    
                    # Store the full email data
                    item.setData(0, Qt.ItemDataRole.UserRole, email_data)
                    
                    # Style unread emails
                    if email_data.get('flags') and '\\Seen' not in email_data['flags']:
                        font = item.font(0)
                        font.setBold(True)
                        for col in range(3):
                            item.setFont(col, font)
                    
                    # Add attachment indicator
                    if email_data.get('attachments'):
                        item.setText(0, f"📎 {subject}")
                    
                    # Add flag indicator
                    if email_data.get('flags') and '\\Flagged' in email_data['flags']:
                        item.setText(0, f"⭐ {item.text(0)}")
                    
                    self.email_table.addTopLevelItem(item)
                    
                except Exception as e:
                    logger.error(f"Error adding email to list: {str(e)}")
                    logger.error(f"Email data: {email_data}")
                    continue
            
            # Resize columns to content
            for i in range(3):
                self.email_table.resizeColumnToContents(i)
            
            logger.debug(f"Email list now has {self.email_table.topLevelItemCount()} items")
            
        except Exception as e:
            logger.error(f"Error setting emails: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to display emails: {str(e)}"
            )
        finally:
            self.loading_spinner.stop()
    
    def on_email_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle single click on email item."""
        email_data = item.data(0, Qt.ItemDataRole.UserRole)
        if email_data:
            self.email_selected.emit(email_data)
            
            # Mark as read if unread
            if '\\Seen' not in email_data.get('flags', []):
                try:
                    if self.email_manager:
                        self.email_manager.mark_read(email_data['message_id'])
                        # Update UI to reflect read status
                        font = item.font(0)
                        font.setBold(False)
                        for col in range(3):
                            item.setFont(col, font)
                except Exception as e:
                    logger.error(f"Error marking email as read: {str(e)}")
    
    def on_email_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double click on email item."""
        email_data = item.data(0, Qt.ItemDataRole.UserRole)
        if email_data:
            # Open email in a new window or trigger reply
            self.email_double_clicked.emit(email_data)