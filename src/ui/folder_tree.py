from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt
from utils import logger

class FolderTree(QWidget):
    """Widget for displaying email folders in a tree structure."""
    
    folder_selected = pyqtSignal(str)  # Emitted when a folder is selected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.email_manager = None
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Folders")
        self.tree.itemClicked.connect(self.on_folder_clicked)
        layout.addWidget(self.tree)
        
    def set_email_manager(self, email_manager):
        """Set the email manager instance."""
        self.email_manager = email_manager
        
    def update_folders(self, folders: list, status_data: dict = None):
        """Update the folder tree with new folder data."""
        self.tree.clear()
        
        try:
            # Create folder hierarchy
            folder_map = {}  # Maps folder paths to tree items
            special_folders = {
                'INBOX': '📥',
                'Sent': '📤',
                'Drafts': '📝',
                'Trash': '🗑️',
                'Spam': '⚠️',
                'Archive': '📦',
                'All Mail': '📧'
            }
            
            # Sort folders to ensure parent folders are created first
            sorted_folders = sorted(folders, key=lambda f: len(f['name'].split('/')))
            
            for folder in sorted_folders:
                try:
                    folder_name = folder['name']
                    raw_name = folder.get('raw_name', folder_name)
                    delimiter = folder.get('delimiter', '/')
                    flags = folder.get('flags', [])
                    
                    # Get folder status
                    status = status_data.get(raw_name, {}) if status_data else {}
                    total = status.get('messages', 0)
                    unread = status.get('unseen', 0)
                    
                    # Split path into components
                    path_parts = folder_name.split(delimiter)
                    display_name = path_parts[-1]  # Get last part of path
                    
                    # Add appropriate icon
                    icon = ''
                    for special, emoji in special_folders.items():
                        if special.upper() in display_name.upper():
                            icon = emoji
                            break
                    if not icon:
                        icon = '📁'
                    
                    # Create display text with counts
                    if unread > 0:
                        display_text = f"{icon} {display_name} ({unread}/{total})"
                    else:
                        display_text = f"{icon} {display_name} ({total})"
                    
                    # Create tree item
                    item = QTreeWidgetItem([display_text])
                    item.setData(0, Qt.ItemDataRole.UserRole, raw_name)
                    
                    # Set tooltip with full path
                    item.setToolTip(0, folder_name)
                    
                    # Style based on flags
                    font = item.font(0)
                    if '\\Noselect' in flags:
                        font.setItalic(True)
                        item.setDisabled(True)
                    if unread > 0:
                        font.setBold(True)
                    item.setFont(0, font)
                    
                    # Find parent folder
                    if len(path_parts) > 1:
                        parent_path = delimiter.join(path_parts[:-1])
                        parent_item = folder_map.get(parent_path)
                        if parent_item:
                            parent_item.addChild(item)
                        else:
                            self.tree.addTopLevelItem(item)
                    else:
                        self.tree.addTopLevelItem(item)
                    
                    folder_map[folder_name] = item
                    
                except Exception as e:
                    logger.error(f"Error adding folder to tree: {str(e)}")
                    continue
            
            # Sort items
            self.tree.sortItems(0, Qt.SortOrder.AscendingOrder)
            
            # Expand INBOX by default
            inbox_items = self.tree.findItems('📥 INBOX', Qt.MatchFlag.MatchStartsWith)
            if inbox_items:
                inbox_items[0].setExpanded(True)
                
            logger.debug(f"Updated folder tree with {len(folders)} folders")
            
        except Exception as e:
            logger.error(f"Error updating folder tree: {str(e)}")
    
    def on_folder_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle folder selection."""
        folder_name = item.data(0, Qt.ItemDataRole.UserRole)
        if folder_name:
            self.folder_selected.emit(folder_name)
            logger.debug(f"Selected folder: {folder_name}")