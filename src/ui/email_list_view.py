from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, 
                           QTableWidgetItem, QMenu, QMessageBox,
                           QToolBar, QStyle, QLineEdit, QComboBox,
                           QHBoxLayout, QDateEdit, QCheckBox, QListWidget,
                           QSplitter)
from PyQt6.QtCore import pyqtSignal, Qt, QDate, QSize, QMimeData
from PyQt6.QtGui import QFont, QColor, QBrush, QAction, QIcon, QDrag
from datetime import datetime, timedelta
from utils.error_handler import handle_errors
from utils.logger import logger
from .email_compose_dialog import EmailComposeDialog
from .attachment_view import AttachmentView

class EmailListView(QWidget):
    """
    Widget for displaying a list of emails in a table format.
    Supports drag and drop operations for moving emails between folders.
    """
    
    email_selected = pyqtSignal(dict)  # Emitted when an email is selected
    email_moved = pyqtSignal(str, str)  # Emitted when email is moved (message_id, target_folder)
    email_mark_read = pyqtSignal(str)  # Emitted when email should be marked as read
    email_mark_unread = pyqtSignal(str)  # Emitted when email should be marked as unread
    email_mark_flagged = pyqtSignal(str)  # Emitted when email should be flagged
    email_mark_unflagged = pyqtSignal(str)  # Emitted when email should be unflagged
    email_reply = pyqtSignal(dict)  # Emitted when user wants to reply to email
    email_reply_all = pyqtSignal(dict)  # Emitted when user wants to reply to all
    email_forward = pyqtSignal(dict)  # Emitted when user wants to forward email
    email_delete = pyqtSignal(str)  # Emitted when user wants to delete email
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_folder = None
        self.emails = []  # List of email data dictionaries
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create toolbar
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        layout.addWidget(self.toolbar)
        
        # Create splitter for email list and attachments
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Create email table
        self.email_table = QTableWidget()
        self.email_table.setColumnCount(6)  # Added column for attachment indicator
        self.email_table.setHorizontalHeaderLabels(["Subject", "From", "Date", "Size", "Status", "📎"])
        self.email_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.email_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.email_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.email_table.verticalHeader().setVisible(False)
        self.email_table.setAlternatingRowColors(True)
        self.email_table.setSortingEnabled(True)
        
        # Enable drag and drop
        self.email_table.setDragEnabled(True)
        self.email_table.setAcceptDrops(False)  # Only allow dragging FROM here
        self.email_table.setDragDropMode(QTableWidget.DragDropMode.DragOnly)
        
        # Connect signals
        self.email_table.itemDoubleClicked.connect(self.on_email_double_clicked)
        self.email_table.customContextMenuRequested.connect(self.show_context_menu)
        self.email_table.itemSelectionChanged.connect(self.on_selection_changed)
        
        splitter.addWidget(self.email_table)
        
        # Create attachment view
        self.attachment_view = AttachmentView()
        self.attachment_view.attachment_downloaded.connect(self.on_attachment_downloaded)
        splitter.addWidget(self.attachment_view)
        
        # Set initial splitter sizes (70% email list, 30% attachments)
        splitter.setSizes([700, 300])
        layout.addWidget(splitter)
        
        # Add search/filter widgets
        filter_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search emails...")
        self.search_input.textChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.search_input)
        
        self.date_filter = QComboBox()
        self.date_filter.addItems(["All Time", "Today", "Last 7 Days", "Last 30 Days", "Custom..."])
        self.date_filter.currentTextChanged.connect(self.on_date_filter_changed)
        filter_layout.addWidget(self.date_filter)
        
        self.custom_date = QDateEdit()
        self.custom_date.setCalendarPopup(True)
        self.custom_date.setDate(QDate.currentDate())
        self.custom_date.hide()
        self.custom_date.dateChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.custom_date)
        
        self.show_unread = QCheckBox("Unread Only")
        self.show_unread.stateChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.show_unread)
        
        layout.addLayout(filter_layout)
    
    def update_email_list(self, emails):
        """Update the email list with new data."""
        self.emails = emails
        self.email_table.setRowCount(len(emails))
        
        for row, email in enumerate(emails):
            # Subject
            subject_item = QTableWidgetItem(email['subject'])
            self.email_table.setItem(row, 0, subject_item)
            
            # From
            from_item = QTableWidgetItem(email['from'])
            self.email_table.setItem(row, 1, from_item)
            
            # Date
            date_str = email['date'].strftime("%Y-%m-%d %H:%M")
            date_item = QTableWidgetItem(date_str)
            date_item.setData(Qt.ItemDataRole.UserRole, email['date'])
            self.email_table.setItem(row, 2, date_item)
            
            # Size
            size_item = QTableWidgetItem(self._format_size(len(email['body'])))
            self.email_table.setItem(row, 3, size_item)
            
            # Status
            status = []
            if '\\Seen' not in email.get('flags', []):
                status.append('Unread')
            if '\\Flagged' in email.get('flags', []):
                status.append('⭐')
            status_item = QTableWidgetItem(' '.join(status))
            self.email_table.setItem(row, 4, status_item)
            
            # Attachment indicator
            has_attachments = bool(email.get('attachments', []))
            attachment_item = QTableWidgetItem('📎' if has_attachments else '')
            self.email_table.setItem(row, 5, attachment_item)
            
            # Style unread emails
            if '\\Seen' not in email.get('flags', []):
                font = QFont()
                font.setBold(True)
                for col in range(self.email_table.columnCount()):
                    self.email_table.item(row, col).setFont(font)
        
        self.email_table.resizeColumnsToContents()
        
        # Clear attachment view
        self.attachment_view.set_attachments([])
    
    def on_selection_changed(self):
        """Handle email selection change."""
        selected_items = self.email_table.selectedItems()
        if not selected_items:
            self.attachment_view.set_attachments([])
            return
        
        row = selected_items[0].row()
        email = self.emails[row]
        
        # Update attachment view
        self.attachment_view.set_attachments(email.get('attachments', []))
    
    def on_attachment_downloaded(self, file_path):
        """Handle attachment download completion."""
        logger.info(f"Attachment downloaded to: {file_path}")
        # You could add additional handling here if needed
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events to start drag operations."""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        
        # Get the current item
        item = self.email_table.currentItem()
        if not item:
            return
        
        # Get the email data
        row = item.row()
        email_data = self.emails[row]
        if not email_data or 'message_id' not in email_data:
            return
        
        # Create mime data
        mime_data = QMimeData()
        mime_data.setData("application/x-email-id", email_data['message_id'].encode())
        
        # Create drag operation
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        
        # Optional: Set drag pixmap
        # pixmap = QPixmap(32, 32)
        # pixmap.fill(Qt.GlobalColor.transparent)
        # painter = QPainter(pixmap)
        # painter.drawText(0, 0, 32, 32, Qt.AlignmentFlag.AlignCenter, "📧")
        # painter.end()
        # drag.setPixmap(pixmap)
        
        # Execute drag
        drag.exec(Qt.DropAction.MoveAction)
    
    def on_email_double_clicked(self, item):
        """Handle double-click on email item."""
        row = item.row()
        if 0 <= row < len(self.emails):
            email = self.emails[row]
            self.email_selected.emit(email)
            
            # Mark email as read if it isn't already
            if '\\Seen' not in email.get('flags', []):
                self.email_mark_read.emit(email['message_id'])
    
    def show_context_menu(self, position):
        """Show context menu for email operations."""
        item = self.email_table.itemAt(position)
        if not item:
            return
        
        row = item.row()
        if row < 0 or row >= len(self.emails):
            return
            
        email = self.emails[row]
        menu = QMenu(self)
        
        # Add menu actions
        reply_action = menu.addAction("Reply")
        reply_all_action = menu.addAction("Reply All")
        forward_action = menu.addAction("Forward")
        menu.addSeparator()
        
        # Read/Unread toggle
        if '\\Seen' in email.get('flags', []):
            mark_unread_action = menu.addAction("Mark as Unread")
        else:
            mark_read_action = menu.addAction("Mark as Read")
            
        # Flag/Unflag toggle
        if '\\Flagged' in email.get('flags', []):
            unflag_action = menu.addAction("Remove Flag")
        else:
            flag_action = menu.addAction("Flag")
            
        menu.addSeparator()
        delete_action = menu.addAction("Delete")
        
        # Handle action selection
        action = menu.exec(self.email_table.mapToGlobal(position))
        if not action:
            return
            
        if action == reply_action:
            self.email_reply.emit(email)
        elif action == reply_all_action:
            self.email_reply_all.emit(email)
        elif action == forward_action:
            self.email_forward.emit(email)
        elif action == delete_action:
            self.email_delete.emit(email['message_id'])
        elif '\\Seen' in email.get('flags', []) and action == mark_unread_action:
            self.email_mark_unread.emit(email['message_id'])
        elif '\\Seen' not in email.get('flags', []) and action == mark_read_action:
            self.email_mark_read.emit(email['message_id'])
        elif '\\Flagged' in email.get('flags', []) and action == unflag_action:
            self.email_mark_unflagged.emit(email['message_id'])
        elif '\\Flagged' not in email.get('flags', []) and action == flag_action:
            self.email_mark_flagged.emit(email['message_id'])
    
    def apply_filters(self):
        """Apply search and date filters to the email list."""
        search_text = self.search_input.text().lower()
        show_unread = self.show_unread.isChecked()
        
        # Get date filter
        date_filter = self.date_filter.currentText()
        if date_filter == "All Time":
            min_date = None
        elif date_filter == "Today":
            min_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_filter == "Last 7 Days":
            min_date = datetime.now() - timedelta(days=7)
        elif date_filter == "Last 30 Days":
            min_date = datetime.now() - timedelta(days=30)
        elif date_filter == "Custom...":
            min_date = self.custom_date.date().toPyDate()
        else:
            min_date = None
        
        # Hide rows that don't match filters
        for row in range(self.email_table.rowCount()):
            email = self.emails[row]
            show_row = True
            
            # Apply search filter
            if search_text:
                text_match = False
                for field in ['subject', 'from', 'body']:
                    if search_text in str(email.get(field, '')).lower():
                        text_match = True
                        break
                show_row = text_match
            
            # Apply unread filter
            if show_unread and show_row:
                show_row = '\\Seen' not in email.get('flags', [])
            
            # Apply date filter
            if min_date and show_row:
                email_date = email.get('date')
                if not email_date or email_date < min_date:
                    show_row = False
            
            self.email_table.setRowHidden(row, not show_row)
    
    def on_date_filter_changed(self, filter_text):
        """Handle date filter combo box changes."""
        self.custom_date.setVisible(filter_text == "Custom...")
        self.apply_filters()