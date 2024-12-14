from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, 
                           QTableWidgetItem, QMenu, QMessageBox,
                           QToolBar, QStyle)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QColor, QBrush, QAction, QIcon
from datetime import datetime
from utils.error_handler import handle_errors
from utils.logger import logger

class EmailListView(QWidget):
    """
    Widget for displaying a list of emails in a table format.
    Supports sorting, selection, and context menu operations.
    """
    
    email_selected = pyqtSignal(dict)  # Emitted when an email is selected
    email_moved = pyqtSignal(str, str)  # Emitted when email is moved (message_id, target_folder)
    email_mark_read = pyqtSignal(str)  # Emitted when email should be marked as read
    email_mark_unread = pyqtSignal(str)  # Emitted when email should be marked as unread
    email_mark_flagged = pyqtSignal(str)  # Emitted when email should be flagged
    email_mark_unflagged = pyqtSignal(str)  # Emitted when email should be unflagged
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_folder = None
        self.emails = []  # List of email data dictionaries
        self.setup_ui()
    
    def setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create toolbar
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(Qt.QSize(16, 16))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        
        # Create toolbar actions
        self.setup_toolbar_actions()
        
        # Add toolbar to layout
        layout.addWidget(self.toolbar)
        
        # Create email table
        self.email_table = QTableWidget()
        self.email_table.setColumnCount(4)
        self.email_table.setHorizontalHeaderLabels(["From", "Subject", "Date", "Status"])
        self.email_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.email_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.email_table.setSortingEnabled(True)
        
        # Style the table
        self.email_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
            QTableWidget::item:selected {
                background-color: rgba(25, 118, 210, 0.1);
                color: #1976D2;
            }
        """)
        
        # Connect signals
        self.email_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.email_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.email_table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.email_table)
    
    def setup_toolbar_actions(self):
        """Set up toolbar actions."""
        style = self.style()
        
        # Mark Read/Unread action
        self.read_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton),
            "Mark as Read",
            self
        )
        self.read_action.setEnabled(False)
        self.read_action.triggered.connect(self.toggle_read_status)
        self.toolbar.addAction(self.read_action)
        
        # Flag/Unflag action
        self.flag_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogYesButton),
            "Flag",
            self
        )
        self.flag_action.setEnabled(False)
        self.flag_action.triggered.connect(self.toggle_flag_status)
        self.toolbar.addAction(self.flag_action)
        
        self.toolbar.addSeparator()
        
        # Move to submenu
        self.move_menu = QMenu("Move to", self)
        self.move_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_DirIcon),
            "Move to",
            self
        )
        self.move_action.setEnabled(False)
        self.move_action.setMenu(self.move_menu)
        self.toolbar.addAction(self.move_action)
    
    def update_toolbar_actions(self):
        """Update toolbar actions based on selected email."""
        selected_items = self.email_table.selectedItems()
        has_selection = bool(selected_items)
        
        self.read_action.setEnabled(has_selection)
        self.flag_action.setEnabled(has_selection)
        self.move_action.setEnabled(has_selection)
        
        if has_selection:
            row = selected_items[0].row()
            email_data = self.email_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            
            # Update read/unread action
            is_unread = 'unread' in email_data.get('flags', [])
            self.read_action.setText("Mark as Read" if is_unread else "Mark as Unread")
            
            # Update flag action
            is_flagged = 'flagged' in email_data.get('flags', [])
            self.flag_action.setText("Remove Flag" if is_flagged else "Flag")
            
            # Update move menu
            self.update_move_menu(email_data)
    
    def update_move_menu(self, email_data):
        """Update the move to menu with available folders."""
        self.move_menu.clear()
        
        # Add special folders first
        for folder in ['INBOX', 'Archive', 'Spam', 'Trash']:
            if folder != self.current_folder:
                action = self.move_menu.addAction(folder)
                action.triggered.connect(
                    lambda checked, f=folder: self.move_email(email_data, f)
                )
        
        # Add separator
        if self.move_menu.actions():
            self.move_menu.addSeparator()
        
        # Add custom folders
        if hasattr(self, 'available_folders'):
            for folder in self.available_folders:
                if folder not in ['INBOX', 'Archive', 'Spam', 'Trash'] and folder != self.current_folder:
                    action = self.move_menu.addAction(folder)
                    action.triggered.connect(
                        lambda checked, f=folder: self.move_email(email_data, f)
                    )
    
    def toggle_read_status(self):
        """Toggle read/unread status of selected email."""
        selected_items = self.email_table.selectedItems()
        if not selected_items:
            return
        
        row = selected_items[0].row()
        email_data = self.email_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        is_unread = 'unread' in email_data.get('flags', [])
        
        if is_unread:
            self.mark_read(email_data)
        else:
            self.mark_unread(email_data)
    
    def toggle_flag_status(self):
        """Toggle flagged status of selected email."""
        selected_items = self.email_table.selectedItems()
        if not selected_items:
            return
        
        row = selected_items[0].row()
        email_data = self.email_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        is_flagged = 'flagged' in email_data.get('flags', [])
        
        if is_flagged:
            self.mark_unflagged(email_data)
        else:
            self.mark_flagged(email_data)
    
    def update_emails(self, emails, folder=None):
        """
        Update the email list with new data.
        
        Args:
            emails (list): List of email data dictionaries
            folder (str, optional): Current folder name
        """
        logger.logger.debug(f"Updating email list with {len(emails)} emails")
        self.emails = emails
        self.current_folder = folder
        
        # Remember sorting state
        current_sort_column = self.email_table.horizontalHeader().sortIndicatorSection()
        current_sort_order = self.email_table.horizontalHeader().sortIndicatorOrder()
        
        self.email_table.setRowCount(0)
        for email in emails:
            row = self.email_table.rowCount()
            self.email_table.insertRow(row)
            
            # From
            from_item = QTableWidgetItem(email['from'])
            self.email_table.setItem(row, 0, from_item)
            
            # Subject
            subject_item = QTableWidgetItem(email['subject'])
            self.email_table.setItem(row, 1, subject_item)
            
            # Date
            date_str = email['date'].strftime("%Y-%m-%d %H:%M")
            date_item = QTableWidgetItem(date_str)
            date_item.setData(Qt.ItemDataRole.UserRole, email['date'])  # Store datetime for sorting
            self.email_table.setItem(row, 2, date_item)
            
            # Status
            status = []
            if 'unread' in email.get('flags', []):
                status.append("Unread")
            if 'flagged' in email.get('flags', []):
                status.append("Flagged")
            if email.get('attachments'):
                status.append("📎")
            status_item = QTableWidgetItem(" ".join(status))
            self.email_table.setItem(row, 3, status_item)
            
            # Style unread emails
            if 'unread' in email.get('flags', []):
                font = QFont()
                font.setBold(True)
                for col in range(4):
                    self.email_table.item(row, col).setFont(font)
            
            # Store email data
            from_item.setData(Qt.ItemDataRole.UserRole, email)
        
        # Restore sorting
        self.email_table.sortItems(current_sort_column, current_sort_order)
        
        # Resize columns
        self.email_table.resizeColumnsToContents()
        logger.logger.debug("Email list update complete")
    
    def show_context_menu(self, position):
        """Show context menu for email operations."""
        item = self.email_table.itemAt(position)
        if not item:
            return
        
        row = item.row()
        email_data = self.email_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        menu = QMenu(self)
        
        # Add mark read/unread actions
        is_unread = 'unread' in email_data.get('flags', [])
        read_action = menu.addAction("Mark as Read" if is_unread else "Mark as Unread")
        read_action.triggered.connect(
            lambda: self.mark_read(email_data) if is_unread else self.mark_unread(email_data)
        )
        
        # Add flag/unflag actions
        is_flagged = 'flagged' in email_data.get('flags', [])
        flag_action = menu.addAction("Remove Flag" if is_flagged else "Flag")
        flag_action.triggered.connect(
            lambda: self.mark_unflagged(email_data) if is_flagged else self.mark_flagged(email_data)
        )
        
        menu.addSeparator()
        
        # Add move to folder submenu
        move_menu = menu.addMenu("Move to")
        
        # Add special folders first
        for folder in ['INBOX', 'Archive', 'Spam', 'Trash']:
            if folder != self.current_folder:
                action = move_menu.addAction(folder)
                action.triggered.connect(
                    lambda checked, f=folder: self.move_email(email_data, f)
                )
        
        # Add separator
        if move_menu.actions():
            move_menu.addSeparator()
        
        # Add custom folders if available
        if hasattr(self, 'available_folders'):
            for folder in self.available_folders:
                if folder not in ['INBOX', 'Archive', 'Spam', 'Trash'] and folder != self.current_folder:
                    action = move_menu.addAction(folder)
                    action.triggered.connect(
                        lambda checked, f=folder: self.move_email(email_data, f)
                    )
        
        menu.exec(self.email_table.mapToGlobal(position))
    
    def move_email(self, email_data, target_folder):
        """
        Move an email to another folder.
        
        Args:
            email_data (dict): Email data dictionary
            target_folder (str): Target folder name
        """
        # Confirm move
        reply = QMessageBox.question(
            self,
            "Move Email",
            f"Move this email to {target_folder}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.email_moved.emit(str(email_data['message_id']), target_folder)
    
    def on_selection_changed(self):
        """Handle email selection changes."""
        selected_items = self.email_table.selectedItems()
        if not selected_items:
            return
        
        row = selected_items[0].row()
        email_data = self.email_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.email_selected.emit(email_data)
        
        # Update toolbar actions
        self.update_toolbar_actions()
    
    def update_folder_list(self, folders):
        """
        Update the list of available folders for move operations.
        
        Args:
            folders (list): List of folder dictionaries
        """
        self.available_folders = [f['name'] for f in folders] 
    
    def mark_read(self, email_data):
        """Emit signal to mark email as read."""
        self.email_mark_read.emit(str(email_data['message_id']))
    
    def mark_unread(self, email_data):
        """Emit signal to mark email as unread."""
        self.email_mark_unread.emit(str(email_data['message_id']))
    
    def mark_flagged(self, email_data):
        """Emit signal to flag email."""
        self.email_mark_flagged.emit(str(email_data['message_id']))
    
    def mark_unflagged(self, email_data):
        """Emit signal to unflag email."""
        self.email_mark_unflagged.emit(str(email_data['message_id']))