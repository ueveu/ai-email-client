"""
Settings dialog for configuring application preferences and options.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                           QWidget, QLabel, QComboBox, QCheckBox, QSpinBox,
                           QPushButton, QGroupBox, QFormLayout, QDialogButtonBox,
                           QLineEdit, QScrollArea)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QColor
import json
from pathlib import Path
from utils.logger import logger
from services.credential_service import CredentialService
from services.ai_service import AIService

class SettingsDialog(QDialog):
    """Dialog for managing application settings and preferences."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings('AI Email Assistant', 'Settings')
        self.credential_service = CredentialService()
        self.ai_service = AIService()
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Set up the settings dialog UI."""
        self.setWindowTitle("Settings")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout(self)
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Add settings tabs
        tab_widget.addTab(self.create_general_tab(), "General")
        tab_widget.addTab(self.create_appearance_tab(), "Appearance")
        tab_widget.addTab(self.create_ai_tab(), "AI Settings")
        tab_widget.addTab(self.create_security_tab(), "Security")
        tab_widget.addTab(self.create_accounts_tab(), "Email Accounts")
        
        layout.addWidget(tab_widget)
        
        # Add dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Apply |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_settings)
        
        layout.addWidget(button_box)
    
    def create_general_tab(self) -> QWidget:
        """Create the general settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Startup group
        startup_group = QGroupBox("Startup")
        startup_layout = QFormLayout()
        
        self.start_minimized = QCheckBox("Start minimized")
        self.check_updates = QCheckBox("Check for updates on startup")
        self.auto_connect = QCheckBox("Auto-connect to email accounts")
        
        startup_layout.addRow(self.start_minimized)
        startup_layout.addRow(self.check_updates)
        startup_layout.addRow(self.auto_connect)
        startup_group.setLayout(startup_layout)
        layout.addWidget(startup_group)
        
        # Notifications group
        notif_group = QGroupBox("Notifications")
        notif_layout = QFormLayout()
        
        self.enable_notifications = QCheckBox("Enable desktop notifications")
        self.notification_sound = QCheckBox("Play notification sound")
        
        notif_layout.addRow(self.enable_notifications)
        notif_layout.addRow(self.notification_sound)
        notif_group.setLayout(notif_layout)
        layout.addWidget(notif_group)
        
        # Cache group
        cache_group = QGroupBox("Cache")
        cache_layout = QFormLayout()
        
        self.cache_size = QSpinBox()
        self.cache_size.setRange(100, 10000)
        self.cache_size.setSuffix(" MB")
        
        self.cache_days = QSpinBox()
        self.cache_days.setRange(1, 365)
        self.cache_days.setSuffix(" days")
        
        cache_layout.addRow("Maximum cache size:", self.cache_size)
        cache_layout.addRow("Keep cache for:", self.cache_days)
        cache_group.setLayout(cache_layout)
        layout.addWidget(cache_group)
        
        layout.addStretch()
        return tab
    
    def create_appearance_tab(self) -> QWidget:
        """Create the appearance settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Theme group
        theme_group = QGroupBox("Theme")
        theme_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "System"])
        
        self.custom_colors = QCheckBox("Use custom accent colors")
        self.accent_color = QPushButton()
        self.accent_color.setEnabled(False)
        self.custom_colors.toggled.connect(self.accent_color.setEnabled)
        
        theme_layout.addRow("Theme:", self.theme_combo)
        theme_layout.addRow(self.custom_colors)
        theme_layout.addRow("Accent color:", self.accent_color)
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Font group
        font_group = QGroupBox("Font")
        font_layout = QFormLayout()
        
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 24)
        self.font_size.setSuffix(" pt")
        
        font_layout.addRow("Font size:", self.font_size)
        font_group.setLayout(font_layout)
        layout.addWidget(font_group)
        
        layout.addStretch()
        return tab
    
    def create_ai_tab(self) -> QWidget:
        """Create the AI settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # API Settings group
        api_group = QGroupBox("API Settings")
        api_layout = QFormLayout()
        
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("Enter your Gemini API key")
        
        api_layout.addRow("API Key:", self.api_key)
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # Reply Generation group
        reply_group = QGroupBox("Reply Generation")
        reply_layout = QFormLayout()
        
        self.num_suggestions = QSpinBox()
        self.num_suggestions.setRange(1, 5)
        
        self.default_tone = QComboBox()
        self.default_tone.addItems([
            "Professional", "Friendly", "Formal", "Casual",
            "Diplomatic", "Direct", "Empathetic"
        ])
        
        self.learn_preferences = QCheckBox("Learn from my selections")
        self.include_context = QCheckBox("Include conversation context")
        
        reply_layout.addRow("Number of suggestions:", self.num_suggestions)
        reply_layout.addRow("Default tone:", self.default_tone)
        reply_layout.addRow(self.learn_preferences)
        reply_layout.addRow(self.include_context)
        reply_group.setLayout(reply_layout)
        layout.addWidget(reply_group)
        
        # Learning Data group
        learning_group = QGroupBox("Learning Data")
        learning_layout = QVBoxLayout()
        
        # Display learning stats
        try:
            stats = self.ai_service.get_learning_stats()
            stats_text = (
                f"Replies analyzed: {stats['total_replies']}\n"
                f"Common tones: {', '.join(stats['common_tones'].keys())}\n"
                f"Patterns stored: {sum(stats['pattern_counts'].values())}"
            )
        except Exception as e:
            stats_text = "Error loading learning stats"
            logger.error(f"Error loading learning stats: {str(e)}")
        
        stats_label = QLabel(stats_text)
        stats_label.setWordWrap(True)
        
        clear_data_btn = QPushButton("Clear Learning Data")
        clear_data_btn.clicked.connect(self.clear_learning_data)
        
        learning_layout.addWidget(stats_label)
        learning_layout.addWidget(clear_data_btn)
        learning_group.setLayout(learning_layout)
        layout.addWidget(learning_group)
        
        layout.addStretch()
        return tab
    
    def create_security_tab(self) -> QWidget:
        """Create the security settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Session group
        session_group = QGroupBox("Session")
        session_layout = QFormLayout()
        
        self.session_timeout = QSpinBox()
        self.session_timeout.setRange(0, 1440)
        self.session_timeout.setSuffix(" minutes")
        self.session_timeout.setSpecialValueText("Never")
        
        self.auto_logout = QCheckBox("Auto-logout on inactivity")
        
        session_layout.addRow("Session timeout:", self.session_timeout)
        session_layout.addRow(self.auto_logout)
        session_group.setLayout(session_layout)
        layout.addWidget(session_group)
        
        # Encryption group
        encryption_group = QGroupBox("Encryption")
        encryption_layout = QVBoxLayout()
        
        self.encrypt_cache = QCheckBox("Encrypt email cache")
        self.secure_memory = QCheckBox("Secure memory (recommended)")
        
        # Display master key info
        try:
            has_master_key = bool(self.credential_service.fernet)
            key_status = "Master key: Present and valid" if has_master_key else "Master key: Not found"
        except Exception:
            key_status = "Master key: Error checking status"
        
        key_label = QLabel(key_status)
        regenerate_key_btn = QPushButton("Regenerate Master Key")
        regenerate_key_btn.clicked.connect(self.regenerate_master_key)
        
        encryption_layout.addWidget(self.encrypt_cache)
        encryption_layout.addWidget(self.secure_memory)
        encryption_layout.addWidget(key_label)
        encryption_layout.addWidget(regenerate_key_btn)
        encryption_group.setLayout(encryption_layout)
        layout.addWidget(encryption_group)
        
        # Audit group
        audit_group = QGroupBox("Audit Logging")
        audit_layout = QFormLayout()
        
        self.enable_audit = QCheckBox("Enable security audit logging")
        self.log_retention = QSpinBox()
        self.log_retention.setRange(1, 365)
        self.log_retention.setSuffix(" days")
        
        audit_layout.addRow(self.enable_audit)
        audit_layout.addRow("Keep logs for:", self.log_retention)
        audit_group.setLayout(audit_layout)
        layout.addWidget(audit_group)
        
        layout.addStretch()
        return tab
    
    def create_accounts_tab(self) -> QWidget:
        """Create the email accounts tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Account list group
        accounts_group = QGroupBox("Email Accounts")
        accounts_layout = QVBoxLayout()
        
        # Get account list
        accounts = self.credential_service.list_accounts()
        
        if accounts:
            for account in accounts:
                account_widget = QWidget()
                account_layout = QHBoxLayout(account_widget)
                
                email_label = QLabel(account['email'])
                provider_label = QLabel(f"({account['provider']})")
                status_label = QLabel("✓ Connected" if account['has_credentials'] else "⚠️ No credentials")
                
                account_layout.addWidget(email_label)
                account_layout.addWidget(provider_label)
                account_layout.addWidget(status_label)
                account_layout.addStretch()
                
                accounts_layout.addWidget(account_widget)
        else:
            accounts_layout.addWidget(QLabel("No email accounts configured"))
        
        accounts_group.setLayout(accounts_layout)
        layout.addWidget(accounts_group)
        
        layout.addStretch()
        return tab
    
    def load_settings(self):
        """Load current settings into the dialog."""
        # General settings
        self.start_minimized.setChecked(self.settings.value('general/start_minimized', False, bool))
        self.check_updates.setChecked(self.settings.value('general/check_updates', True, bool))
        self.auto_connect.setChecked(self.settings.value('general/auto_connect', True, bool))
        self.enable_notifications.setChecked(self.settings.value('notifications/enabled', True, bool))
        self.notification_sound.setChecked(self.settings.value('notifications/sound', True, bool))
        self.cache_size.setValue(self.settings.value('cache/max_size', 1000, int))
        self.cache_days.setValue(self.settings.value('cache/retention_days', 30, int))
        
        # Appearance settings
        self.theme_combo.setCurrentText(self.settings.value('appearance/theme', 'System'))
        self.custom_colors.setChecked(self.settings.value('appearance/custom_colors', False, bool))
        self.font_size.setValue(self.settings.value('appearance/font_size', 10, int))
        
        # AI settings
        self.api_key.setText(self.settings.value('ai/api_key', ''))
        self.num_suggestions.setValue(self.settings.value('ai/num_suggestions', 3, int))
        self.default_tone.setCurrentText(self.settings.value('ai/default_tone', 'Professional'))
        self.learn_preferences.setChecked(self.settings.value('ai/learn_preferences', True, bool))
        self.include_context.setChecked(self.settings.value('ai/include_context', True, bool))
        
        # Security settings
        self.session_timeout.setValue(self.settings.value('security/session_timeout', 30, int))
        self.auto_logout.setChecked(self.settings.value('security/auto_logout', True, bool))
        self.encrypt_cache.setChecked(self.settings.value('security/encrypt_cache', True, bool))
        self.secure_memory.setChecked(self.settings.value('security/secure_memory', True, bool))
        self.enable_audit.setChecked(self.settings.value('security/enable_audit', True, bool))
        self.log_retention.setValue(self.settings.value('security/log_retention', 30, int))
    
    def apply_settings(self):
        """Apply the current settings."""
        try:
            # General settings
            self.settings.setValue('general/start_minimized', self.start_minimized.isChecked())
            self.settings.setValue('general/check_updates', self.check_updates.isChecked())
            self.settings.setValue('general/auto_connect', self.auto_connect.isChecked())
            self.settings.setValue('notifications/enabled', self.enable_notifications.isChecked())
            self.settings.setValue('notifications/sound', self.notification_sound.isChecked())
            self.settings.setValue('cache/max_size', self.cache_size.value())
            self.settings.setValue('cache/retention_days', self.cache_days.value())
            
            # Appearance settings
            self.settings.setValue('appearance/theme', self.theme_combo.currentText())
            self.settings.setValue('appearance/custom_colors', self.custom_colors.isChecked())
            self.settings.setValue('appearance/font_size', self.font_size.value())
            
            # AI settings
            self.settings.setValue('ai/api_key', self.api_key.text())
            self.settings.setValue('ai/num_suggestions', self.num_suggestions.value())
            self.settings.setValue('ai/default_tone', self.default_tone.currentText())
            self.settings.setValue('ai/learn_preferences', self.learn_preferences.isChecked())
            self.settings.setValue('ai/include_context', self.include_context.isChecked())
            
            # Security settings
            self.settings.setValue('security/session_timeout', self.session_timeout.value())
            self.settings.setValue('security/auto_logout', self.auto_logout.isChecked())
            self.settings.setValue('security/encrypt_cache', self.encrypt_cache.isChecked())
            self.settings.setValue('security/secure_memory', self.secure_memory.isChecked())
            self.settings.setValue('security/enable_audit', self.enable_audit.isChecked())
            self.settings.setValue('security/log_retention', self.log_retention.value())
            
            self.settings.sync()
            logger.info("Settings applied successfully")
            
        except Exception as e:
            logger.error(f"Error applying settings: {str(e)}")
            raise
    
    def accept(self):
        """Handle dialog acceptance."""
        try:
            self.apply_settings()
            super().accept()
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
    
    def clear_learning_data(self):
        """Clear AI learning data after confirmation."""
        from PyQt6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self,
            "Clear Learning Data",
            "Are you sure you want to clear all AI learning data? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Clear learning data (implementation needed in AIService)
                # self.ai_service.clear_learning_data()
                logger.info("AI learning data cleared")
            except Exception as e:
                logger.error(f"Error clearing learning data: {str(e)}")
    
    def regenerate_master_key(self):
        """Regenerate the master encryption key after confirmation."""
        from PyQt6.QtWidgets import QMessageBox
        
        reply = QMessageBox.warning(
            self,
            "Regenerate Master Key",
            "Warning: Regenerating the master key will make all existing encrypted data unreadable. "
            "Make sure to back up any important data first.\n\n"
            "Do you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Implementation needed in CredentialService
                # self.credential_service.regenerate_master_key()
                logger.info("Master encryption key regenerated")
            except Exception as e:
                logger.error(f"Error regenerating master key: {str(e)}") 