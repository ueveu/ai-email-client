"""
Service for managing application themes and styling.
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import QSettings, Qt
import json
from pathlib import Path
from utils.logger import logger

class ThemeService:
    """Service for managing application themes and styling."""
    
    # Default color schemes
    LIGHT_THEME = {
        'window': '#FFFFFF',
        'window_text': '#000000',
        'base': '#FFFFFF',
        'alternate_base': '#F7F7F7',
        'text': '#000000',
        'button': '#F0F0F0',
        'button_text': '#000000',
        'bright_text': '#FFFFFF',
        'link': '#0000FF',
        'highlight': '#308CC6',
        'highlight_text': '#FFFFFF',
        'light': '#E0E0E0',
        'midlight': '#D0D0D0',
        'mid': '#A0A0A0',
        'dark': '#606060',
        'shadow': '#404040'
    }
    
    DARK_THEME = {
        'window': '#2B2B2B',
        'window_text': '#FFFFFF',
        'base': '#323232',
        'alternate_base': '#383838',
        'text': '#FFFFFF',
        'button': '#454545',
        'button_text': '#FFFFFF',
        'bright_text': '#FFFFFF',
        'link': '#5C9FFF',
        'highlight': '#2D7FC9',
        'highlight_text': '#FFFFFF',
        'light': '#505050',
        'midlight': '#606060',
        'mid': '#808080',
        'dark': '#A0A0A0',
        'shadow': '#202020'
    }
    
    def __init__(self):
        """Initialize the theme service."""
        self.settings = QSettings('AI Email Assistant', 'Settings')
        self.custom_themes = self._load_custom_themes()
    
    def apply_theme(self, theme_name: str, custom_colors: bool = False):
        """
        Apply the specified theme to the application.
        
        Args:
            theme_name (str): Name of the theme ('Light', 'Dark', or 'System')
            custom_colors (bool): Whether to use custom accent colors
        """
        try:
            if theme_name == 'System':
                # Use system theme (implementation depends on platform)
                self._apply_system_theme()
                return
            
            # Get color scheme
            colors = self.LIGHT_THEME if theme_name == 'Light' else self.DARK_THEME
            
            # Apply custom colors if enabled
            if custom_colors:
                custom_scheme = self.settings.value('appearance/custom_colors_scheme', {})
                colors.update(custom_scheme)
            
            # Create and apply palette
            palette = self._create_palette(colors)
            QApplication.instance().setPalette(palette)
            
            # Apply additional styling
            self._apply_stylesheet(theme_name, colors)
            
            logger.info(f"Applied theme: {theme_name}")
            
        except Exception as e:
            logger.error(f"Error applying theme: {str(e)}")
    
    def _create_palette(self, colors: dict) -> QPalette:
        """Create QPalette from color scheme."""
        palette = QPalette()
        
        # Map colors to palette roles
        role_map = {
            QPalette.ColorRole.Window: 'window',
            QPalette.ColorRole.WindowText: 'window_text',
            QPalette.ColorRole.Base: 'base',
            QPalette.ColorRole.AlternateBase: 'alternate_base',
            QPalette.ColorRole.Text: 'text',
            QPalette.ColorRole.Button: 'button',
            QPalette.ColorRole.ButtonText: 'button_text',
            QPalette.ColorRole.BrightText: 'bright_text',
            QPalette.ColorRole.Link: 'link',
            QPalette.ColorRole.Highlight: 'highlight',
            QPalette.ColorRole.HighlightedText: 'highlight_text',
            QPalette.ColorRole.Light: 'light',
            QPalette.ColorRole.Midlight: 'midlight',
            QPalette.ColorRole.Mid: 'mid',
            QPalette.ColorRole.Dark: 'dark',
            QPalette.ColorRole.Shadow: 'shadow'
        }
        
        # Set colors for all roles
        for role, color_key in role_map.items():
            if color_key in colors:
                palette.setColor(role, QColor(colors[color_key]))
        
        return palette
    
    def _apply_stylesheet(self, theme_name: str, colors: dict):
        """Apply additional styling through stylesheet."""
        # Base stylesheet
        stylesheet = f"""
        QWidget {{
            background-color: {colors['window']};
            color: {colors['window_text']};
        }}
        
        QScrollBar:vertical {{
            background: {colors['base']};
            width: 12px;
            margin: 0px;
        }}
        
        QScrollBar::handle:vertical {{
            background: {colors['mid']};
            min-height: 20px;
            border-radius: 6px;
        }}
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        QToolTip {{
            background-color: {colors['base']};
            color: {colors['text']};
            border: 1px solid {colors['mid']};
            padding: 4px;
        }}
        
        QPushButton {{
            background-color: {colors['button']};
            color: {colors['button_text']};
            border: 1px solid {colors['mid']};
            padding: 4px 8px;
            border-radius: 4px;
        }}
        
        QPushButton:hover {{
            background-color: {colors['highlight']};
            color: {colors['highlight_text']};
        }}
        
        QLineEdit, QTextEdit, QComboBox {{
            background-color: {colors['base']};
            color: {colors['text']};
            border: 1px solid {colors['mid']};
            padding: 4px;
            border-radius: 4px;
        }}
        
        QTabWidget::pane {{
            border: 1px solid {colors['mid']};
        }}
        
        QTabBar::tab {{
            background-color: {colors['button']};
            color: {colors['button_text']};
            padding: 6px 12px;
            border: 1px solid {colors['mid']};
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {colors['window']};
            border-bottom: none;
            margin-bottom: -1px;
        }}
        """
        
        # Apply stylesheet
        QApplication.instance().setStyleSheet(stylesheet)
    
    def _apply_system_theme(self):
        """Apply the system theme."""
        # Reset palette and stylesheet
        QApplication.instance().setPalette(QPalette())
        QApplication.instance().setStyleSheet("")
    
    def save_custom_colors(self, colors: dict):
        """
        Save custom color scheme.
        
        Args:
            colors (dict): Dictionary of custom colors
        """
        try:
            self.settings.setValue('appearance/custom_colors_scheme', colors)
            self.settings.sync()
            logger.info("Saved custom color scheme")
            
        except Exception as e:
            logger.error(f"Error saving custom colors: {str(e)}")
    
    def _load_custom_themes(self) -> dict:
        """Load custom theme definitions."""
        try:
            themes_path = Path.home() / '.ai_email_assistant' / 'themes'
            themes_path.mkdir(parents=True, exist_ok=True)
            
            themes = {}
            for theme_file in themes_path.glob('*.json'):
                with open(theme_file, 'r') as f:
                    theme_data = json.load(f)
                    themes[theme_file.stem] = theme_data
            
            return themes
            
        except Exception as e:
            logger.error(f"Error loading custom themes: {str(e)}")
            return {}
    
    def get_current_theme(self) -> str:
        """Get the name of the currently active theme."""
        return self.settings.value('appearance/theme', 'System')
    
    def is_dark_theme(self) -> bool:
        """Check if a dark theme is currently active."""
        current_theme = self.get_current_theme()
        if current_theme == 'Dark':
            return True
        elif current_theme == 'System':
            # Check system theme (implementation depends on platform)
            return self._is_system_theme_dark()
        return False
    
    def _is_system_theme_dark(self) -> bool:
        """Check if the system theme is dark."""
        # This is a simplified implementation
        # In a real application, this would need platform-specific checks
        palette = QApplication.instance().palette()
        bg_color = palette.color(QPalette.ColorRole.Window)
        return bg_color.lightness() < 128
    
    def export_theme(self, name: str, colors: dict, path: str):
        """
        Export a theme to a JSON file.
        
        Args:
            name (str): Theme name
            colors (dict): Color scheme
            path (str): Export path
        """
        try:
            theme_data = {
                'name': name,
                'colors': colors,
                'metadata': {
                    'version': '1.0',
                    'type': 'dark' if self.is_dark_theme() else 'light'
                }
            }
            
            with open(path, 'w') as f:
                json.dump(theme_data, f, indent=2)
                
            logger.info(f"Exported theme '{name}' to {path}")
            
        except Exception as e:
            logger.error(f"Error exporting theme: {str(e)}")
            raise
    
    def import_theme(self, path: str) -> dict:
        """
        Import a theme from a JSON file.
        
        Args:
            path (str): Path to theme file
            
        Returns:
            dict: Imported theme data
        """
        try:
            with open(path, 'r') as f:
                theme_data = json.load(f)
            
            # Validate theme data
            required_keys = {'name', 'colors', 'metadata'}
            if not all(key in theme_data for key in required_keys):
                raise ValueError("Invalid theme file format")
            
            # Save to custom themes
            name = theme_data['name']
            self.custom_themes[name] = theme_data
            
            # Save to themes directory
            themes_dir = Path.home() / '.ai_email_assistant' / 'themes'
            theme_path = themes_dir / f"{name}.json"
            with open(theme_path, 'w') as f:
                json.dump(theme_data, f, indent=2)
            
            logger.info(f"Imported theme '{name}' from {path}")
            return theme_data
            
        except Exception as e:
            logger.error(f"Error importing theme: {str(e)}")
            raise 