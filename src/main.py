"""
Main entry point for the email client application.
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow
from utils.logger import logger

def main():
    """Main application entry point."""
    try:
        # Create application
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        # Start event loop
        sys.exit(app.exec())
        
    except Exception as e:
        logger.critical(f"Application startup error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 