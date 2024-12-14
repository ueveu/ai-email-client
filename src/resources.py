from pathlib import Path
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QBrush, QLinearGradient
from PyQt6.QtCore import QSize, Qt, QPointF

class Resources:
    """
    Manages application resources including icons, images, and branding elements.
    """
    
    # Application metadata
    APP_NAME = "AI Email Assistant"
    APP_VERSION = "1.0.0"
    ORGANIZATION_NAME = "AI Email Assistant"
    ORGANIZATION_DOMAIN = "ai-email-assistant.app"
    
    # Asset paths
    ASSETS_DIR = Path(__file__).parent / "assets"
    ICON_PATH = ASSETS_DIR / "icon.png"
    SPLASH_IMAGE_PATH = ASSETS_DIR / "splash.png"
    
    # Icon sizes
    WINDOW_ICON_SIZE = QSize(64, 64)
    TOOLBAR_ICON_SIZE = QSize(24, 24)
    TRAY_ICON_SIZE = QSize(16, 16)
    
    @classmethod
    def init(cls):
        """Initialize application resources."""
        # Create assets directory if it doesn't exist
        cls.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Generate default icons if they don't exist
        if not cls.ICON_PATH.exists():
            cls._generate_default_icon()
        if not cls.SPLASH_IMAGE_PATH.exists():
            cls._generate_default_splash()
    
    @classmethod
    def get_app_icon(cls) -> QIcon:
        """Get the main application icon."""
        return QIcon(str(cls.ICON_PATH))
    
    @classmethod
    def get_splash_image(cls) -> QPixmap:
        """Get the splash screen image."""
        return QPixmap(str(cls.SPLASH_IMAGE_PATH))
    
    @classmethod
    def _generate_default_icon(cls):
        """Generate a default application icon if none exists."""
        # Create a 64x64 icon
        icon = QPixmap(64, 64)
        icon.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(icon)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background circle
        painter.setBrush(QBrush(QColor("#2196F3")))  # Material Blue
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 60, 60)
        
        # Draw text
        painter.setPen(QColor("white"))
        font = QFont("Arial", 24, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(icon.rect(), Qt.AlignmentFlag.AlignCenter, "AI")
        
        painter.end()
        
        # Save the icon
        icon.save(str(cls.ICON_PATH))
    
    @classmethod
    def _generate_default_splash(cls):
        """Generate a default splash screen image if none exists."""
        # Create a 400x300 splash image
        splash = QPixmap(400, 300)
        
        # Create gradient background
        gradient = QLinearGradient(0, 0, 400, 300)  # Use float coordinates
        gradient.setColorAt(0, QColor("#1976D2"))  # Dark Blue
        gradient.setColorAt(1, QColor("#64B5F6"))  # Light Blue
        
        painter = QPainter(splash)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        painter.fillRect(splash.rect(), QBrush(gradient))
        
        # Draw application name
        painter.setPen(QColor("white"))
        font = QFont("Arial", 24, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(splash.rect(), Qt.AlignmentFlag.AlignCenter, cls.APP_NAME)
        
        # Draw version
        font.setPointSize(12)
        painter.setFont(font)
        version_rect = splash.rect()
        version_rect.setTop(version_rect.center().y() + 20)
        painter.drawText(version_rect, Qt.AlignmentFlag.AlignHCenter, f"Version {cls.APP_VERSION}")
        
        painter.end()
        
        # Save the splash image
        splash.save(str(cls.SPLASH_IMAGE_PATH)) 