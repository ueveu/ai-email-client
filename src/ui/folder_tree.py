from PyQt6.QtWidgets import (QTreeWidget, QTreeWidgetItem, QMenu, 
                           QInputDialog, QMessageBox)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon, QColor, QBrush, QFont, QDragEnterEvent, QDropEvent, QDragMoveEvent
from utils.error_handler import handle_errors
from utils.logger import logger
from datetime import datetime

class FolderTree(QTreeWidget):
    """
    Tree widget for displaying email folders in a hierarchical structure.
    Supports folder selection, context menu operations, and displays unread counts.
    """
    
    folder_selected = pyqtSignal(str)  # Signal emitted when folder is selected
    folder_created = pyqtSignal(str)   # Signal emitted when new folder is created
    folder_deleted = pyqtSignal(str)   # Signal emitted when folder is deleted
    folder_renamed = pyqtSignal(str, str)  # Signal emitted when folder is renamed (old_name, new_name)
    email_moved = pyqtSignal(str, str)  # Signal emitted when email is moved (message_id, target_folder)
    
    SPECIAL_FOLDERS = {
        'INBOX': {'icon': '📥', 'color': '#2196F3'},  # Blue
        'Sent': {'icon': '📤', 'color': '#4CAF50'},   # Green
        'Drafts': {'icon': '📝', 'color': '#FFC107'}, # Yellow
        'Trash': {'icon': '🗑️', 'color': '#F44336'},  # Red
        'Spam': {'icon': '⚠️', 'color': '#FF9800'},   # Orange
        'Archive': {'icon': '📦', 'color': '#9E9E9E'}, # Gray
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_folder = None
        self.folder_items = {}  # Maps folder names to tree items
        
        # Track folder states
        self.expanded_folders = set()  # Remember expanded state
        self.selected_folder = None    # Currently selected folder
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        
        # Track sync status
        self.syncing = False
        self.last_sync = None
    
    def setup_ui(self):
        """Initialize the UI components."""
        # Set up tree widget properties
        self.setHeaderLabels(["Folder", "Unread"])
        self.setColumnCount(2)
        self.setUniformRowHeights(True)
        self.setAnimated(True)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        
        # Style the tree
        self.setStyleSheet("""
            QTreeWidget {
                border: none;
                background-color: transparent;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
            QTreeWidget::item:selected {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        
        # Connect signals
        self.itemClicked.connect(self.on_folder_clicked)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Add drag and drop settings
        self.setDragDropMode(QTreeWidget.DragDropMode.DropOnly)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
    
    def show_context_menu(self, position):
        """Show context menu for folder operations."""
        item = self.itemAt(position)
        if not item:
            # Right-click on empty space - show only create folder option
            menu = QMenu(self)
            create_action = menu.addAction("Create Folder")
            create_action.triggered.connect(lambda: self.create_folder())
            menu.exec(self.mapToGlobal(position))
            return
        
        folder_name = item.text(0)
        menu = QMenu(self)
        
        # Don't allow modification of special folders
        is_special = folder_name in self.SPECIAL_FOLDERS
        
        create_action = menu.addAction("Create Subfolder")
        create_action.triggered.connect(lambda: self.create_folder(parent_folder=folder_name))
        
        if not is_special:
            rename_action = menu.addAction("Rename Folder")
            rename_action.triggered.connect(lambda: self.rename_folder(folder_name))
            
            delete_action = menu.addAction("Delete Folder")
            delete_action.triggered.connect(lambda: self.delete_folder(folder_name))
        
        menu.exec(self.mapToGlobal(position))
    
    def create_folder(self, parent_folder=None):
        """Create a new folder, optionally as a subfolder of parent_folder."""
        dialog_title = "Create Subfolder" if parent_folder else "Create Folder"
        folder_name, ok = QInputDialog.getText(self, dialog_title, "Enter folder name:")
        
        if ok and folder_name:
            # If parent folder is specified, create a hierarchical name
            full_name = f"{parent_folder}/{folder_name}" if parent_folder else folder_name
            self.folder_created.emit(full_name)
    
    def rename_folder(self, folder_name):
        """Rename an existing folder."""
        new_name, ok = QInputDialog.getText(
            self, "Rename Folder", 
            "Enter new folder name:",
            text=folder_name
        )
        
        if ok and new_name and new_name != folder_name:
            self.folder_renamed.emit(folder_name, new_name)
    
    def delete_folder(self, folder_name):
        """Delete a folder after confirmation."""
        reply = QMessageBox.question(
            self,
            "Delete Folder",
            f"Are you sure you want to delete the folder '{folder_name}'?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.folder_deleted.emit(folder_name)
    
    def on_folder_clicked(self, item, column):
        """Handle folder selection."""
        folder_name = item.text(0)
        self.selected_folder = folder_name
        self.folder_selected.emit(folder_name)
    
    def _create_folder_item(self, folder_name):
        """Create a styled tree item for a folder."""
        item = QTreeWidgetItem([folder_name, ""])
        
        # Apply special folder styling
        base_name = folder_name.split('/')[-1]
        if base_name in self.SPECIAL_FOLDERS:
            special = self.SPECIAL_FOLDERS[base_name]
            # Set icon
            item.setText(0, f"{special['icon']} {folder_name}")
            # Set color
            item.setForeground(0, QBrush(QColor(special['color'])))
            # Set font
            font = QFont()
            font.setBold(True)
            item.setFont(0, font)
        
        return item
    
    def update_folder_status(self, folder_name, status):
        """
        Update the status display for a folder.
        
        Args:
            folder_name (str): Name of the folder to update
            status (dict): Status information including unread count
        """
        if folder_name in self.folder_items and status:
            item = self.folder_items[folder_name]
            unread = status.get('unseen', 0)
            
            # Update unread count
            item.setText(1, str(unread) if unread > 0 else "")
            
            # Highlight folders with unread messages
            if unread > 0:
                font = item.font(0)
                font.setBold(True)
                item.setFont(0, font)
                item.setForeground(1, QBrush(QColor('#1976D2')))  # Blue for unread
            else:
                font = item.font(0)
                font.setBold(False)
                item.setFont(0, font)
                item.setForeground(1, QBrush(QColor('#666666')))  # Gray for no unread
    
    def _on_item_clicked(self, item, column):
        """Handle folder selection."""
        folder_name = item.text(0).split()[-1]  # Remove icon if present
        self.current_folder = folder_name
        self.folder_selected.emit(folder_name)
    
    def _on_item_expanded(self, item):
        """Track expanded state of folders."""
        self.expanded_folders.add(item.text(0))
    
    def _on_item_collapsed(self, item):
        """Track collapsed state of folders."""
        self.expanded_folders.discard(item.text(0)) 
    
    def update_folders(self, folders):
        """
        Update the folder tree with the latest folder list.
        
        Args:
            folders (list): List of folder dictionaries from EmailManager
        """
        logger.logger.debug(f"Updating folder tree with {len(folders)} folders")
        
        # Remember expanded and selected states
        expanded_folders = {item.text(0).split()[-1] for item in self.folder_items.values() 
                          if item.isExpanded()}
        selected_folder = self.selected_folder
        
        # Clear current items
        self.clear()
        self.folder_items = {}
        
        # Create root folders first
        root_items = {}
        for folder in folders:
            path_parts = folder['name'].split('/')
            
            # Create or get the root item
            if len(path_parts) > 1:
                root_name = path_parts[0]
                if root_name not in root_items:
                    root_items[root_name] = self._create_folder_item(root_name)
                    self.addTopLevelItem(root_items[root_name])
            
            # Create the folder item
            if len(path_parts) > 1:
                # This is a subfolder
                item = self._create_folder_item(path_parts[-1])
                root_items[path_parts[0]].addChild(item)
            else:
                # This is a root folder
                item = self._create_folder_item(folder['name'])
                self.addTopLevelItem(item)
            
            # Store reference to the item
            self.folder_items[folder['name']] = item
        
        # Restore expanded states
        for folder in expanded_folders:
            if folder in self.folder_items:
                self.folder_items[folder].setExpanded(True)
        
        # Restore selection
        if selected_folder and selected_folder in self.folder_items:
            self.folder_items[selected_folder].setSelected(True)
            self.scrollToItem(self.folder_items[selected_folder])
        
        logger.logger.debug("Folder tree update complete")
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events for email drops."""
        if event.mimeData().hasFormat("application/x-email-id"):
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event: QDragMoveEvent):
        """Handle drag move events to highlight valid drop targets."""
        item = self.itemAt(event.pos())
        if item:
            # Don't allow dropping into special folders that don't support it
            folder_name = item.text(0).split()[-1]  # Remove icon if present
            if folder_name in ['Sent', 'Drafts']:
                event.ignore()
                return
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """Handle email drops onto folders."""
        item = self.itemAt(event.pos())
        if not item:
            event.ignore()
            return
        
        target_folder = item.text(0).split()[-1]  # Remove icon if present
        message_id = event.mimeData().data("application/x-email-id").data().decode()
        
        # Emit signal to move the email
        self.email_moved.emit(message_id, target_folder)
        event.acceptProposedAction()
    
    def start_sync(self):
        """Start folder synchronization."""
        if not self.syncing:
            self.syncing = True
            # Add visual indicator (e.g., spinner) here
            self.update_sync_status("Syncing folders...")
    
    def finish_sync(self):
        """Complete folder synchronization."""
        self.syncing = False
        self.last_sync = datetime.now()
        self.update_sync_status("Sync complete")
    
    def update_sync_status(self, message: str):
        """Update sync status display."""
        # Update status bar or other UI element to show sync status
        if hasattr(self.parent(), 'statusBar'):
            self.parent().statusBar().showMessage(message, 3000)
    
    def refresh_folders(self):
        """Refresh folder list and status from server."""
        self.start_sync()
        # Emit signal to request folder refresh from email manager
        self.folder_refresh_requested.emit()
    
    def update_special_folders(self, folder_data: dict):
        """Update special folder information."""
        for folder_name, data in folder_data.items():
            if folder_name in self.folder_items:
                item = self.folder_items[folder_name]
                # Update folder icon and status
                if 'icon' in data:
                    item.setText(0, f"{data['icon']} {folder_name}")
                if 'color' in data:
                    item.setForeground(0, QBrush(QColor(data['color'])))
                if 'status' in data:
                    self.update_folder_status(folder_name, data['status'])
    
    def get_folder_path(self, item: QTreeWidgetItem) -> str:
        """Get full path for a folder item."""
        path = []
        while item:
            path.insert(0, item.text(0).split()[-1])  # Remove icon if present
            item = item.parent()
        return '/'.join(path)
    
    def find_folder_item(self, folder_path: str) -> QTreeWidgetItem:
        """Find a folder item by its path."""
        parts = folder_path.split('/')
        current = None
        
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.text(0).split()[-1] == parts[0]:
                current = item
                break
        
        if not current or len(parts) == 1:
            return current
        
        for part in parts[1:]:
            found = False
            for i in range(current.childCount()):
                child = current.child(i)
                if child.text(0).split()[-1] == part:
                    current = child
                    found = True
                    break
            if not found:
                return None
        
        return current