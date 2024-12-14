#!/usr/bin/env python3

import sys
import os
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt, QTimer
from ui.main_window import MainWindow
from resources import Resources

def main():
    """Main application entry point."""
    print("Starting application...")
    
    # Create application
    app = QApplication(sys.argv)
    print("QApplication created")
    
    # Set application metadata
    app.setApplicationName(Resources.APP_NAME)
    app.setOrganizationName("AI Email Assistant")
    app.setOrganizationDomain("ai-email-assistant.app")
    print("Application metadata set")
    
    # Initialize resources
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    print(f"Initializing resources. Assets dir: {assets_dir}")
    
    # Create main window
    window = MainWindow()
    print("Main window created")
    
    # Check if window was initialized successfully
    if not hasattr(window, 'tab_widget'):
        print("Exiting due to initialization failure")
        return
    
    # Show the window
    window.show()
    print("Main window shown")
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 