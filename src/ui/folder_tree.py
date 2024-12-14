from PyQt6.QtWidgets import (QTreeWidget, QTreeWidgetItem, QMenu, 
                           QInputDialog, QMessageBox)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon, QColor, QBrush, QFont
from utils.error_handler import handle_errors
from utils.logger import logger

class FolderTree(QTreeWidget):
    """
    Tree widget for displaying email folders in a hierarchical structure.
    Supports folder selection, context menu operations, and displays unread counts.
    """
    
    folder_selected = pyqtSignal(str)  # Signal emitted when folder is selected
    folder_created = pyqtSignal(str)   # Signal emitted when new folder is created
    folder_deleted = pyqtSignal(str)   # Signal emitted when folder is deleted
    folder_renamed = pyqtSignal(str, str)  # Signal emitted when folder is renamed (old_name, new_name)
    
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
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px;
            }
            QTreeWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976D2;
            }
        """)
        
        # Connect signals
        self.itemClicked.connect(self._on_item_clicked)
        self.itemExpanded.connect(self._on_item_expanded)
        self.itemCollapsed.connect(self._on_item_collapsed)
        
        # Set up context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    @handle_errors
    def update_folders(self, folders, status_data=None):
        """
        Update the folder tree with the latest folder list and status.
        
        Args:
            folders (list): List of folder dictionaries from EmailManager
            status_data (dict): Optional dict mapping folder names to their status
        """
        # Remember expanded and selected states
        expanded_folders = {item.text(0) for item in self.folder_items.values() 
                          if item.isExpanded()}
        selected_folder = self.currentItem().text(0) if self.currentItem() else None
        
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
            
            # Update status if provided
            if status_data and folder['name'] in status_data:
                self.update_folder_status(folder['name'], status_data[folder['name']])
        
        # Restore expanded states
        for folder in expanded_folders:
            if folder in self.folder_items:
                self.folder_items[folder].setExpanded(True)
        
        # Restore selection
        if selected_folder and selected_folder in self.folder_items:
            self.folder_items[selected_folder].setSelected(True)
            self.scrollToItem(self.folder_items[selected_folder])
    
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
    
    @handle_errors
    def _show_context_menu(self, position):
        """Show context menu for folder operations."""
        item = self.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        
        # Add folder operations
        create_subfolder = menu.addAction("Create Subfolder")
        rename_folder = menu.addAction("Rename Folder")
        delete_folder = menu.addAction("Delete Folder")
        
        # Disable operations for special folders
        folder_name = item.text(0).split()[-1]  # Remove icon if present
        is_special = folder_name in self.SPECIAL_FOLDERS
        
        rename_folder.setEnabled(not is_special)
        delete_folder.setEnabled(not is_special)
        
        # Show menu and handle selection
        action = menu.exec(self.mapToGlobal(position))
        
        if action == create_subfolder:
            self._create_subfolder(item)
        elif action == rename_folder:
            self._rename_folder(item)
        elif action == delete_folder:
            self._delete_folder(item)
    
    @handle_errors
    def _create_subfolder(self, parent_item):
        """Create a new subfolder under the selected folder."""
        name, ok = QInputDialog.getText(
            self, 
            "Create Subfolder",
            "Enter subfolder name:"
        )
        
        if ok and name:
            parent_path = parent_item.text(0).split()[-1]  # Remove icon if present
            new_folder = f"{parent_path}/{name}"
            
            # Create new item
            new_item = self._create_folder_item(name)
            parent_item.addChild(new_item)
            parent_item.setExpanded(True)
            
            # Store reference and emit signal
            self.folder_items[new_folder] = new_item
            self.folder_created.emit(new_folder)
    
    @handle_errors
    def _rename_folder(self, item):
        """Rename the selected folder."""
        old_name = item.text(0).split()[-1]  # Remove icon if present
        
        name, ok = QInputDialog.getText(
            self,
            "Rename Folder",
            "Enter new folder name:",
            text=old_name
        )
        
        if ok and name and name != old_name:
            # Update item
            item.setText(0, name)
            
            # Update folder items mapping
            self.folder_items[name] = self.folder_items.pop(old_name)
            
            # Emit signal
            self.folder_renamed.emit(old_name, name)
    
    @handle_errors
    def _delete_folder(self, item):
        """Delete the selected folder."""
        folder_name = item.text(0).split()[-1]  # Remove icon if present
        
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the folder '{folder_name}'?\n"
            "All messages in this folder will be moved to Trash.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Remove item from tree
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                self.takeTopLevelItem(self.indexOfTopLevelItem(item))
            
            # Remove from folder items and emit signal
            del self.folder_items[folder_name]
            self.folder_deleted.emit(folder_name)
    
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