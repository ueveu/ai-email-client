#!/usr/bin/env python3

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from utils.logger import logger
from utils.error_handler import handle_errors, ErrorCollection, error_handler
import traceback
from services.api_key_service import APIKeyService

def setup_debug_mode():
    """Configure application for debug mode."""
    try:
        # Enable Qt debug output
        os.environ['QT_DEBUG_PLUGINS'] = '1'
        os.environ['PYTHONVERBOSE'] = '1'
        
        # Set maximum logging detail
        logger.setLevel('DEBUG')
        
        # Log system information
        logger.debug(f"Python version: {sys.version}")
        logger.debug(f"Qt version: {Qt.qVersion()}")
        logger.debug(f"Platform: {sys.platform}")
        logger.debug(f"Working directory: {os.getcwd()}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to setup debug mode: {str(e)}")
        return False

# Create Qt application first
app = QApplication(sys.argv)

# Import UI modules after QApplication is created
from ui.main_window import MainWindow

# Initialize the APIKeyService
api_key_service = APIKeyService()

# Store the Gemini API key
api_name = 'gemini'
api_key = 'AIzaSyB0x3FmPRdtvmwfERTf8iD0XrvJtfpjLQ0'

success = api_key_service.store_api_key(api_name, api_key)
if success:
    print("API key stored successfully.")
else:
    print("Failed to store API key.")

@handle_errors
def main():
    """Main application entry point."""
    try:
        # Check for debug mode
        debug_mode = '--debug' in sys.argv
        if debug_mode:
            logger.info("Starting application in debug mode")
            setup_debug_mode()
        
        # Set application style
        app.setStyle('Fusion')
        
        # Create error collection for startup
        startup_errors = ErrorCollection()
        
        # Create and show main window
        window = MainWindow()
        
        # Connect error handler to window
        error_handler.error_occurred.connect(window.handle_error)
        
        # Show window
        window.show()
        
        # Log successful startup
        logger.info("Application started successfully")
        if startup_errors.has_errors():
            logger.warning("Startup completed with warnings:")
            for msg in startup_errors.get_messages():
                logger.warning(f"- {msg}")
        
        # Start application event loop
        return app.exec()
        
    except Exception as e:
        logger.critical(f"Application startup error: {str(e)}")
        logger.critical(f"Traceback:\n{''.join(traceback.format_exc())}")
        return 1

if __name__ == '__main__':
    try:
        exit_code = main()
        logger.info(f"Application exiting with code: {exit_code}")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}")
        logger.critical(f"Traceback:\n{''.join(traceback.format_exc())}")
        sys.exit(1) 