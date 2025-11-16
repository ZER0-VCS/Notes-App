"""
Графический интерфейс для приложения заметок.
Использует PySide6 (Qt) для создания desktop GUI.
"""

import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLineEdit, QTextEdit, QPushButton,
    QSplitter, QMessageBox, QLabel, QFileDialog
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
import threading
from PySide6.QtGui import QFont, QShortcut, QKeySequence, QTextCharFormat, QColor, QTextCursor
from notes import Note, NoteStore
from sync import SyncManager

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
        self.search_box.setPlaceholderText("🔍 Поиск по заголовку и тексту...")
        self.search_box.textChanged.connect(self.filter_notes)
        self.search_box.setClearButtonEnabled(True)  # Кнопка очистки
        left_layout.addWidget(self.search_box)
        
        # Метка с количеством результатов
        self.search_results_label = QLabel("")
        self.search_results_label.setStyleSheet("color: #666666; font-size: 10px; padding: 2px;")
        left_layout.addWidget(self.search_results_label)
        
        # Список заметок
        self.notes_list = QListWidget()
        self.notes_list.itemClicked.connect(self.on_note_selected)
        # Ограничение ширины для предотвращения растягивания окна
        self.notes_list.setMaximumWidth(400)
        # Добавляем spacing между элементами списка
        self.notes_list.setSpacing(4)
        left_layout.addWidget(self.notes_list)
        
        # Кнопка "Создать новую заметку"
        self.btn_new = QPushButton("➕ Создать заметку")
        self.btn_new.clicked.connect(self.create_new_note)
        self.btn_new.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
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
        
        # Панель кнопок
        buttons_layout = QHBoxLayout()
        
        self.btn_save = QPushButton("💾 Сохранить")
        self.btn_save.clicked.connect(self.save_current_note)
        self.btn_save.setEnabled(False)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        buttons_layout.addWidget(self.btn_save)
        
        self.btn_delete = QPushButton("🗑️ Удалить")
        self.btn_delete.clicked.connect(self.delete_current_note)
        self.btn_delete.setEnabled(False)
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        buttons_layout.addWidget(self.btn_delete)
        
        buttons_layout.addStretch()
        
        # Кнопка синхронизации
        self.btn_sync = QPushButton("🔄 Синхронизировать")
        self.btn_sync.clicked.connect(self.sync_notes)
        self.btn_sync.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        buttons_layout.addWidget(self.btn_sync)

        # Кнопка настроек синхронизации (смена папки) - всегда доступна
        self.btn_sync_settings = QPushButton("📁")
        self.btn_sync_settings.setFixedWidth(36)
        self.btn_sync_settings.clicked.connect(self.setup_sync_path)
        self.btn_sync_settings.setToolTip("Изменить папку синхронизации")
        buttons_layout.addWidget(self.btn_sync_settings)
        
        right_layout.addLayout(buttons_layout)
        
        # Статусная метка внизу (отдельная строка чтобы не сдвигать кнопки)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666666; font-size: 11px; padding: 5px;")
        self.status_label.setWordWrap(True)
        self.status_label.setMaximumHeight(40)
        right_layout.addWidget(self.status_label)
        
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
        
        # Таймер автосохранения
        self.autosave_timer = QTimer()
        self.autosave_timer.setSingleShot(True)  # Однократный запуск после каждого изменения
        self.autosave_timer.timeout.connect(self.autosave_current_note)
        self.autosave_delay = 5000  # 5 секунд в миллисекундах
        
        # Таймер автосинхронизации
        self.autosync_timer = QTimer()
        self.autosync_timer.timeout.connect(self.auto_sync_notes)
        self.autosync_interval = 60000  # 60 секунд в миллисекундах
        self.autosync_enabled = False  # По умолчанию выключена
        
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
    
    def load_notes_list(self, reload_current_note: bool = False):
        """Загрузка списка заметок в QListWidget.
        
        Args:
            reload_current_note: Если True, перезагружает текущую открытую заметку после обновления списка
        """
        # Сохраняем ID текущей заметки для возможной перезагрузки
        current_note_id = self.current_note_id if reload_current_note else None
        
        self.notes_list.clear()
        
        notes = self.store.get_all_notes()
        
        # Сортировка по времени изменения (новые сверху)
        notes.sort(key=lambda n: n.last_modified, reverse=True)
        
        for note in notes:
            # Обрезаем длинные названия для списка
            title = note.title or "(Без заголовка)"
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
                # Очищаем выделение в заголовке
                self.title_edit.deselect()
                
                # Очищаем выделение в теле заметки
                cursor = self.body_edit.textCursor()
                cursor.clearSelection()
                self.body_edit.setTextCursor(cursor)
                
                # Очищаем выделение в тегах
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
            self.search_results_label.setText(f"❌ Ничего не найдено")
        elif visible_count == 1:
            self.search_results_label.setText(f"✅ Найдена 1 заметка")
        else:
            self.search_results_label.setText(f"✅ Найдено заметок: {visible_count}")
    
    def focus_search(self):
        """Установка фокуса на поле поиска (Ctrl+F)."""
        self.search_box.setFocus()
        self.search_box.selectAll()
        logger.info("Фокус установлен на поле поиска")
    
    def highlight_text_in_field(self, text_edit, search_text: str, scroll_to_first: bool = False):
        """Подсветка найденного текста в текстовом поле желтым цветом.
        
        Args:
            text_edit: QTextEdit или QLineEdit для подсветки
            search_text: Текст для поиска
            scroll_to_first: Прокручивать к первому совпадению
        """
        if not search_text:
            return
        
        # Получаем текст в зависимости от типа поля
        from PySide6.QtWidgets import QLineEdit, QTextEdit
        if isinstance(text_edit, QLineEdit):
            text = text_edit.text()
        else:
            text = text_edit.toPlainText()
        
        if not text:
            return
        
        # Для QLineEdit используем QPalette
        if isinstance(text_edit, QLineEdit):
            from PySide6.QtGui import QPalette
            from PySide6.QtCore import Qt
            
            text_lower = text.lower()
            search_lower = search_text.lower()
            
            if search_lower in text_lower:
                # Находим позицию первого совпадения
                pos = text_lower.find(search_lower)
                # Выделяем текст
                text_edit.setSelection(pos, len(search_text))
        else:
            # Для QTextEdit выделяем текст (как в QLineEdit)
            text_lower = text.lower()
            search_lower = search_text.lower()
            
            # Находим первое совпадение
            pos = text_lower.find(search_lower)
            if pos != -1:
                # Создаём курсор и выделяем найденный текст
                cursor = text_edit.textCursor()
                cursor.setPosition(pos)
                cursor.setPosition(pos + len(search_text), QTextCursor.MoveMode.KeepAnchor)
                text_edit.setTextCursor(cursor)
                
                # Прокручиваем к найденному тексту если нужно
                if scroll_to_first:
                    text_edit.ensureCursorVisible()
    
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
            
            self.has_unsaved_changes = False
            self.update_status(f"Заметка загружена: {note.title}")
            
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
            self.update_status("⚠️ Ошибка автосохранения")
    
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
                    self.has_unsaved_changes = False
                    
                    # Обновляем список
                    self.load_notes_list()
            
            except Exception as e:
                logger.error("Ошибка при удалении заметки: %s", e)
                QMessageBox.critical(
                    self,
                    "Ошибка удаления",
                    f"Не удалось удалить заметку:\n{e}"
                )
    
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
                
                logger.info("Автоматически создана новая заметка: %s", new_note.id[:8])
                self.update_status("Создана новая заметка")
            except Exception as e:
                logger.error("Ошибка при автоматическом создании заметки: %s", e)
                return
        
        self.has_unsaved_changes = True
        self.btn_save.setEnabled(True)
        self.update_status("Есть несохраненные изменения")
        
        # Перезапускаем таймер автосохранения
        self.autosave_timer.stop()  # Останавливаем предыдущий таймер
        self.autosave_timer.start(self.autosave_delay)  # Запускаем новый отсчёт
    
    def update_status(self, message):
        """Обновление статусного сообщения."""
        self.status_label.setText(message)
        
        # Автоматически очищаем статус через 5 секунд
        QTimer.singleShot(5000, lambda: self.status_label.setText(""))
    
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
                            f"Синхронизировано: {synced_count} заметок\n⚠️ Обнаружено конфликтов: {conflict_count}\n\nЗаметки с конфликтами помечены префиксом ⚠️"
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
                        self.update_status(f"⚠️ Автосинхронизация: {synced_count} заметок, {conflict_count} конфликтов")
                    else:
                        self.update_status(f"✅ Автосинхронизация: {synced_count} заметок")
            else:
                if is_manual:
                    self.update_status("Ошибка синхронизации")
                    QMessageBox.critical(self, "Ошибка синхронизации", "Не удалось выполнить синхронизацию.\nПроверьте логи для деталей.")
                else:
                    self.update_status("⚠️ Ошибка автосинхронизации")
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
