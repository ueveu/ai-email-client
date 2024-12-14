"""
Service for managing application-wide keyboard shortcuts.
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QSettings, QObject, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
import json
from typing import Dict, Optional
from utils.logger import logger

class ShortcutService(QObject):
    """Service for managing application keyboard shortcuts."""
    
    # Signal emitted when a shortcut is triggered
    shortcut_triggered = pyqtSignal(str)  # Emits action name
    
    # Default shortcuts
    DEFAULT_SHORTCUTS = {
        # Application shortcuts
        'app_settings': 'Ctrl+,',
        'app_quit': 'Ctrl+Q',
        'app_help': 'F1',
        
        # Email operations
        'email_compose': 'Ctrl+N',
        'email_reply': 'Ctrl+R',
        'email_reply_all': 'Ctrl+Shift+R',
        'email_forward': 'Ctrl+F',
        'email_send': 'Ctrl+Return',
        'email_save_draft': 'Ctrl+S',
        'email_delete': 'Delete',
        'email_mark_read': 'Ctrl+M',
        'email_mark_unread': 'Ctrl+U',
        'email_flag': 'Ctrl+Shift+F',
        
        # Navigation
        'nav_next_email': 'J',
        'nav_prev_email': 'K',
        'nav_next_unread': 'N',
        'nav_prev_unread': 'P',
        'nav_inbox': 'G then I',
        'nav_sent': 'G then S',
        'nav_drafts': 'G then D',
        'nav_search': 'Ctrl+F',
        
        # AI features
        'ai_generate_reply': 'Ctrl+G',
        'ai_customize_reply': 'Ctrl+E',
        'ai_next_suggestion': 'Alt+Right',
        'ai_prev_suggestion': 'Alt+Left',
        'ai_apply_suggestion': 'Alt+Return',
        
        # Attachments
        'attach_file': 'Ctrl+Shift+A',
        'attach_preview': 'Space',
        'attach_save': 'Ctrl+Shift+S',
        'attach_save_all': 'Ctrl+Shift+Alt+S',
        
        # Status bar and notifications
        'toggle_notifications': 'Ctrl+Alt+N',  # Toggle notifications panel
        'toggle_operations': 'Ctrl+Alt+O',     # Toggle operations panel
        'clear_notifications': 'Ctrl+Alt+C',   # Clear all notifications
        'cancel_operation': 'Ctrl+Alt+X',      # Cancel current operation
        'toggle_status_bar': 'Ctrl+Alt+S'      # Toggle entire status bar
    }
    
    def __init__(self, parent=None):
        """Initialize the shortcut service."""
        super().__init__(parent)
        self.settings = QSettings('AI Email Assistant', 'Settings')
        self.shortcuts: Dict[str, QShortcut] = {}
        self.main_window = None
    
    def initialize(self, main_window):
        """
        Initialize shortcuts for the main window.
        
        Args:
            main_window: The application's main window
        """
        self.main_window = main_window
        self.load_shortcuts()
        self.create_shortcuts()
    
    def load_shortcuts(self):
        """Load shortcut configurations from settings."""
        try:
            # Load custom shortcuts or use defaults
            self.shortcut_configs = self.settings.value(
                'shortcuts/custom',
                self.DEFAULT_SHORTCUTS
            )
            
            # Validate loaded shortcuts
            if not isinstance(self.shortcut_configs, dict):
                logger.warning("Invalid shortcut configuration, using defaults")
                self.shortcut_configs = self.DEFAULT_SHORTCUTS.copy()
            
            logger.info("Loaded keyboard shortcuts")
            
        except Exception as e:
            logger.error(f"Error loading shortcuts: {str(e)}")
            self.shortcut_configs = self.DEFAULT_SHORTCUTS.copy()
    
    def create_shortcuts(self):
        """Create QShortcut objects for all configured shortcuts."""
        if not self.main_window:
            logger.error("Cannot create shortcuts: main window not set")
            return
        
        try:
            # Clear existing shortcuts
            for shortcut in self.shortcuts.values():
                shortcut.setEnabled(False)
                shortcut.deleteLater()
            self.shortcuts.clear()
            
            # Create new shortcuts
            for action, key_sequence in self.shortcut_configs.items():
                shortcut = QShortcut(QKeySequence(key_sequence), self.main_window)
                shortcut.activated.connect(lambda a=action: self.shortcut_triggered.emit(a))
                self.shortcuts[action] = shortcut
            
            logger.info("Created keyboard shortcuts")
            
        except Exception as e:
            logger.error(f"Error creating shortcuts: {str(e)}")
    
    def update_shortcut(self, action: str, key_sequence: str):
        """
        Update a shortcut's key sequence.
        
        Args:
            action (str): The action name
            key_sequence (str): The new key sequence
        """
        try:
            # Validate key sequence
            if not QKeySequence(key_sequence).isEmpty():
                # Update configuration
                self.shortcut_configs[action] = key_sequence
                
                # Update active shortcut
                if action in self.shortcuts:
                    self.shortcuts[action].setKey(QKeySequence(key_sequence))
                
                # Save to settings
                self.settings.setValue('shortcuts/custom', self.shortcut_configs)
                self.settings.sync()
                
                logger.info(f"Updated shortcut for {action}: {key_sequence}")
            else:
                logger.warning(f"Invalid key sequence for {action}: {key_sequence}")
                
        except Exception as e:
            logger.error(f"Error updating shortcut: {str(e)}")
    
    def reset_shortcuts(self):
        """Reset all shortcuts to their default values."""
        try:
            self.shortcut_configs = self.DEFAULT_SHORTCUTS.copy()
            self.settings.setValue('shortcuts/custom', self.shortcut_configs)
            self.settings.sync()
            
            if self.main_window:
                self.create_shortcuts()
            
            logger.info("Reset all shortcuts to defaults")
            
        except Exception as e:
            logger.error(f"Error resetting shortcuts: {str(e)}")
    
    def get_shortcut(self, action: str) -> Optional[str]:
        """
        Get the key sequence for an action.
        
        Args:
            action (str): The action name
            
        Returns:
            str: The key sequence or None if not found
        """
        return self.shortcut_configs.get(action)
    
    def get_all_shortcuts(self) -> Dict[str, str]:
        """
        Get all configured shortcuts.
        
        Returns:
            Dict[str, str]: Dictionary of action names to key sequences
        """
        return self.shortcut_configs.copy()
    
    def is_shortcut_available(self, key_sequence: str, current_action: Optional[str] = None) -> bool:
        """
        Check if a key sequence is available for use.
        
        Args:
            key_sequence (str): The key sequence to check
            current_action (str, optional): The action being edited
            
        Returns:
            bool: True if the key sequence is available
        """
        for action, sequence in self.shortcut_configs.items():
            if sequence == key_sequence and action != current_action:
                return False
        return True
    
    def get_action_categories(self) -> Dict[str, list]:
        """
        Get shortcuts organized by category.
        
        Returns:
            Dict[str, list]: Dictionary of categories to lists of (action, key_sequence)
        """
        categories = {
            'Application': [],
            'Email Operations': [],
            'Navigation': [],
            'AI Features': [],
            'Attachments': [],
            'Status Bar': []  # New category for status bar shortcuts
        }
        
        for action, sequence in self.shortcut_configs.items():
            if action.startswith('app_'):
                categories['Application'].append((action, sequence))
            elif action.startswith('email_'):
                categories['Email Operations'].append((action, sequence))
            elif action.startswith('nav_'):
                categories['Navigation'].append((action, sequence))
            elif action.startswith('ai_'):
                categories['AI Features'].append((action, sequence))
            elif action.startswith('attach_'):
                categories['Attachments'].append((action, sequence))
            elif action.startswith('toggle_') or action in ['clear_notifications', 'cancel_operation']:
                categories['Status Bar'].append((action, sequence))
        
        return categories
    
    def get_action_description(self, action: str) -> str:
        """
        Get a human-readable description of an action.
        
        Args:
            action (str): The action name
            
        Returns:
            str: Human-readable description
        """
        descriptions = {
            # Application
            'app_settings': 'Open Settings Dialog',
            'app_quit': 'Quit Application',
            'app_help': 'Show Help',
            
            # Email operations
            'email_compose': 'Compose New Email',
            'email_reply': 'Reply to Email',
            'email_reply_all': 'Reply All',
            'email_forward': 'Forward Email',
            'email_send': 'Send Email',
            'email_save_draft': 'Save as Draft',
            'email_delete': 'Delete Email',
            'email_mark_read': 'Mark as Read',
            'email_mark_unread': 'Mark as Unread',
            'email_flag': 'Flag Email',
            
            # Navigation
            'nav_next_email': 'Next Email',
            'nav_prev_email': 'Previous Email',
            'nav_next_unread': 'Next Unread Email',
            'nav_prev_unread': 'Previous Unread Email',
            'nav_inbox': 'Go to Inbox',
            'nav_sent': 'Go to Sent',
            'nav_drafts': 'Go to Drafts',
            'nav_search': 'Search Emails',
            
            # AI features
            'ai_generate_reply': 'Generate AI Reply',
            'ai_customize_reply': 'Customize AI Reply',
            'ai_next_suggestion': 'Next AI Suggestion',
            'ai_prev_suggestion': 'Previous AI Suggestion',
            'ai_apply_suggestion': 'Apply Selected Suggestion',
            
            # Attachments
            'attach_file': 'Attach File',
            'attach_preview': 'Preview Attachment',
            'attach_save': 'Save Attachment',
            'attach_save_all': 'Save All Attachments',
            
            # Status bar
            'toggle_notifications': 'Toggle Notifications Panel',
            'toggle_operations': 'Toggle Operations Panel',
            'clear_notifications': 'Clear All Notifications',
            'cancel_operation': 'Cancel Current Operation',
            'toggle_status_bar': 'Toggle Status Bar'
        }
        
        return descriptions.get(action, action.replace('_', ' ').title()) 