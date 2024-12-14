from PyQt6.QtWidgets import QSplashScreen
from PyQt6.QtCore import Qt
from resources import Resources

class SplashScreen(QSplashScreen):
    """
    Application splash screen shown during startup.
    """
    
    def __init__(self):
        """Initialize the splash screen with the application splash image."""
        super().__init__(Resources.get_splash_image())
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
    
    def show_message(self, message: str):
        """
        Show a status message on the splash screen.
        
        Args:
            message (str): Message to display
        """
        self.showMessage(
            message,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
            Qt.GlobalColor.white
        ) 