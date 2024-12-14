#!/usr/bin/env python3

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ui.main_window import MainWindow
from ui.splash_screen import SplashScreen
from resources import Resources

def main():
    """
    Main entry point of the application.
    Initializes the Qt application and shows the main window.
    """
    # Create application instance
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName(Resources.APP_NAME)
    app.setApplicationVersion(Resources.APP_VERSION)
    app.setOrganizationName(Resources.ORGANIZATION_NAME)
    app.setOrganizationDomain(Resources.ORGANIZATION_DOMAIN)
    
    # Initialize resources
    Resources.init()
    
    # Set application icon
    app.setWindowIcon(Resources.get_app_icon())
    
    # Show splash screen
    splash = SplashScreen()
    splash.show()
    
    # Create main window
    window = MainWindow()
    
    # Function to finish splash screen and show main window
    def finish_splash():
        splash.finish(window)
        window.show()
    
    # Simulate startup delay and show some messages
    splash.show_message("Loading resources...")
    QTimer.singleShot(1000, lambda: splash.show_message("Initializing..."))
    QTimer.singleShot(2000, lambda: splash.show_message("Starting application..."))
    QTimer.singleShot(3000, finish_splash)
    
    # Start the event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 