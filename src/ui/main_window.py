from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                           QTabWidget, QMenuBar, QInputDialog, QLineEdit, QMessageBox,
                           QDialog, QLabel, QPushButton, QHBoxLayout, QApplication)
from PyQt6.QtCore import Qt, QTimer
from ui.email_accounts_tab import EmailAccountsTab
from ui.email_analysis_tab import EmailAnalysisTab
from ui.settings_dialog import SettingsDialog
from resources import Resources
from config import Config
import os
import sys
import google.generativeai as genai

class MainWindow(QMainWindow):
    """
    Main application window that contains all UI elements and manages
    the overall application layout.
    """
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Initialize config
        self.config = Config()
        if "providers" not in self.config.settings:
            self.config.settings["providers"] = {}
            self.config._save_settings(self.config.settings)
        
        # Set window properties
        self.setWindowTitle("AI Email Assistant")
        self.setMinimumSize(800, 600)
        self.setWindowIcon(Resources.get_icon("app_icon.png"))
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: white;
            }
            QWidget {
                background-color: #1e1e1e;
                color: white;
            }
            QTabWidget::pane {
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                background-color: #2d2d2d;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #3d3d3d;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                min-width: 100px;
            }
            QTabBar::tab:selected {
                background-color: #3d3d3d;
                border-bottom: none;
            }
            QTabBar::tab:hover {
                background-color: #353535;
            }
            QMenuBar {
                background-color: #2d2d2d;
                color: white;
                border-bottom: 1px solid #3d3d3d;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 8px 16px;
            }
            QMenuBar::item:selected {
                background-color: #3d3d3d;
            }
            QMenu {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #3d3d3d;
            }
            QMenu::item {
                padding: 8px 16px;
            }
            QMenu::item:selected {
                background-color: #3d3d3d;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QPushButton {
                background-color: #4285f4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3367d6;
            }
            QLineEdit {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #4285f4;
            }
        """)
        
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(16)
        
        # Create menu bar
        self.setup_menu_bar()
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.email_accounts_tab = EmailAccountsTab()
        self.email_analysis_tab = EmailAnalysisTab()
        
        self.tab_widget.addTab(self.email_accounts_tab, "Email Accounts")
        self.tab_widget.addTab(self.email_analysis_tab, "Email Analysis")
        
        self.layout.addWidget(self.tab_widget)
        
        # Check API key after UI is set up
        QTimer.singleShot(0, self.check_api_key)
    
    def setup_menu_bar(self):
        """Set up the application menu bar."""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        
        # Add settings action
        settings_action = file_menu.addAction("Settings")
        settings_action.triggered.connect(self.show_settings)
        
        file_menu.addSeparator()
        
        # Add exit action
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)
    
    def show_settings(self):
        """Show the settings dialog."""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Reload configuration
            if "providers" in self.config.settings:
                provider_config = self.config.settings["providers"].get("Gemini 1.5 Flash (Recommended)", {})
                if not provider_config.get("api_key"):
                    QTimer.singleShot(0, self.check_api_key)
    
    def show_about(self):
        """Show the about dialog."""
        QMessageBox.about(
            self,
            "About AI Email Assistant",
            "AI Email Assistant\n\n"
            "A desktop application for managing emails with AI assistance.\n\n"
            "Version: 1.0.0"
        )
    
    def check_api_key(self) -> bool:
        """
        Check if Gemini API key is set and prompt user if not.
        
        Returns:
            bool: True if valid API key is set, False otherwise
        """
        # Show settings dialog if no API key is configured
        provider_config = self.config.settings.get("providers", {}).get("Gemini 1.5 Flash (Recommended)", {})
        if not provider_config.get("api_key"):
            QMessageBox.information(
                self,
                "API Key Required",
                "To use the AI Email Assistant, you need to configure your Gemini API key.\n\n"
                "Click OK to open the settings dialog and configure your API key."
            )
            dialog = SettingsDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Check if API key was configured
                provider_config = self.config.settings.get("providers", {}).get("Gemini 1.5 Flash (Recommended)", {})
                if provider_config.get("api_key"):
                    return True
                else:
                    QMessageBox.critical(
                        self,
                        "API Key Required",
                        "No API key was configured. Some features may not work properly."
                    )
                    return False
            else:
                QMessageBox.critical(
                    self,
                    "API Key Required",
                    "No API key was configured. Some features may not work properly."
                )
                return False
        
        return True
    
    def save_config(self):
        """Save the current configuration."""
        self.config._save_settings(self.config.settings)