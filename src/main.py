#!/usr/bin/env python3

import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    """
    Main entry point of the application.
    Initializes the Qt application and shows the main window.
    """
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("AI Email Assistant")
    app.setApplicationVersion("1.0.0")
    
    # Create and show the main window
    window = MainWindow()
    window.show()
    
    # Start the event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 