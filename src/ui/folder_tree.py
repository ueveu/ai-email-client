from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import pyqtSignal

class FolderTree(QTreeWidget):
    """
    Tree widget for displaying email folders in a hierarchical structure.
    Supports folder selection and displays unread message counts.
    """
    
    folder_selected = pyqtSignal(str)  # Signal emitted when folder is selected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_folder = None
        self.folder_items = {}  # Maps folder names to tree items
    
    def setup_ui(self):
        """Initialize the UI components."""
        self.setHeaderLabels(["Folder", "Unread"])
        self.setColumnCount(2)
        self.itemClicked.connect(self._on_item_clicked)
    
    def update_folders(self, folders, status_data=None):
        """
        Update the folder tree with the latest folder list and status.
        
        Args:
            folders (list): List of folder dictionaries from EmailManager
            status_data (dict): Optional dict mapping folder names to their status
        """
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
                    root_items[root_name] = QTreeWidgetItem([root_name, ""])
                    self.addTopLevelItem(root_items[root_name])
            
            # Create the folder item
            if len(path_parts) > 1:
                # This is a subfolder
                item = QTreeWidgetItem([path_parts[-1], ""])
                root_items[path_parts[0]].addChild(item)
            else:
                # This is a root folder
                item = QTreeWidgetItem([folder['name'], ""])
                self.addTopLevelItem(item)
            
            # Store reference to the item
            self.folder_items[folder['name']] = item
            
            # Update status if provided
            if status_data and folder['name'] in status_data:
                self.update_folder_status(folder['name'], status_data[folder['name']])
        
        # Expand all items
        self.expandAll()
    
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
            item.setText(1, str(unread) if unread > 0 else "")
    
    def select_folder(self, folder_name):
        """
        Programmatically select a folder.
        
        Args:
            folder_name (str): Name of the folder to select
        """
        if folder_name in self.folder_items:
            item = self.folder_items[folder_name]
            self.setCurrentItem(item)
            self.current_folder = folder_name
    
    def _on_item_clicked(self, item, column):
        """Handle folder selection."""
        # Get the full folder path
        path_parts = []
        current = item
        while current is not None:
            path_parts.insert(0, current.text(0))
            current = current.parent()
        
        folder_path = '/'.join(path_parts)
        self.current_folder = folder_path
        self.folder_selected.emit(folder_path) 