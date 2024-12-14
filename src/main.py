#!/usr/bin/env python3

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from utils.logger import logger
from utils.error_handler import handle_errors

# Create Qt application first
app = QApplication(sys.argv)

# Import UI modules after QApplication is created
from ui.main_window import MainWindow

@handle_errors
def main():
    """Main application entry point."""
    try:
        # Set application style
        app.setStyle('Fusion')
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        # Start application event loop
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Application startup error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 