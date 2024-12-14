from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QTabWidget, QWidget, QScrollArea,
                           QMessageBox)
from PyQt6.QtCore import Qt
from ai.providers import GeminiProvider
import logging

class ProviderSettingsTab(QWidget):
    """Tab for configuring an AI provider."""
    
    def __init__(self, provider, parent=None):
        super().__init__(parent)
        self.provider = provider
        self.setup_ui()
        
        # Load existing config if available
        if self.provider.provider_name in self.provider.app.config.get("providers", {}):
            self.provider.load_config(
                self.provider.app.config["providers"][self.provider.provider_name]
            )
        
    def setup_ui(self):
        """Set up the provider settings UI."""
        layout = QVBoxLayout(self)
        
        # Add description
        description = QLabel(self.provider.description)
        description.setWordWrap(True)
        description.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 12px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(description)
        
        # Add URL button if available
        if self.provider.button_action:
            url_button = QPushButton(self.provider.button_text)
            url_button.clicked.connect(self.provider.button_action)
            url_button.setStyleSheet("""
                QPushButton {
                    background-color: #4285f4;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-size: 12px;
                    margin-bottom: 16px;
                }
                QPushButton:hover {
                    background-color: #3367d6;
                }
            """)
            layout.addWidget(url_button)
            
        # Add settings
        settings_group = QWidget()
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setContentsMargins(0, 16, 0, 16)
        settings_group.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-radius: 4px;
                padding: 8px;
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
            QComboBox {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
            QComboBox:on {
                border: 1px solid #4285f4;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
        """)
        
        for setting in self.provider.settings:
            setting.render_to_layout(settings_layout)
            
        layout.addWidget(settings_group)
            
        # Add save button
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #34a853;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
                margin-top: 16px;
            }
            QPushButton:hover {
                background-color: #2d8e47;
            }
        """)
        layout.addWidget(save_button)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
    def save_settings(self):
        """Save the provider settings and test connection."""
        try:
            # Save settings
            self.provider.save_config()
            
            # Test connection
            self.provider.before_load()
            self.provider.after_load()
            
            if self.provider.model:
                QMessageBox.information(
                    self,
                    "Success",
                    "Settings saved and connection tested successfully!"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Warning",
                    "Settings saved but connection test failed.\n"
                    "Please check your settings and try again."
                )
        except Exception as e:
            logging.error(f"Error saving settings: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Error saving settings: {str(e)}"
            )

class SettingsDialog(QDialog):
    """Dialog for managing application settings."""
    
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("Settings")
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the settings dialog UI."""
        # Set dialog style
        self.setStyleSheet("""
            QDialog {
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
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QWidget#content_widget {
                background-color: #2d2d2d;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Add AI Providers tab
        providers_tab = QWidget()
        providers_layout = QVBoxLayout(providers_tab)
        providers_layout.setContentsMargins(16, 16, 16, 16)
        
        # Create provider tabs
        provider_tabs = QTabWidget()
        
        # Add Gemini provider
        gemini_provider = GeminiProvider(self.app)
        gemini_tab = ProviderSettingsTab(gemini_provider)
        provider_tabs.addTab(gemini_tab, "Gemini")
        
        # Add provider tabs to layout
        providers_layout.addWidget(provider_tabs)
        
        # Add providers tab to main tabs
        tab_widget.addTab(providers_tab, "AI Providers")
        
        # Add tab widget to dialog
        layout.addWidget(tab_widget)
        
        # Add close button
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #ea4335;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d33828;
            }
        """)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        # Set dialog size
        self.setMinimumWidth(600)
        self.setMinimumHeight(500) 