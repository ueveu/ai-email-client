from PyQt6.QtGui import QIcon
import os

class Resources:
    """Resource manager for the application."""
    
    APP_NAME = "AI Email Assistant"
    ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
    
    @classmethod
    def get_icon(cls, icon_name: str) -> QIcon:
        """
        Get an icon from the assets directory.
        
        Args:
            icon_name: Name of the icon file
            
        Returns:
            QIcon: The icon
        """
        icon_path = os.path.join(cls.ASSETS_DIR, icon_name)
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        else:
            print(f"Warning: Icon not found: {icon_path}")
            return QIcon()