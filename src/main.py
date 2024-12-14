#!/usr/bin/env python3

import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer
from ui.main_window import MainWindow
from ui.splash_screen import SplashScreen
from ui.api_key_dialog import ApiKeyDialog
from resources import Resources
from config import Config

def check_api_key(config, window) -> bool:
    """
    Check if API key exists and prompt user if it doesn't.
    
    Args:
        config: Application configuration
        window: Main window for dialog parent
    
    Returns:
        bool: True if API key is available, False otherwise
    """
    # Check if API key exists
    api_key = config.get_api_key()
    if not api_key:
        # Show dialog to get API key
        api_key = ApiKeyDialog.get_api_key(window)
        if api_key:
            # Store the API key
            config.credential_manager.store_api_key("gemini", api_key)
            return True
        else:
            # User cancelled
            QMessageBox.critical(
                window,
                "API Key Required",
                "The application requires a Gemini API key to function. "
                "Please restart the application and enter a valid API key."
            )
            return False
    return True

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
    
    # Initialize configuration
    config = Config()
    
    # Function to finish splash screen and show main window
    def finish_splash():
        splash.finish(window)
        # Check for API key
        if check_api_key(config, window):
            window.show()
        else:
            app.quit()
    
    # Simulate startup delay and show some messages
    splash.show_message("Loading resources...")
    QTimer.singleShot(1000, lambda: splash.show_message("Initializing..."))
    QTimer.singleShot(2000, lambda: splash.show_message("Starting application..."))
    QTimer.singleShot(3000, finish_splash)
    
    # Start the event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 