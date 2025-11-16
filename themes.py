"""
Система управления темами оформления для приложения заметок.
Поддерживает различные цветовые схемы и настройки внешнего вида.
"""

from dataclasses import dataclass
from typing import Dict
from PySide6.QtGui import QColor, QPalette


@dataclass
class Theme:
    """Класс для хранения настроек темы оформления."""
    
    # Название темы
    name: str
    
    # Цвета интерфейса
    background: str  # Основной фон
    text: str  # Основной текст
    
    # Цвета для кнопок
    button_background: str
    button_text: str
    button_hover: str
    button_disabled: str
    
    # Цвета для кнопки удаления
    delete_button_background: str
    delete_button_hover: str
    
    # Цвета для полей ввода
    input_background: str
    input_text: str
    input_border: str
    
    # Цвета для списка заметок
    list_background: str
    list_text: str
    list_selected: str
    list_hover: str
    
    # Цвет выделения при поиске
    search_highlight: str
    search_highlight_text: str
    
    # Цвета для статус-бара
    status_text: str
    
    # Цвета для поля поиска
    search_background: str
    search_border: str


class ThemeManager:
    """Менеджер тем оформления."""
    
    # Светлая тема (по умолчанию)
    LIGHT_THEME = Theme(
        name="Светлая",
        background="#FFFFFF",
        text="#000000",
        
        button_background="#0078D4",
        button_text="#FFFFFF",
        button_hover="#106EBE",
        button_disabled="#CCCCCC",
        
        delete_button_background="#F44336",
        delete_button_hover="#DA190B",
        
        input_background="#FFFFFF",
        input_text="#000000",
        input_border="#CCCCCC",
        
        list_background="#FFFFFF",
        list_text="#000000",
        list_selected="#0078D4",
        list_hover="#E5F3FF",
        
        # Жёлтый цвет выделения при поиске
        search_highlight="#FFEB3B",
        search_highlight_text="#000000",
        
        status_text="#666666",
        
        search_background="#FFFFFF",
        search_border="#CCCCCC",
    )
    
    # Темная тема
    DARK_THEME = Theme(
        name="Темная",
        background="#1E1E1E",
        text="#FFFFFF",
        
        button_background="#0E639C",
        button_text="#FFFFFF",
        button_hover="#1177BB",
        button_disabled="#3C3C3C",
        
        delete_button_background="#C62828",
        delete_button_hover="#8E0000",
        
        input_background="#2D2D2D",
        input_text="#FFFFFF",
        input_border="#3E3E3E",
        
        list_background="#252526",
        list_text="#CCCCCC",
        list_selected="#094771",
        list_hover="#2A2D2E",
        
        # Системный цвет выделения (синий на Windows)
        search_highlight="palette(highlight)",
        search_highlight_text="palette(highlighted-text)",
        
        status_text="#969696",
        
        search_background="#3C3C3C",
        search_border="#555555",
    )
    
    # Голубая тема
    BLUE_THEME = Theme(
        name="Голубая",
        background="#F0F8FF",
        text="#000000",
        
        button_background="#4682B4",
        button_text="#FFFFFF",
        button_hover="#5F9EA0",
        button_disabled="#D3D3D3",
        
        delete_button_background="#DC143C",
        delete_button_hover="#B22222",
        
        input_background="#FFFFFF",
        input_text="#000000",
        input_border="#B0C4DE",
        
        list_background="#E6F2FF",
        list_text="#000000",
        list_selected="#4682B4",
        list_hover="#D6E9FF",
        
        # Жёлтый цвет выделения при поиске
        search_highlight="#FFEB3B",
        search_highlight_text="#000000",
        
        status_text="#4682B4",
        
        search_background="#FFFFFF",
        search_border="#87CEEB",
    )
    
    # Зеленая тема
    GREEN_THEME = Theme(
        name="Зеленая",
        background="#F0FFF0",
        text="#000000",
        
        button_background="#2E7D32",
        button_text="#FFFFFF",
        button_hover="#388E3C",
        button_disabled="#C8E6C9",
        
        delete_button_background="#C62828",
        delete_button_hover="#8E0000",
        
        input_background="#FFFFFF",
        input_text="#000000",
        input_border="#A5D6A7",
        
        list_background="#E8F5E9",
        list_text="#000000",
        list_selected="#2E7D32",
        list_hover="#C8E6C9",
        
        # Жёлтый цвет выделения при поиске
        search_highlight="#FFEB3B",
        search_highlight_text="#000000",
        
        status_text="#2E7D32",
        
        search_background="#FFFFFF",
        search_border="#81C784",
    )
    
    def __init__(self):
        """Инициализация менеджера тем."""
        self.themes: Dict[str, Theme] = {
            "light": self.LIGHT_THEME,
            "dark": self.DARK_THEME,
            "blue": self.BLUE_THEME,
            "green": self.GREEN_THEME,
        }
        self.current_theme: Theme = self.LIGHT_THEME
    
    def get_theme(self, theme_name: str) -> Theme:
        """
        Получить тему по имени.
        
        Args:
            theme_name: Имя темы ("light", "dark", "blue", "green")
        
        Returns:
            Theme: Объект темы
        """
        return self.themes.get(theme_name, self.LIGHT_THEME)
    
    def set_theme(self, theme_name: str):
        """
        Установить текущую тему.
        
        Args:
            theme_name: Имя темы ("light", "dark", "blue", "green")
        """
        self.current_theme = self.get_theme(theme_name)
    
    def get_available_themes(self) -> list:
        """
        Получить список доступных тем.
        
        Returns:
            list: Список кортежей (id, название)
        """
        return [(key, theme.name) for key, theme in self.themes.items()]
    
    def get_stylesheet(self, theme: Theme = None) -> str:
        """
        Генерировать QSS stylesheet для темы.
        
        Args:
            theme: Тема оформления (если None, используется текущая)
        
        Returns:
            str: QSS stylesheet
        """
        if theme is None:
            theme = self.current_theme
        
        return f"""
            /* Основное окно */
            QMainWindow {{
                background-color: {theme.background};
                color: {theme.text};
            }}
            
            /* Кнопки */
            QPushButton {{
                background-color: {theme.button_background};
                color: {theme.button_text};
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {theme.button_hover};
            }}
            QPushButton:disabled {{
                background-color: {theme.button_disabled};
                color: #666666;
            }}
            
            /* Кнопка удаления */
            QPushButton#btn_delete {{
                background-color: {theme.delete_button_background};
            }}
            QPushButton#btn_delete:hover {{
                background-color: {theme.delete_button_hover};
            }}
            
            /* Поля ввода */
            QLineEdit, QTextEdit {{
                background-color: {theme.input_background};
                color: {theme.input_text};
                border: 1px solid {theme.input_border};
                padding: 5px;
                border-radius: 3px;
            }}
            
            QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid {theme.button_background};
            }}
            
            /* Список заметок */
            QListWidget {{
                background-color: {theme.list_background};
                color: {theme.list_text};
                border: 1px solid {theme.input_border};
                border-radius: 3px;
            }}
            
            QListWidget::item:selected {{
                background-color: {theme.list_selected};
                color: white;
            }}
            
            QListWidget::item:hover {{
                background-color: {theme.list_hover};
            }}
            
            /* Статус-бар */
            QLabel#status_label {{
                color: {theme.status_text};
                font-size: 11px;
                padding: 5px;
            }}
            
            /* Поле поиска */
            QLineEdit#search_box {{
                background-color: {theme.search_background};
                border: 2px solid {theme.search_border};
                padding: 8px;
                border-radius: 5px;
            }}
            
            QLineEdit#search_box:focus {{
                border: 2px solid {theme.button_background};
            }}
            
            /* Метка результатов поиска */
            QLabel#search_results {{
                color: {theme.status_text};
                font-weight: bold;
            }}
        """
    
    def get_search_highlight_color(self, theme: Theme = None) -> QColor:
        """
        Получить цвет выделения для поиска.
        
        Args:
            theme: Тема оформления (если None, используется текущая)
        
        Returns:
            QColor: Цвет выделения (системный highlight color)
        """
        if theme is None:
            theme = self.current_theme
        
        # Используем системную палитру для получения цвета выделения
        palette = QPalette()
        return palette.color(QPalette.ColorRole.Highlight)


# Глобальный экземпляр менеджера тем
theme_manager = ThemeManager()
