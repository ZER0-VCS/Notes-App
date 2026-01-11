"""
Графический интерфейс для приложения заметок.
Использует PySide6 (Qt) для создания desktop GUI.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLineEdit, QTextEdit, QPushButton,
    QSplitter, QMessageBox, QLabel, QFileDialog, QComboBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
import threading
from PySide6.QtGui import QFont, QShortcut, QKeySequence, QTextCharFormat, QColor, QTextCursor, QPalette, QBrush

try:
    from notes import Note, NoteStore
    from sync import SyncManager
    from themes import theme_manager
except ImportError:
    from .notes import Note, NoteStore
    from .sync import SyncManager
    from .themes import theme_manager

logger = logging.getLogger(__name__)


class SyncSignals(QObject):
    """Сигналы для межпоточной коммуникации синхронизации."""
    completed = Signal(bool, int, int)  # success, synced_count, conflict_count
    error = Signal(Exception)  # error


class NotesApp(QMainWindow):
    """
    Главное окно приложения для работы с заметками.
    """
    
    def __init__(self):
        super().__init__()
        
        # Инициализация хранилища заметок
        try:
            self.store = NoteStore()
        except Exception as e:
            logger.error("Ошибка при инициализации хранилища: %s", e)
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось инициализировать хранилище заметок:\n{e}"
            )
            sys.exit(1)
        
        self.current_note_id = None
        
        # Инициализация темы оформления
        self.theme_manager = theme_manager
        # Загружаем сохраненную тему
        self.saved_theme = self._load_theme_config()
        self.current_theme = self.theme_manager.get_theme(self.saved_theme)
        logger.info(f"Загружена тема: {self.saved_theme}")
        
        # Инициализация менеджера синхронизации
        self.sync_manager = SyncManager(self.store)
        logger.info("Менеджер синхронизации инициализирован")
        
        # Создание сигналов для межпоточной коммуникации
        self.sync_signals = SyncSignals()
        self.sync_signals.completed.connect(self._on_sync_complete)
        self.sync_signals.error.connect(self._on_sync_error)
        
        # Настройка окна
        self.setWindowTitle("Заметки")
        self.setGeometry(100, 100, 1000, 600)
        
        # Установка минимального размера окна
        self.setMinimumSize(800, 500)
        
        # Не устанавливаем максимальный размер - позволяем Windows/Qt управлять развертыванием
        # Это позволяет нативной кнопке "Развернуть" работать корректно
        
        # Создание интерфейса
        self.init_ui()
        
        # Настройка горячих клавиш
        self.setup_shortcuts()
        
        # Создание меню
        self.create_menu_bar()
        
        # Применяем сохраненные настройки шрифта и темы
        config_settings = self._load_config_settings()
        font_family = config_settings.get('editor_font', 'Arial')
        font_size = config_settings.get('editor_font_size', 11)
        self.apply_editor_font(font_family, font_size)
        logger.info(f"Применен сохраненный шрифт: {font_family}, размер {font_size}")
        
        # Применяем тему (уже загружена в __init__)
        self.apply_theme_live(self.saved_theme)
        logger.info(f"Применена сохраненная тема: {self.saved_theme}")
        
        # Загрузка заметок
        self.load_notes_list()
        
    def init_ui(self):
        """Инициализация пользовательского интерфейса."""
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главный layout
        main_layout = QHBoxLayout(central_widget)
        
        # Создание splitter для изменяемого размера панелей
        splitter = QSplitter(Qt.Horizontal)
        
        # === ЛЕВАЯ ПАНЕЛЬ: Список заметок ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Заголовок
        title_label = QLabel("Мои заметки")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        left_layout.addWidget(title_label)
        
        # Поле поиска
        self.search_box = QLineEdit()
        self.search_box.setObjectName("search_box")
        self.search_box.setPlaceholderText("Поиск по заголовку и тексту...")
        self.search_box.textChanged.connect(self.filter_notes)
        self.search_box.setClearButtonEnabled(True)  # Кнопка очистки
        left_layout.addWidget(self.search_box)
        
        # Метка с количеством результатов
        self.search_results_label = QLabel("")
        self.search_results_label.setObjectName("search_results")
        left_layout.addWidget(self.search_results_label)
        
        # Dropdown для сортировки
        sort_layout = QHBoxLayout()
        sort_label = QLabel("Сортировка:")
        sort_label.setObjectName("sort_label")
        sort_layout.addWidget(sort_label)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "По дате (новые)",
            "По дате (старые)",
            "По алфавиту (А-Я)",
            "По алфавиту (Я-А)",
            "По размеру"
        ])
        self.sort_combo.currentIndexChanged.connect(self.on_sort_changed)
        sort_layout.addWidget(self.sort_combo)
        left_layout.addLayout(sort_layout)
        
        # Список заметок
        self.notes_list = QListWidget()
        self.notes_list.itemClicked.connect(self.on_note_selected)
        # Ограничение ширины для предотвращения растягивания окна
        self.notes_list.setMaximumWidth(400)
        # Добавляем spacing между элементами списка
        self.notes_list.setSpacing(4)
        left_layout.addWidget(self.notes_list)
        
        # Кнопка "Создать новую заметку"
        self.btn_new = QPushButton("Создать заметку")
        self.btn_new.clicked.connect(self.create_new_note)
        self.btn_new.setObjectName("btn_new")
        left_layout.addWidget(self.btn_new)
        
        splitter.addWidget(left_panel)
        
        # === ПРАВАЯ ПАНЕЛЬ: Редактор заметки ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Заголовок заметки
        title_label2 = QLabel("Заголовок:")
        right_layout.addWidget(title_label2)
        
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Введите заголовок заметки...")
        self.title_edit.setFont(QFont("Arial", 14))
        # Ограничение длины заголовка
        self.title_edit.setMaxLength(100)
        self.title_edit.textChanged.connect(self.on_text_changed)
        # Ограничение ширины для предотвращения растягивания окна
        self.title_edit.setMaximumWidth(800)
        right_layout.addWidget(self.title_edit)
        
        # Теги заметки
        tags_label = QLabel("Теги (через запятую):")
        right_layout.addWidget(tags_label)
        
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("работа, личное, важное...")
        self.tags_edit.textChanged.connect(self.on_text_changed)
        self.tags_edit.setMaximumWidth(800)
        right_layout.addWidget(self.tags_edit)
        
        # Текст заметки
        body_label = QLabel("Текст:")
        right_layout.addWidget(body_label)
        
        self.body_edit = QTextEdit()
        self.body_edit.setPlaceholderText("Введите текст заметки...")
        self.body_edit.setFont(QFont("Arial", 11))
        # Включение переноса слов для предотвращения горизонтальной прокрутки
        self.body_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        self.body_edit.textChanged.connect(self.on_text_changed)
        right_layout.addWidget(self.body_edit)
        
        # Сохраняем ссылку на активные подсветки поиска
        self.search_highlights = []
        
        # Панель кнопок
        buttons_layout = QHBoxLayout()
        
        self.btn_save = QPushButton("Сохранить")
        self.btn_save.clicked.connect(self.save_current_note)
        self.btn_save.setEnabled(False)
        self.btn_save.setObjectName("btn_save")
        buttons_layout.addWidget(self.btn_save)
        
        self.btn_pin = QPushButton("Закрепить")
        self.btn_pin.clicked.connect(self.toggle_pin)
        self.btn_pin.setEnabled(False)
        self.btn_pin.setObjectName("btn_pin")
        buttons_layout.addWidget(self.btn_pin)
        
        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self.delete_current_note)
        self.btn_delete.setEnabled(False)
        self.btn_delete.setObjectName("btn_delete")
        buttons_layout.addWidget(self.btn_delete)
        
        buttons_layout.addStretch()
        
        # Кнопка синхронизации
        self.btn_sync = QPushButton("Синхронизировать")
        self.btn_sync.clicked.connect(self.sync_notes)
        self.btn_sync.setObjectName("btn_sync")
        buttons_layout.addWidget(self.btn_sync)

        # Кнопка настроек синхронизации (смена папки) - всегда доступна
        self.btn_sync_settings = QPushButton("📁")
        self.btn_sync_settings.setObjectName("btn_sync_settings")
        self.btn_sync_settings.setFixedWidth(36)
        # Устанавливаем шрифт с поддержкой эмодзи (Segoe UI Emoji для Windows)
        emoji_font = QFont("Segoe UI Emoji", 14)
        self.btn_sync_settings.setFont(emoji_font)
        self.btn_sync_settings.clicked.connect(self.setup_sync_path)
        self.btn_sync_settings.setToolTip("Изменить папку синхронизации")
        buttons_layout.addWidget(self.btn_sync_settings)
        
        right_layout.addLayout(buttons_layout)
        
        # Строка статуса: информация о загрузке/синхронизации
        self.status_label = QLabel("")
        self.status_label.setObjectName("status_label")
        self.status_label.setWordWrap(True)
        right_layout.addWidget(self.status_label)
        
        # Нижняя строка: информация о заметке и статистика
        bottom_status_layout = QHBoxLayout()
        
        self.note_info_label = QLabel("")
        self.note_info_label.setObjectName("note_info_label")
        self.note_info_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        bottom_status_layout.addWidget(self.note_info_label, stretch=1)
        
        self.statistics_label = QLabel("")
        self.statistics_label.setObjectName("statistics_label")
        self.statistics_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        bottom_status_layout.addWidget(self.statistics_label)
        
        right_layout.addLayout(bottom_status_layout)
        
        splitter.addWidget(right_panel)
        
        # Установка пропорций splitter (30% - 70%)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)
        
        main_layout.addWidget(splitter)
        
        # Флаг изменений
        self.has_unsaved_changes = False

        # Флаг синхронизации (предотвращает параллельные запуски)
        self._sync_in_progress = False
        self._is_manual_sync = False  # Флаг для различения ручной и автосинхронизации
        
        # Загружаем настройки интервалов
        config_settings = self._load_config_settings()
        autosave_interval = config_settings.get('autosave_interval', 5)
        autosync_interval = config_settings.get('autosync_interval', 60)
        
        # Таймер автосохранения
        self.autosave_timer = QTimer()
        self.autosave_timer.setSingleShot(True)  # Однократный запуск после каждого изменения
        self.autosave_timer.timeout.connect(self.autosave_current_note)
        self.autosave_delay = autosave_interval * 1000  # В миллисекундах
        logger.info(f"Интервал автосохранения: {autosave_interval} сек")
        
        # Таймер автосинхронизации
        self.autosync_timer = QTimer()
        self.autosync_timer.timeout.connect(self.auto_sync_notes)
        self.autosync_interval = autosync_interval * 1000  # В миллисекундах
        self.autosync_enabled = False  # По умолчанию выключена
        logger.info(f"Интервал автосинхронизации: {autosync_interval} сек")
        
        # Запускаем автосинхронизацию, если настроена папка облака
        if self.sync_manager.cloud_path:
            self.enable_autosync()
            logger.info("Автосинхронизация включена (интервал: 60 сек)")
    
    def setup_shortcuts(self):
        """Настройка горячих клавиш."""
        # Ctrl+S - Сохранить
        QShortcut(QKeySequence.Save, self).activated.connect(self.save_current_note)
        logger.info("Горячая клавиша Ctrl+S настроена")
        
        # Ctrl+N - Новая заметка
        QShortcut(QKeySequence.New, self).activated.connect(self.create_new_note)
        logger.info("Горячая клавиша Ctrl+N настроена")
        
        # Ctrl+D - Удалить
        QShortcut(QKeySequence("Ctrl+D"), self).activated.connect(self.delete_current_note)
        logger.info("Горячая клавиша Ctrl+D настроена")
        
        # Ctrl+F - Поиск
        QShortcut(QKeySequence.Find, self).activated.connect(self.focus_search)
        logger.info("Горячая клавиша Ctrl+F настроена")
    
    def create_menu_bar(self):
        """Создание меню приложения."""
        from PySide6.QtWidgets import QMenuBar
        from PySide6.QtGui import QActionGroup, QAction
        
        menubar = self.menuBar()
        
        # Меню "Файл"
        file_menu = menubar.addMenu("&Файл")
        
        # Экспорт
        export_menu = file_menu.addMenu("Экспорт")
        
        export_md_action = QAction("Текущую заметку в Markdown...", self)
        export_md_action.triggered.connect(lambda: self.export_current_note('markdown'))
        export_menu.addAction(export_md_action)
        
        export_txt_action = QAction("Текущую заметку в TXT...", self)
        export_txt_action.triggered.connect(lambda: self.export_current_note('txt'))
        export_menu.addAction(export_txt_action)
        
        export_html_action = QAction("Текущую заметку в HTML...", self)
        export_html_action.triggered.connect(lambda: self.export_current_note('html'))
        export_menu.addAction(export_html_action)
        
        export_menu.addSeparator()
        
        export_all_md_action = QAction("Все заметки в ZIP (Markdown)...", self)
        export_all_md_action.triggered.connect(lambda: self.export_all_notes('markdown'))
        export_menu.addAction(export_all_md_action)
        
        export_all_txt_action = QAction("Все заметки в ZIP (TXT)...", self)
        export_all_txt_action.triggered.connect(lambda: self.export_all_notes('txt'))
        export_menu.addAction(export_all_txt_action)
        
        export_all_html_action = QAction("Все заметки в ZIP (HTML)...", self)
        export_all_html_action.triggered.connect(lambda: self.export_all_notes('html'))
        export_menu.addAction(export_all_html_action)
        
        file_menu.addSeparator()
        
        # Настройки
        settings_action = QAction("Настройки...", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        # Выход
        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Меню "Вид"
        view_menu = menubar.addMenu("&Вид")
        
        # Подменю "Тема"
        theme_menu = view_menu.addMenu("Тема")
        
        # Группа для radio buttons
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        
        # Получаем доступные темы
        available_themes = self.theme_manager.get_available_themes()
        
        for theme_id, theme_display_name in available_themes:
            action = QAction(theme_display_name, self)
            action.setCheckable(True)
            
            # Отмечаем текущую тему
            if theme_id == self.current_theme.name or theme_display_name == self.current_theme.name:
                action.setChecked(True)
            
            # Подключаем обработчик
            action.triggered.connect(
                lambda checked, tid=theme_id: self.change_theme(tid)
            )
            
            theme_group.addAction(action)
            theme_menu.addAction(action)
        
        logger.info("Меню создано")
    
    def export_current_note(self, format_type: str):
        """
        Экспортировать текущую заметку в указанный формат.
        
        Args:
            format_type: Тип формата ('markdown', 'txt', 'html')
        """
        if not self.current_note_id:
            QMessageBox.warning(
                self,
                "Нет выбранной заметки",
                "Выберите заметку для экспорта."
            )
            return
        
        from export import NoteExporter
        
        note = self.store.get_note(self.current_note_id)
        if not note:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось загрузить заметку."
            )
            return
        
        # Выбор файла для сохранения
        extensions = {
            'markdown': ('Markdown Files (*.md)', '.md'),
            'txt': ('Text Files (*.txt)', '.txt'),
            'html': ('HTML Files (*.html)', '.html')
        }
        
        ext_filter, ext = extensions.get(format_type, ('All Files (*)', ''))
        
        # Безопасное имя файла
        safe_title = "".join(c for c in note.title if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_title:
            safe_title = f"note_{note.id[:8]}"
        
        default_name = f"{safe_title}{ext}"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспортировать заметку",
            str(Path.home() / default_name),
            ext_filter
        )
        
        if not file_path:
            return
        
        # Экспорт
        success = False
        if format_type == 'markdown':
            success = NoteExporter.export_to_markdown(note, Path(file_path))
        elif format_type == 'txt':
            success = NoteExporter.export_to_txt(note, Path(file_path))
        elif format_type == 'html':
            success = NoteExporter.export_to_html(note, Path(file_path))
        
        if success:
            QMessageBox.information(
                self,
                "Экспорт завершен",
                f"Заметка успешно экспортирована в:\n{file_path}"
            )
        else:
            QMessageBox.critical(
                self,
                "Ошибка экспорта",
                "Не удалось экспортировать заметку."
            )
    
    def export_all_notes(self, format_type: str):
        """
        Экспортировать все заметки в ZIP архив.
        
        Args:
            format_type: Тип формата ('markdown', 'txt', 'html')
        """
        from export import NoteExporter
        
        notes = self.store.get_all_notes()
        if not notes:
            QMessageBox.warning(
                self,
                "Нет заметок",
                "Нет заметок для экспорта."
            )
            return
        
        # Выбор файла для сохранения
        format_names = {
            'markdown': 'Markdown',
            'txt': 'TXT',
            'html': 'HTML'
        }
        
        default_name = f"notes_export_{format_names.get(format_type, 'all')}.zip"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспортировать все заметки",
            str(Path.home() / default_name),
            "ZIP Files (*.zip)"
        )
        
        if not file_path:
            return
        
        # Экспорт
        success = NoteExporter.export_all_to_zip(notes, Path(file_path), format_type)
        
        if success:
            QMessageBox.information(
                self,
                "Экспорт завершен",
                f"Все заметки ({len(notes)}) успешно экспортированы в:\n{file_path}"
            )
        else:
            QMessageBox.critical(
                self,
                "Ошибка экспорта",
                "Не удалось экспортировать заметки."
            )
    
    def open_settings_dialog(self):
        """Открыть диалог настроек."""
        from settings_dialog import SettingsDialog
        
        # Загружаем текущую тему из конфига
        saved_theme = self._load_theme_config()
        
        dialog = SettingsDialog(self, saved_theme)
        if dialog.exec():
            logger.info("Настройки сохранены пользователем")
            QMessageBox.information(
                self,
                "Настройки применены",
                "Настройки сохранены успешно."
            )
    
    def update_intervals(self, autosave_interval: int, autosync_interval: int):
        """
        Обновить интервалы автосохранения и автосинхронизации.
        
        Args:
            autosave_interval: Интервал автосохранения в секундах
            autosync_interval: Интервал автосинхронизации в секундах
        """
        # Обновляем автосохранение
        if hasattr(self, 'autosave_delay'):
            self.autosave_delay = autosave_interval * 1000
            logger.info(f"Интервал автосохранения обновлен: {autosave_interval} сек")
        
        # Обновляем автосинхронизацию
        if hasattr(self, 'autosync_interval'):
            self.autosync_interval = autosync_interval * 1000
            if hasattr(self, 'autosync_timer') and self.autosync_timer.isActive():
                self.autosync_timer.setInterval(self.autosync_interval)
                logger.info(f"Интервал автосинхронизации обновлен: {autosync_interval} сек")
    
    def apply_editor_font(self, font_family: str, font_size: int):
        """
        Применить шрифт к редактору заметок и списку.
        
        Args:
            font_family: Название шрифта
            font_size: Размер шрифта
        """
        try:
            # Применяем к полю заголовка
            title_font = QFont(font_family, font_size + 3)  # Заголовок крупнее
            self.title_edit.setFont(title_font)
            
            # Применяем к полю текста
            body_font = QFont(font_family, font_size)
            self.body_edit.setFont(body_font)
            
            # Применяем к списку заметок
            list_font = QFont(font_family, font_size)
            self.notes_list.setFont(list_font)
            
            # Применяем к полю поиска
            search_font = QFont(font_family, font_size - 1)
            self.search_box.setFont(search_font)
            
            # Применяем к полю тегов
            tags_font = QFont(font_family, font_size)
            self.tags_edit.setFont(tags_font)
            
            logger.info(f"Шрифт применен: {font_family}, размер {font_size}")
        except Exception as e:
            logger.error(f"Ошибка при применении шрифта: {e}")
    
    def apply_theme_live(self, theme_name: str):
        """
        Применить тему оформления без перезапуска приложения.
        
        Args:
            theme_name: Имя темы
        """
        try:
            theme = self.theme_manager.get_theme(theme_name)
            self.current_theme = theme
            
            # Сохраняем текущие шрифты перед применением темы
            title_font = self.title_edit.font()
            body_font = self.body_edit.font()
            list_font = self.notes_list.font()
            search_font = self.search_box.font()
            tags_font = self.tags_edit.font()
            
            # Применяем цвета темы к основным элементам
            palette = self.palette()
            palette.setColor(self.backgroundRole(), QColor(theme.background))
            palette.setColor(self.foregroundRole(), QColor(theme.text))
            self.setPalette(palette)
            
            # Обновляем стиль основного окна и всех элементов
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {theme.background};
                    color: {theme.text};
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
                
                /* Обычные кнопки */
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
                
                /* Кнопка создания заметки */
                QPushButton#btn_new {{
                    background-color: #4CAF50;
                    padding: 10px;
                }}
                QPushButton#btn_new:hover {{
                    background-color: #45a049;
                }}
                
                /* Кнопка закрепления */
                QPushButton#btn_pin {{
                    background-color: #FF9800;
                }}
                QPushButton#btn_pin:hover {{
                    background-color: #FB8C00;
                }}
                
                /* Кнопка удаления */
                QPushButton#btn_delete {{
                    background-color: {theme.delete_button_background};
                }}
                QPushButton#btn_delete:hover {{
                    background-color: {theme.delete_button_hover};
                }}
                
                /* Кнопка синхронизации */
                QPushButton#btn_sync {{
                    background-color: #FF9800;
                }}
                QPushButton#btn_sync:hover {{
                    background-color: #F57C00;
                }}
                
                /* Кнопка настроек синхронизации (с эмодзи папки) */
                QPushButton#btn_sync_settings {{
                    background-color: {theme.button_background};
                    font-size: 16px;
                    padding: 8px;
                }}
                QPushButton#btn_sync_settings:hover {{
                    background-color: {theme.button_hover};
                }}
                
                /* Метки */
                QLabel {{
                    color: {theme.text};
                    background-color: transparent;
                }}
                
                /* Статус-бары и информационные метки */
                QLabel#status_label, QLabel#note_info_label, QLabel#statistics_label {{
                    color: {theme.status_text};
                    font-size: 11px;
                    padding: 5px;
                }}
                
                /* Метка результатов поиска и сортировки */
                QLabel#search_results, QLabel#sort_label {{
                    color: {theme.status_text};
                    font-size: 11px;
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
                
                /* Комбобокс */
                QComboBox {{
                    background-color: {theme.input_background};
                    color: {theme.input_text};
                    border: 1px solid {theme.input_border};
                    padding: 5px;
                    border-radius: 3px;
                }}
                QComboBox:hover {{
                    border: 1px solid {theme.button_background};
                }}
                QComboBox::drop-down {{
                    border: none;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {theme.input_background};
                    color: {theme.input_text};
                    selection-background-color: {theme.list_selected};
                    selection-color: white;
                }}
            """)
            
            # Восстанавливаем шрифты после применения стилей
            self.title_edit.setFont(title_font)
            self.body_edit.setFont(body_font)
            self.notes_list.setFont(list_font)
            self.search_box.setFont(search_font)
            self.tags_edit.setFont(tags_font)
            
            # Настраиваем палитру выделения для текстовых полей
            self.setup_selection_palette(theme)
            
            logger.info(f"Тема применена в реальном времени: {theme_name}")
        except Exception as e:
            logger.error(f"Ошибка при применении темы: {e}")
    
    def setup_selection_palette(self, theme):
        """Настройка цветов выделения текста (как в VS Code/Word).
        
        Args:
            theme: Объект темы с цветовой схемой
        """
        # Создаем палитру для ручного выделения текста
        for widget in [self.title_edit, self.tags_edit, self.body_edit]:
            palette = widget.palette()
            
            # Цвет фона выделенного текста (как в VS Code)
            palette.setColor(QPalette.ColorRole.Highlight, QColor(theme.text_selection_background))
            
            # Цвет текста при выделении (контрастный)
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor(theme.text_selection_foreground))
            
            # Цвет неактивного выделения (когда фокус не на виджете)
            palette.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Highlight, 
                           QColor(theme.text_selection_inactive))
            palette.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.HighlightedText, 
                           QColor(theme.text_selection_foreground))
            
            widget.setPalette(palette)
    
    def change_theme(self, theme_name: str):
        """
        Изменить тему оформления.
        
        Args:
            theme_name: Имя темы
        """
        try:
            # Применяем тему сразу
            self.apply_theme_live(theme_name)
            logger.info(f"Тема изменена на: {theme_name}")
            
            # Сохраняем выбор темы в config.json
            self._save_theme_config(theme_name)
            
            QMessageBox.information(
                self,
                "Тема изменена",
                f"Тема '{theme_name}' успешно применена!"
            )
        except Exception as e:
            logger.error(f"Ошибка при изменении темы: {e}")
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось изменить тему:\n{e}"
            )
    
    def _load_config_settings(self) -> dict:
        """
        Загрузить все настройки из config.json.
        
        Returns:
            Словарь с настройками
        """
        import json
        config_path = Path.home() / ".notes_app" / "config.json"
        default_settings = {
            'theme': 'light',
            'autosave_interval': 5,
            'autosync_interval': 60,
            'editor_font': 'Arial',
            'editor_font_size': 11
        }
        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info("Настройки загружены из конфига")
                    return {**default_settings, **config}
        except Exception as e:
            logger.warning(f"Не удалось загрузить настройки из конфига: {e}")
        return default_settings
    
    def _load_theme_config(self) -> str:
        """
        Загрузить настройку темы из config.json.
        
        Returns:
            Имя темы или "light" по умолчанию
        """
        config = self._load_config_settings()
        theme = config.get('theme', 'light')
        logger.info(f"Загружена тема из конфига: {theme}")
        return theme
    
    def _save_theme_config(self, theme_name: str):
        """
        Сохранить настройку темы в config.json.
        
        Args:
            theme_name: Имя темы
        """
        import json
        config_path = Path.home() / ".notes_app" / "config.json"
        try:
            # Загружаем существующий конфиг
            config = {}
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # Обновляем тему
            config['theme'] = theme_name
            
            # Сохраняем
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Тема сохранена в конфиг: {theme_name}")
        except Exception as e:
            logger.error(f"Не удалось сохранить тему в конфиг: {e}")
    
    def apply_theme(self, theme_name: str = "light"):
        """
        Применить тему оформления к приложению.
        
        Args:
            theme_name: Имя темы ("light", "dark", "blue", "green")
        """
        theme = self.theme_manager.get_theme(theme_name)
        self.current_theme = theme
        
        # Применяем stylesheet
        # Примечание: В текущей версии стили применяются через inline CSS в init_ui
        # В будущем можно использовать self.setStyleSheet(self.theme_manager.get_stylesheet(theme))
        
        logger.info(f"Применена тема: {theme.name}")
    
    def load_notes_list(self, reload_current_note: bool = False):
        """Загрузка списка заметок в QListWidget.
        
        Args:
            reload_current_note: Если True, перезагружает текущую открытую заметку после обновления списка
        """
        # Сохраняем ID текущей заметки для возможной перезагрузки
        current_note_id = self.current_note_id if reload_current_note else None
        
        self.notes_list.clear()
        
        notes = self.store.get_all_notes()
        
        # Применяем сортировку в зависимости от выбранного режима
        sort_mode = self.sort_combo.currentText()
        
        if sort_mode == "По дате (новые)":
            # Закрепленные внизу, затем по дате (новые сверху)
            notes.sort(key=lambda n: (n.pinned, n.last_modified), reverse=True)
        elif sort_mode == "По дате (старые)":
            # Закрепленные внизу, затем по дате (старые сверху)
            notes.sort(key=lambda n: (n.pinned, n.last_modified))
        elif sort_mode == "По алфавиту (А-Я)":
            # Закрепленные внизу, затем по алфавиту А-Я
            notes.sort(key=lambda n: (n.pinned, (n.title or "").lower()))
        elif sort_mode == "По алфавиту (Я-А)":
            # Закрепленные внизу, затем по алфавиту Я-А
            notes.sort(key=lambda n: (n.pinned, (n.title or "").lower()), reverse=True)
        elif sort_mode == "По размеру":
            # Закрепленные внизу, затем по размеру (большие сверху)
            notes.sort(key=lambda n: (n.pinned, -len(n.body)))
        
        for note in notes:
            # Обрезаем длинные названия для списка
            title = note.title or "(Без заголовка)"
            
            # Добавляем индикатор закрепления
            if note.pinned:
                title = "📌 " + title
            
            if len(title) > 50:
                title = title[:47] + "..."
            
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, note.id)  # Сохраняем ID заметки
            # Добавляем полный заголовок как подсказку
            item.setToolTip(note.title or "(Без заголовка)")
            self.notes_list.addItem(item)
        
        # Обновление статуса
        self.update_status(f"Загружено заметок: {len(notes)}")
        
        # Применяем текущий фильтр поиска (если есть)
        if self.search_box.text():
            self.filter_notes(self.search_box.text())
        
        # Перезагружаем текущую заметку, если она была открыта
        if current_note_id:
            note = self.store.get_note(current_note_id)
            if note:
                # Перезагружаем с блокировкой сигналов, чтобы не вызвать has_unsaved_changes
                self.load_note(current_note_id)
    
    def filter_notes(self, search_text: str = ""):
        """Фильтрация списка заметок по поисковому запросу."""
        search_text = search_text.lower().strip()
        
        if not search_text:
            # Показываем все заметки без подсветки
            for i in range(self.notes_list.count()):
                item = self.notes_list.item(i)
                item.setHidden(False)
                # Убираем индикаторы поиска
                note_id = item.data(Qt.UserRole)
                all_notes = self.store.get_all_notes()
                note = next((n for n in all_notes if n.id == note_id), None)
                if note:
                    title = note.title or "(Без заголовка)"
                    if len(title) > 50:
                        title = title[:47] + "..."
                    item.setText(title)
            self.search_results_label.setText("")
            
            # Убираем подсветку текста во всех полях
            if self.current_note_id:
                # Очищаем подсветку в заголовке
                self.title_edit.deselect()
                
                # Очищаем подсветку в теле заметки
                cursor = self.body_edit.textCursor()
                cursor.select(QTextCursor.SelectionType.Document)
                cursor.setCharFormat(QTextCharFormat())
                cursor.clearSelection()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                self.body_edit.setTextCursor(cursor)
                
                # Очищаем подсветку в тегах
                self.tags_edit.deselect()
            
            return
        
        # Получаем все заметки для поиска по телу
        all_notes = self.store.get_all_notes()
        notes_dict = {note.id: note for note in all_notes}
        
        visible_count = 0
        
        for i in range(self.notes_list.count()):
            item = self.notes_list.item(i)
            note_id = item.data(Qt.UserRole)
            note = notes_dict.get(note_id)
            
            if note:
                # Поиск в заголовке, тексте и тегах (регистронезависимый)
                title_match = search_text in note.title.lower()
                body_match = search_text in note.body.lower()
                tags_match = any(search_text in tag.lower() for tag in note.tags)
                
                if title_match or body_match or tags_match:
                    item.setHidden(False)
                    visible_count += 1
                    
                    # Добавляем индикатор типа совпадения
                    title = note.title or "(Без заголовка)"
                    if len(title) > 50:
                        title = title[:47] + "..."
                    
                    if title_match:
                        item.setText(f"📌 {title}")
                    elif tags_match:
                        item.setText(f"🏷️ {title}")
                    else:  # body_match
                        item.setText(f"📄 {title}")
                else:
                    item.setHidden(True)
            else:
                item.setHidden(True)
        
        # Обновляем счётчик результатов
        if visible_count == 0:
            self.search_results_label.setText(f"Ничего не найдено")
        elif visible_count == 1:
            self.search_results_label.setText(f"Найдена 1 заметка")
        else:
            self.search_results_label.setText(f"Найдено заметок: {visible_count}")
    
    def focus_search(self):
        """Установка фокуса на поле поиска (Ctrl+F)."""
        self.search_box.setFocus()
        self.search_box.selectAll()
        logger.info("Фокус установлен на поле поиска")
    
    def highlight_text_in_field(self, text_edit, search_text: str, scroll_to_first: bool = False):
        """Подсветка найденного текста с использованием ExtraSelections (как в VS Code).
        
        Args:
            text_edit: QTextEdit или QLineEdit для подсветки
            search_text: Текст для поиска
            scroll_to_first: Прокручивать к первому совпадению
        """
        if not search_text:
            # Очищаем подсветку если поиск пустой
            self.clear_search_highlights(text_edit)
            return
        
        # Получаем текст в зависимости от типа поля
        from PySide6.QtWidgets import QLineEdit, QTextEdit
        if isinstance(text_edit, QLineEdit):
            text = text_edit.text()
        else:
            text = text_edit.toPlainText()
        
        if not text:
            return
        
        # Для QLineEdit используем встроенное выделение
        if isinstance(text_edit, QLineEdit):
            text_lower = text.lower()
            search_lower = search_text.lower()
            
            if search_lower in text_lower:
                # Находим позицию первого совпадения
                pos = text_lower.find(search_lower)
                # Выделяем текст (использует палитру Highlight)
                text_edit.setSelection(pos, len(search_text))
        else:
            # Для QTextEdit используем ExtraSelections (не влияет на ручное выделение)
            self.clear_search_highlights(text_edit)
            
            # Получаем цвет выделения поиска из темы (отличается от ручного выделения)
            search_bg_color = QColor(self.current_theme.search_highlight)
            search_fg_color = QColor(self.current_theme.search_highlight_text)
            
            # Создаём формат для подсветки поиска
            search_format = QTextCharFormat()
            search_format.setBackground(QBrush(search_bg_color))
            search_format.setForeground(QBrush(search_fg_color))
            
            # Ищем все вхождения (регистронезависимо)
            extra_selections = []
            cursor = QTextCursor(text_edit.document())
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            
            text_lower = text.lower()
            search_lower = search_text.lower()
            
            pos = 0
            first_cursor = None
            while True:
                pos = text_lower.find(search_lower, pos)
                if pos == -1:
                    break
                
                # Создаём выделение для этого вхождения
                selection_cursor = QTextCursor(text_edit.document())
                selection_cursor.setPosition(pos)
                selection_cursor.setPosition(pos + len(search_text), QTextCursor.MoveMode.KeepAnchor)
                
                # Создаём ExtraSelection
                selection = QTextEdit.ExtraSelection()
                selection.cursor = selection_cursor
                selection.format = search_format
                extra_selections.append(selection)
                
                # Запоминаем первое вхождение для прокрутки
                if first_cursor is None:
                    first_cursor = selection_cursor
                
                pos += len(search_text)
            
            # Применяем все подсветки поиска (не затрагивает ручное выделение)
            text_edit.setExtraSelections(extra_selections)
            self.search_highlights = extra_selections
            
            # Прокручиваем к первому найденному вхождению
            if scroll_to_first and first_cursor:
                text_edit.setTextCursor(first_cursor)
    
    def clear_search_highlights(self, text_edit):
        """Очистка подсветки поиска без влияния на ручное выделение.
        
        Args:
            text_edit: QTextEdit для очистки
        """
        from PySide6.QtWidgets import QTextEdit
        if isinstance(text_edit, QTextEdit):
            text_edit.setExtraSelections([])
            self.search_highlights = []
    
    def on_note_selected(self, item):
        """Обработчик выбора заметки из списка."""
        # Проверяем, что item еще существует
        if not item:
            return
        
        try:
            note_id = item.data(Qt.UserRole)
        except RuntimeError:
            # Item был удален
            return
        
        # Проверка несохраненных изменений
        if self.has_unsaved_changes:
            reply = QMessageBox.question(
                self,
                "Несохраненные изменения",
                "У вас есть несохраненные изменения. Сохранить их?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Yes:
                self.save_current_note()
            elif reply == QMessageBox.Cancel:
                return
        
        # Загрузка выбранной заметки
        self.load_note(note_id)
    
    def load_note(self, note_id):
        """Загрузка заметки в редактор."""
        # Останавливаем таймер автосохранения для предыдущей заметки
        self.autosave_timer.stop()
        
        note = self.store.get_note(note_id)
        
        if note:
            self.current_note_id = note_id
            
            # Блокируем сигналы, чтобы избежать пометки как "измененное"
            self.title_edit.blockSignals(True)
            self.body_edit.blockSignals(True)
            self.tags_edit.blockSignals(True)
            
            self.title_edit.setText(note.title)
            # Устанавливаем курсор в начало для длинных заголовков
            self.title_edit.setCursorPosition(0)
            self.body_edit.setText(note.body)
            # Конвертируем список тегов в строку через запятую
            self.tags_edit.setText(", ".join(note.tags))
            
            self.title_edit.blockSignals(False)
            self.body_edit.blockSignals(False)
            self.tags_edit.blockSignals(False)
            
            # Активируем кнопки
            self.btn_save.setEnabled(False)
            self.btn_delete.setEnabled(True)
            self.btn_pin.setEnabled(True)
            
            # Обновляем текст кнопки закрепления
            if note.pinned:
                self.btn_pin.setText("Открепить")
            else:
                self.btn_pin.setText("Закрепить")
            
            self.has_unsaved_changes = False
            self.update_status(f"Заметка загружена: {note.title}")
            self.update_note_info()
            
            # Применяем подсветку текста, если есть активный поиск
            search_text = self.search_box.text().strip()
            if search_text:
                # Блокируем сигналы при применении подсветки
                self.title_edit.blockSignals(True)
                self.body_edit.blockSignals(True)
                self.tags_edit.blockSignals(True)
                
                # Подсвечиваем во всех полях
                self.highlight_text_in_field(self.title_edit, search_text, scroll_to_first=False)
                self.highlight_text_in_field(self.body_edit, search_text, scroll_to_first=True)
                self.highlight_text_in_field(self.tags_edit, search_text, scroll_to_first=False)
                
                self.title_edit.blockSignals(False)
                self.body_edit.blockSignals(False)
                self.tags_edit.blockSignals(False)
    
    def create_new_note(self):
        """Создание новой заметки."""
        # Проверка несохраненных изменений
        if self.has_unsaved_changes:
            reply = QMessageBox.question(
                self,
                "Несохраненные изменения",
                "У вас есть несохраненные изменения. Сохранить их?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Yes:
                self.save_current_note()
            elif reply == QMessageBox.Cancel:
                return
        
        try:
            # Создаем новую заметку
            new_note = Note(title="Новая заметка", body="")
            self.store.add_note(new_note)
            logger.info("Создана новая заметка: %s", new_note.id[:8])
            
            # Обновляем список
            self.load_notes_list()
            
            # Загружаем новую заметку в редактор
            self.load_note(new_note.id)
            
            # Ставим фокус на заголовок
            self.title_edit.selectAll()
            self.title_edit.setFocus()
            
            self.update_status("Создана новая заметка")
        
        except Exception as e:
            logger.error("Ошибка при создании заметки: %s", e)
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось создать заметку:\n{e}"
            )
    
    def save_current_note(self):
        """Сохранение текущей заметки."""
        if not self.current_note_id:
            logger.warning("Попытка сохранить, но заметка не выбрана")
            return
        
        try:
            title = self.title_edit.text()
            body = self.body_edit.toPlainText()
            # Парсим теги из текста (разделитель - запятая)
            tags_text = self.tags_edit.text()
            tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
            
            # Обновляем заметку
            success = self.store.update_note(self.current_note_id, title=title, body=body, tags=tags)
            
            if success:
                self.has_unsaved_changes = False
                self.btn_save.setEnabled(False)
                self.load_notes_list()
                self.update_status("Заметка сохранена")
                logger.info("Заметка сохранена: %s", self.current_note_id[:8])
                
                # Автоматически выбираем обновленную заметку в списке
                for i in range(self.notes_list.count()):
                    item = self.notes_list.item(i)
                    if item.data(Qt.UserRole) == self.current_note_id:
                        self.notes_list.setCurrentItem(item)
                        break
        
        except Exception as e:
            logger.error("Ошибка при сохранении заметки: %s", e)
            QMessageBox.critical(
                self,
                "Ошибка сохранения",
                f"Не удалось сохранить заметку:\n{e}"
            )
    
    def autosave_current_note(self):
        """Автоматическое сохранение текущей заметки по таймеру."""
        if not self.current_note_id or not self.has_unsaved_changes:
            return
        
        try:
            title = self.title_edit.text()
            body = self.body_edit.toPlainText()
            # Парсим теги из текста (разделитель - запятая)
            tags_text = self.tags_edit.text()
            tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
            
            # Обновляем заметку
            success = self.store.update_note(self.current_note_id, title=title, body=body, tags=tags)
            
            if success:
                self.has_unsaved_changes = False
                self.btn_save.setEnabled(False)
                self.load_notes_list()
                
                # Получаем текущее время для отображения
                from datetime import datetime
                current_time = datetime.now().strftime("%H:%M:%S")
                self.update_status(f"💾 Автоматически сохранено в {current_time}")
                logger.info("Заметка автоматически сохранена: %s", self.current_note_id[:8])
                
                # Автоматически выбираем обновленную заметку в списке
                for i in range(self.notes_list.count()):
                    item = self.notes_list.item(i)
                    if item.data(Qt.UserRole) == self.current_note_id:
                        self.notes_list.setCurrentItem(item)
                        break
        
        except Exception as e:
            logger.error("Ошибка при автосохранении заметки: %s", e)
            # Не показываем модальный диалог для автосохранения, только логируем
            self.update_status("Ошибка автосохранения")
    
    def delete_current_note(self):
        """Удаление текущей заметки."""
        if not self.current_note_id:
            logger.warning("Попытка удалить, но заметка не выбрана")
            return
        
        # Подтверждение удаления
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            "Вы уверены, что хотите удалить эту заметку?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Останавливаем таймер автосохранения
                self.autosave_timer.stop()
                
                note_title = self.title_edit.text() or "(Без заголовка)"
                note_id = self.current_note_id
                success = self.store.delete_note(self.current_note_id)
                
                if success:
                    self.update_status(f"Заметка удалена: {note_title}")
                    logger.info("Заметка удалена: %s", note_id[:8])
                    
                    # Очищаем редактор
                    self.current_note_id = None
                    
                    # Блокируем сигналы при очистке
                    self.title_edit.blockSignals(True)
                    self.body_edit.blockSignals(True)
                    self.tags_edit.blockSignals(True)
                    
                    self.title_edit.clear()
                    self.body_edit.clear()
                    self.tags_edit.clear()
                    
                    # Разблокируем сигналы
                    self.title_edit.blockSignals(False)
                    self.body_edit.blockSignals(False)
                    self.tags_edit.blockSignals(False)
                    
                    self.btn_save.setEnabled(False)
                    self.btn_delete.setEnabled(False)
                    self.btn_pin.setEnabled(False)
                    self.has_unsaved_changes = False
                    self.note_info_label.setText("")
                    
                    # Обновляем список
                    self.load_notes_list()
            
            except Exception as e:
                logger.error("Ошибка при удалении заметки: %s", e)
                QMessageBox.critical(
                    self,
                    "Ошибка удаления",
                    f"Не удалось удалить заметку:\n{e}"
                )
    
    def toggle_pin(self):
        """Закрепление/открепление текущей заметки."""
        if not self.current_note_id:
            logger.warning("Попытка закрепить, но заметка не выбрана")
            return
        
        note = self.store.get_note(self.current_note_id)
        if not note:
            logger.error("Заметка не найдена: %s", self.current_note_id)
            return
        
        # Меняем состояние закрепления
        note.pinned = not note.pinned
        
        # Обновляем версию и время модификации
        note.version += 1
        note.last_modified = datetime.now(timezone.utc).isoformat()
        
        # Сохраняем
        self.store.save()
        
        # Обновляем UI
        if note.pinned:
            self.btn_pin.setText("Открепить")
            self.update_status(f"Заметка закреплена: {note.title}")
            logger.info("Заметка закреплена: %s", self.current_note_id[:8])
        else:
            self.btn_pin.setText("Закрепить")
            self.update_status(f"Заметка откреплена: {note.title}")
            logger.info("Заметка откреплена: %s", self.current_note_id[:8])
        
        # Обновляем список с новой сортировкой
        self.load_notes_list()
    
    def on_text_changed(self):
        """Обработчик изменения текста в редакторе."""
        if not self.current_note_id:
            # Автоматически создаём новую заметку при начале редактирования
            try:
                # Блокируем сигналы, чтобы избежать рекурсии
                self.title_edit.blockSignals(True)
                self.body_edit.blockSignals(True)
                self.tags_edit.blockSignals(True)
                
                # Создаем новую заметку с текущим содержимым
                title = self.title_edit.text() or "Новая заметка"
                body = self.body_edit.toPlainText()
                tags_text = self.tags_edit.text()
                tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
                
                new_note = Note(title=title, body=body, tags=tags)
                self.store.add_note(new_note)
                self.current_note_id = new_note.id
                
                # Обновляем список
                self.load_notes_list()
                
                # Разблокируем сигналы
                self.title_edit.blockSignals(False)
                self.body_edit.blockSignals(False)
                self.tags_edit.blockSignals(False)
                
                # Активируем кнопки
                self.btn_delete.setEnabled(True)
                self.btn_pin.setEnabled(True)
                self.btn_pin.setText("Закрепить")
                
                logger.info("Автоматически создана новая заметка: %s", new_note.id[:8])
                self.update_status("Создана новая заметка")
            except Exception as e:
                logger.error("Ошибка при автоматическом создании заметки: %s", e)
                return
        
        self.has_unsaved_changes = True
        self.btn_save.setEnabled(True)
        self.update_status("Есть несохраненные изменения")
        self.update_note_info()
        
        # Перезапускаем таймер автосохранения
        self.autosave_timer.stop()  # Останавливаем предыдущий таймер
        self.autosave_timer.start(self.autosave_delay)  # Запускаем новый отсчёт
    
    def update_status(self, message):
        """Обновление статусного сообщения."""
        self.status_label.setText(message)
        
        # Автоматически очищаем статус через 5 секунд
        QTimer.singleShot(5000, lambda: self.status_label.setText(""))
        
        # Обновляем статистику
        self.update_statistics()
    
    def update_statistics(self):
        """Обновление счетчиков статистики."""
        all_notes = self.store.get_all_notes()
        
        total = len(all_notes)
        active = len([n for n in all_notes if not n.deleted])
        pinned = len([n for n in all_notes if not n.deleted and n.pinned])
        deleted = len([n for n in all_notes if n.deleted])
        
        # Формируем текст статистики
        stats_text = f"Всего: {total} | Активных: {active} | Закреплено: {pinned}"
        if deleted > 0:
            stats_text += f" | Удалено: {deleted}"
        
        self.statistics_label.setText(stats_text)
    
    def update_note_info(self):
        """Обновление информации о текущей заметке."""
        if not self.current_note_id:
            self.note_info_label.setText("")
            return
        
        note = self.store.get_note(self.current_note_id)
        if not note:
            self.note_info_label.setText("")
            return
        
        # Подсчет символов и слов
        char_count = len(note.body)
        word_count = len(note.body.split()) if note.body.strip() else 0
        
        # Форматирование даты создания
        try:
            created_date = datetime.fromisoformat(note.last_modified.replace('Z', '+00:00'))
            date_str = created_date.strftime("%d %B %Y")
            # Перевод месяцев на русский
            months_ru = {
                'January': 'января', 'February': 'февраля', 'March': 'марта',
                'April': 'апреля', 'May': 'мая', 'June': 'июня',
                'July': 'июля', 'August': 'августа', 'September': 'сентября',
                'October': 'октября', 'November': 'ноября', 'December': 'декабря'
            }
            for en, ru in months_ru.items():
                date_str = date_str.replace(en, ru)
        except:
            date_str = "неизвестно"
        
        # Форматирование чисел с запятыми
        char_formatted = f"{char_count:,}".replace(',', ' ')
        word_formatted = f"{word_count:,}".replace(',', ' ')
        
        info_text = f"Текущая заметка: {char_formatted} символов, {word_formatted} слов | Дата изменения: {date_str}"
        self.note_info_label.setText(info_text)
    
    def on_sort_changed(self, index):
        """Обработчик изменения режима сортировки."""
        logger.info("Изменена сортировка: %s", self.sort_combo.currentText())
        self.load_notes_list()
    
    def closeEvent(self, event):
        """Обработчик закрытия окна."""
        if self.has_unsaved_changes:
            reply = QMessageBox.question(
                self,
                "Несохраненные изменения",
                "У вас есть несохраненные изменения. Сохранить перед выходом?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Yes:
                self.save_current_note()
                event.accept()
            elif reply == QMessageBox.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
    
    def setup_sync_path(self):
        """Настройка пути к облачной папке синхронизации."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку облачной синхронизации",
            str(Path.home()),
            QFileDialog.ShowDirsOnly
        )
        
        if folder:
            path = Path(folder)
            if self.sync_manager.set_cloud_path(path):
                self.update_status(f"Папка синхронизации: {path.name}")
                logger.info("Настроена папка синхронизации: %s", path)
                
                # Включаем автосинхронизацию при настройке папки
                self.enable_autosync()
                
                return True
            else:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Не удалось установить папку синхронизации"
                )
                return False
        return False
    
    def sync_notes(self):
        """Выполнение синхронизации заметок."""
        # Асинхронная синхронизация (чтобы UI не зависал при длительных операциях
        # вроде скачивания файлов OneDrive). Запускается в отдельном потоке.
        if self._sync_in_progress:
            QMessageBox.information(self, "Синхронизация", "Синхронизация уже выполняется")
            return

        # Проверка настройки облачной папки
        if not self.sync_manager.cloud_path:
            reply = QMessageBox.question(
                self,
                "Настройка синхронизации",
                "Папка облачной синхронизации не настроена.\nХотите выбрать папку?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                if not self.setup_sync_path():
                    return
            else:
                return

        # Сохраняем текущую заметку перед синхронизацией
        if self.has_unsaved_changes and self.current_note_id:
            self.save_current_note()

        # Запускаем фоновый поток синхронизации
        self._sync_in_progress = True
        self._is_manual_sync = True  # Помечаем как ручную синхронизацию
        self.update_status("Синхронизация...")
        self.btn_sync.setEnabled(False)
        self.btn_sync_settings.setEnabled(False)

        def worker():
            try:
                logger.info("Фоновая синхронизация запущена")
                success, synced_count, conflict_count = self.sync_manager.sync()
                # Передаём результат в главный поток через сигнал
                self.sync_signals.completed.emit(success, synced_count, conflict_count)
            except Exception as e:
                logger.error("Ошибка в фоновом потоке синхронизации: %s", e)
                self.sync_signals.error.emit(e)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _on_sync_complete(self, success: bool, synced_count: int, conflict_count: int):
        """Обработчик завершения синхронизации (главный поток)."""
        # Проверяем, была ли это ручная синхронизация
        is_manual = self._is_manual_sync
        
        # ВАЖНО: Сначала разблокируем кнопки, потом показываем диалоги
        # Иначе модальный диалог может заблокировать выполнение finally
        self._sync_in_progress = False
        self._is_manual_sync = False
        self.btn_sync.setEnabled(True)
        self.btn_sync_settings.setEnabled(True)
        
        try:
            if success:
                # Перезагружаем список и текущую заметку (если открыта)
                self.load_notes_list(reload_current_note=True)
                
                if is_manual:
                    # Ручная синхронизация - показываем модальные окна
                    logger.info("Фоновая синхронизация успешна: %d заметок, %d конфликтов", synced_count, conflict_count)
                    
                    if conflict_count > 0:
                        self.update_status(f"Синхронизация: {synced_count} заметок, {conflict_count} конфликтов")
                        QMessageBox.warning(
                            self,
                            "Синхронизация завершена",
                            f"Синхронизировано: {synced_count} заметок\nОбнаружено конфликтов: {conflict_count}"
                        )
                    else:
                        self.update_status(f"Синхронизировано: {synced_count} заметок")
                        QMessageBox.information(
                            self,
                            "Синхронизация завершена",
                            f"Успешно синхронизировано {synced_count} заметок"
                        )
                else:
                    # Автосинхронизация - только статус без модальных окон
                    logger.info("Автосинхронизация успешна: %d заметок, %d конфликтов", synced_count, conflict_count)
                    
                    if conflict_count > 0:
                        self.update_status(f"Автосинхронизация: {synced_count} заметок, {conflict_count} конфликтов")
                    else:
                        self.update_status(f"Автосинхронизация: {synced_count} заметок")
            else:
                if is_manual:
                    self.update_status("Ошибка синхронизации")
                    QMessageBox.critical(self, "Ошибка синхронизации", "Не удалось выполнить синхронизацию.\nПроверьте логи для деталей.")
                else:
                    self.update_status("Ошибка автосинхронизации")
                logger.error("Синхронизация не удалась")
        except Exception as e:
            logger.error("Ошибка в обработчике завершения синхронизации: %s", e)

    def _on_sync_error(self, error: Exception):
        """Обработчик ошибок синхронизации (главный поток)."""
        self.update_status("Ошибка синхронизации")
        QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при синхронизации:\n{error}")
        logger.error("Ошибка синхронизации: %s", error)
        self._sync_in_progress = False
        self.btn_sync.setEnabled(True)
        self.btn_sync_settings.setEnabled(True)
    
    def enable_autosync(self):
        """Включение автоматической синхронизации."""
        if not self.autosync_enabled and self.sync_manager.cloud_path:
            self.autosync_timer.start(self.autosync_interval)
            self.autosync_enabled = True
            logger.info("Автосинхронизация включена (интервал: %d сек)", self.autosync_interval // 1000)
    
    def disable_autosync(self):
        """Отключение автоматической синхронизации."""
        if self.autosync_enabled:
            self.autosync_timer.stop()
            self.autosync_enabled = False
            logger.info("Автосинхронизация отключена")
    
    def auto_sync_notes(self):
        """Автоматическая фоновая синхронизация без модальных окон."""
        # Не запускаем, если уже идёт синхронизация
        if self._sync_in_progress:
            logger.debug("Автосинхронизация пропущена - синхронизация уже выполняется")
            return
        
        # Проверка настройки облачной папки
        if not self.sync_manager.cloud_path:
            logger.debug("Автосинхронизация пропущена - папка не настроена")
            self.disable_autosync()
            return
        
        # Сохраняем текущую заметку перед синхронизацией (если есть изменения)
        if self.has_unsaved_changes and self.current_note_id:
            self.autosave_current_note()
        
        # Запускаем фоновую синхронизацию
        self._sync_in_progress = True
        self._is_manual_sync = False  # Помечаем как автосинхронизацию
        self.update_status("🔄 Автосинхронизация...")
        
        def worker():
            try:
                logger.info("Автосинхронизация запущена")
                success, synced_count, conflict_count = self.sync_manager.sync()
                # Передаём результат в главный поток через тот же сигнал
                self.sync_signals.completed.emit(success, synced_count, conflict_count)
            except Exception as e:
                logger.error("Ошибка в фоновом потоке автосинхронизации: %s", e)
                self.sync_signals.error.emit(e)
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()


def main():
    """Точка входа для запуска GUI приложения."""
    app = QApplication(sys.argv)
    
    # Установка стиля приложения
    app.setStyle("Fusion")
    
    window = NotesApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
