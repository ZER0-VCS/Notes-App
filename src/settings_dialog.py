"""
Диалог настроек приложения Notes App.
"""

import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QSpinBox, QFontComboBox, QPushButton, QGroupBox,
    QRadioButton, QButtonGroup, QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt
import json

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Диалог настроек приложения."""
    
    def __init__(self, parent=None, current_theme="light"):
        super().__init__(parent)
        self.parent_app = parent
        self.current_theme = current_theme
        self.config_path = Path.home() / ".notes_app" / "config.json"
        
        self.setWindowTitle("Настройки")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        
        # Загружаем текущие настройки
        self.load_settings()
        
        # Создаем интерфейс
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса."""
        layout = QVBoxLayout(self)
        
        # Создаем вкладки
        tabs = QTabWidget()
        
        # Вкладка "Общие"
        general_tab = self.create_general_tab()
        tabs.addTab(general_tab, "Общие")
        
        # Вкладка "Редактор"
        editor_tab = self.create_editor_tab()
        tabs.addTab(editor_tab, "Редактор")
        
        # Вкладка "Оформление"
        appearance_tab = self.create_appearance_tab()
        tabs.addTab(appearance_tab, "Оформление")
        
        layout.addWidget(tabs)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        btn_apply = QPushButton("Применить")
        btn_apply.clicked.connect(self.apply_settings)
        buttons_layout.addWidget(btn_apply)
        
        btn_ok = QPushButton("ОК")
        btn_ok.clicked.connect(self.accept_settings)
        btn_ok.setDefault(True)
        buttons_layout.addWidget(btn_ok)
        
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)
        
        layout.addLayout(buttons_layout)
    
    def create_general_tab(self):
        """Создать вкладку 'Общие'."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Группа "Автосохранение"
        autosave_group = QGroupBox("Автосохранение")
        autosave_layout = QFormLayout()
        
        self.autosave_spinbox = QSpinBox()
        self.autosave_spinbox.setRange(3, 10)
        self.autosave_spinbox.setSuffix(" сек")
        self.autosave_spinbox.setValue(self.settings.get('autosave_interval', 5))
        
        autosave_layout.addRow("Интервал:", self.autosave_spinbox)
        autosave_group.setLayout(autosave_layout)
        layout.addRow(autosave_group)
        
        # Группа "Автосинхронизация"
        autosync_group = QGroupBox("Автосинхронизация")
        autosync_layout = QFormLayout()
        
        self.autosync_spinbox = QSpinBox()
        self.autosync_spinbox.setRange(30, 300)
        self.autosync_spinbox.setSingleStep(30)
        self.autosync_spinbox.setSuffix(" сек")
        self.autosync_spinbox.setValue(self.settings.get('autosync_interval', 60))
        
        autosync_layout.addRow("Интервал:", self.autosync_spinbox)
        autosync_group.setLayout(autosync_layout)
        layout.addRow(autosync_group)
        
        return widget
    
    def create_editor_tab(self):
        """Создать вкладку 'Редактор'."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Шрифт
        self.font_combo = QFontComboBox()
        current_font = self.settings.get('editor_font', 'Arial')
        index = self.font_combo.findText(current_font)
        if index >= 0:
            self.font_combo.setCurrentIndex(index)
        layout.addRow("Шрифт:", self.font_combo)
        
        # Размер шрифта
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(8, 24)
        self.font_size_spinbox.setValue(self.settings.get('editor_font_size', 11))
        layout.addRow("Размер шрифта:", self.font_size_spinbox)
        
        return widget
    
    def create_appearance_tab(self):
        """Создать вкладку 'Оформление'."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Группа "Тема"
        theme_group = QGroupBox("Тема оформления")
        theme_layout = QVBoxLayout()
        
        self.theme_button_group = QButtonGroup()
        
        themes = [
            ("light", "Светлая"),
            ("dark", "Темная"),
            ("blue", "Голубая"),
            ("green", "Зеленая")
        ]
        
        for theme_id, theme_name in themes:
            rb = QRadioButton(theme_name)
            if theme_id == self.current_theme:
                rb.setChecked(True)
            self.theme_button_group.addButton(rb)
            rb.theme_id = theme_id  # Сохраняем ID темы
            theme_layout.addWidget(rb)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Информация
        info_label = QLabel("Примечание: Изменения темы будут применены после перезапуска приложения.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 10px; padding: 10px;")
        layout.addWidget(info_label)
        
        return widget
    
    def load_settings(self):
        """Загрузить настройки из config.json."""
        self.settings = {
            'autosave_interval': 5,
            'autosync_interval': 60,
            'editor_font': 'Arial',
            'editor_font_size': 11,
            'theme': 'light'
        }
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.settings.update(config)
                    logger.info("Настройки загружены")
        except Exception as e:
            logger.warning(f"Не удалось загрузить настройки: {e}")
    
    def save_settings(self):
        """Сохранить настройки в config.json."""
        try:
            # Получаем выбранную тему
            selected_theme = None
            for button in self.theme_button_group.buttons():
                if button.isChecked():
                    selected_theme = button.theme_id
                    break
            
            # Обновляем настройки
            self.settings['autosave_interval'] = self.autosave_spinbox.value()
            self.settings['autosync_interval'] = self.autosync_spinbox.value()
            self.settings['editor_font'] = self.font_combo.currentText()
            self.settings['editor_font_size'] = self.font_size_spinbox.value()
            if selected_theme:
                self.settings['theme'] = selected_theme
            
            # Сохраняем в файл
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            
            logger.info("Настройки сохранены")
            return True
        except Exception as e:
            logger.error(f"Не удалось сохранить настройки: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки:\n{e}")
            return False
    
    def apply_settings(self):
        """Применить настройки без закрытия диалога."""
        if self.save_settings():
            # Применяем настройки в реальном времени
            if self.parent_app:
                # Обновляем интервалы
                self.parent_app.update_intervals(
                    self.autosave_spinbox.value(),
                    self.autosync_spinbox.value()
                )
                
                # Применяем шрифт
                self.parent_app.apply_editor_font(
                    self.font_combo.currentText(),
                    self.font_size_spinbox.value()
                )
                
                # Применяем тему
                selected_theme = None
                for button in self.theme_button_group.buttons():
                    if button.isChecked():
                        selected_theme = button.theme_id
                        break
                
                if selected_theme:
                    self.parent_app.apply_theme_live(selected_theme)
            
            QMessageBox.information(
                self,
                "Настройки применены",
                "Настройки успешно применены!"
            )
    
    def accept_settings(self):
        """Принять настройки и закрыть диалог."""
        if self.save_settings():
            # Применяем настройки в реальном времени
            if self.parent_app:
                # Обновляем интервалы
                self.parent_app.update_intervals(
                    self.autosave_spinbox.value(),
                    self.autosync_spinbox.value()
                )
                
                # Применяем шрифт
                self.parent_app.apply_editor_font(
                    self.font_combo.currentText(),
                    self.font_size_spinbox.value()
                )
                
                # Применяем тему
                selected_theme = None
                for button in self.theme_button_group.buttons():
                    if button.isChecked():
                        selected_theme = button.theme_id
                        break
                
                if selected_theme:
                    self.parent_app.apply_theme_live(selected_theme)
            
            self.accept()
