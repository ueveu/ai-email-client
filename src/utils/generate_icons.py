"""
Generate icons for the email client application.
"""

from PyQt6.QtWidgets import QApplication, QStyle
from PyQt6.QtGui import QIcon
import sys
import os

def generate_icons():
    """Generate and save icons for the application."""
    app = QApplication(sys.argv)
    style = app.style()
    
    # Define icon mappings (Qt standard icon to our custom name)
    icon_mappings = {
        'gmail': QStyle.StandardPixmap.SP_CommandLink,  # Temporary placeholder
        'outlook': QStyle.StandardPixmap.SP_CommandLink,  # Temporary placeholder
        'yahoo': QStyle.StandardPixmap.SP_CommandLink,  # Temporary placeholder
        'eye': QStyle.StandardPixmap.SP_DialogYesButton,
        'eye-slash': QStyle.StandardPixmap.SP_DialogNoButton,
        'check': QStyle.StandardPixmap.SP_DialogApplyButton,
        'error': QStyle.StandardPixmap.SP_DialogCancelButton,
        'test': QStyle.StandardPixmap.SP_BrowserReload,
        'save': QStyle.StandardPixmap.SP_DialogSaveButton,
        'cancel': QStyle.StandardPixmap.SP_DialogCancelButton
    }
    
    # Create icons directory if it doesn't exist
    icons_dir = os.path.join('resources', 'icons')
    os.makedirs(icons_dir, exist_ok=True)
    
    # Generate and save icons
    for name, standard_icon in icon_mappings.items():
        icon = style.standardIcon(standard_icon)
        icon.pixmap(32, 32).save(os.path.join(icons_dir, f"{name}.png"))
    
    print("Icons generated successfully!")

if __name__ == '__main__':
    generate_icons() 