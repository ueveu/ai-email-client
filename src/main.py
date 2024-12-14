#!/usr/bin/env python3

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from dotenv import load_dotenv
from ui.main_window import MainWindow
from ui.splash_screen import SplashScreen
from resources import Resources
from utils.logger import logger
from utils.error_handler import error_handler, handle_errors

# Load environment variables
load_dotenv()

# Verify environment variables
logger.logger.info("Checking environment variables...")
client_id = os.getenv("GOOGLE_CLIENT_ID")
client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
logger.logger.info(f"GOOGLE_CLIENT_ID present: {bool(client_id)}")
logger.logger.info(f"GOOGLE_CLIENT_SECRET present: {bool(client_secret)}")

@handle_errors
def initialize_app():
    """Initialize application resources and settings."""
    # Set application metadata
    app = QApplication.instance()
    app.setApplicationName(Resources.APP_NAME)
    app.setApplicationVersion(Resources.APP_VERSION)
    app.setOrganizationName(Resources.ORGANIZATION_NAME)
    app.setOrganizationDomain(Resources.ORGANIZATION_DOMAIN)
    
    # Initialize resources
    Resources.init()
    
    # Set application icon
    app.setWindowIcon(Resources.get_app_icon())

@handle_errors
def main():
    """
    Main entry point of the application.
    Initializes the Qt application and shows the main window.
    """
    try:
        # Create application instance
        app = QApplication(sys.argv)
        
        # Initialize application
        initialize_app()
        
        # Log application start
        logger.logger.info(f"Starting {Resources.APP_NAME} version {Resources.APP_VERSION}")
        
        # Show splash screen
        splash = SplashScreen()
        splash.show()
        
        # Create main window
        window = MainWindow()
        
        # Function to finish splash screen and show main window
        def finish_splash():
            splash.finish(window)
            window.show()
            logger.logger.info("Application UI initialized successfully")
        
        # Simulate startup delay and show some messages
        splash.show_message("Loading resources...")
        QTimer.singleShot(1000, lambda: splash.show_message("Initializing..."))
        QTimer.singleShot(2000, lambda: splash.show_message("Starting application..."))
        QTimer.singleShot(3000, finish_splash)
        
        # Connect error handler to main window
        error_handler.error_occurred.connect(window.handle_error)
        
        # Start the event loop
        exit_code = app.exec()
        
        # Log application exit
        logger.logger.info(f"Application exiting with code {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.log_error(e, {'context': 'Application startup'})
        raise

if __name__ == "__main__":
    sys.exit(main()) 