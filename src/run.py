#!/usr/bin/env python3

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Configure logging first
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('ai-email-client')

def run_app(debug=True):
    """
    Run the email client application
    
    Args:
        debug: Enable debug mode if True
    """
    try:
        # Set debug environment variables
        if debug:
            os.environ['QT_DEBUG_PLUGINS'] = '1'
            os.environ['PYTHONVERBOSE'] = '1'
        
        # Create Qt application
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        # Import after QApplication creation
        from ui.main_window import MainWindow
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        # Log startup success
        logger.info("Application started successfully")
        
        # Start event loop
        return app.exec()
        
    except Exception as e:
        logger.critical(f"Application startup failed: {str(e)}", exc_info=True)
        return 1

if __name__ == '__main__':
    # Parse command line arguments
    debug_mode = '--debug' in sys.argv
    
    if debug_mode:
        logger.info("Starting application in debug mode")
    
    sys.exit(run_app(debug=debug_mode)) 