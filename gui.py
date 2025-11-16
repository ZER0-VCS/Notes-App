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
from PySide6.QtGui import QFont, QShortcut, QKeySequence
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
        
        # Список заметок
        self.notes_list = QListWidget()
        self.notes_list.itemClicked.connect(self.on_note_selected)
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
        right_layout.addWidget(self.title_edit)
        
        # Текст заметки
        body_label = QLabel("Текст:")
        right_layout.addWidget(body_label)
        
        self.body_edit = QTextEdit()
        self.body_edit.setPlaceholderText("Введите текст заметки...")
        self.body_edit.setFont(QFont("Arial", 11))
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
        self.btn_sync_settings = QPushButton("⚙️")
        self.btn_sync_settings.setFixedWidth(36)
        self.btn_sync_settings.clicked.connect(self.setup_sync_path)
        self.btn_sync_settings.setToolTip("Изменить папку синхронизации")
        buttons_layout.addWidget(self.btn_sync_settings)

        # Статусная метка
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666666; font-size: 11px;")
        buttons_layout.addWidget(self.status_label)
        
        right_layout.addLayout(buttons_layout)
        
        splitter.addWidget(right_panel)
        
        # Установка пропорций splitter (30% - 70%)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)
        
        main_layout.addWidget(splitter)
        
        # Флаг изменений
        self.has_unsaved_changes = False

        # Флаг синхронизации (предотвращает параллельные запуски)
        self._sync_in_progress = False
    
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
    
    def load_notes_list(self):
        """Загрузка списка заметок в QListWidget."""
        self.notes_list.clear()
        
        notes = self.store.get_all_notes()
        
        # Сортировка по времени изменения (новые сверху)
        notes.sort(key=lambda n: n.last_modified, reverse=True)
        
        for note in notes:
            item = QListWidgetItem(note.title or "(Без заголовка)")
            item.setData(Qt.UserRole, note.id)  # Сохраняем ID заметки
            self.notes_list.addItem(item)
        
        # Обновление статуса
        self.update_status(f"Загружено заметок: {len(notes)}")
    
    def on_note_selected(self, item):
        """Обработчик выбора заметки из списка."""
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
        note_id = item.data(Qt.UserRole)
        self.load_note(note_id)
    
    def load_note(self, note_id):
        """Загрузка заметки в редактор."""
        note = self.store.get_note(note_id)
        
        if note:
            self.current_note_id = note_id
            
            # Блокируем сигналы, чтобы избежать пометки как "измененное"
            self.title_edit.blockSignals(True)
            self.body_edit.blockSignals(True)
            
            self.title_edit.setText(note.title)
            self.body_edit.setText(note.body)
            
            self.title_edit.blockSignals(False)
            self.body_edit.blockSignals(False)
            
            # Активируем кнопки
            self.btn_save.setEnabled(False)
            self.btn_delete.setEnabled(True)
            
            self.has_unsaved_changes = False
            self.update_status(f"Заметка загружена: {note.title}")
    
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
            
            # Обновляем заметку
            success = self.store.update_note(self.current_note_id, title=title, body=body)
            
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
                note_title = self.title_edit.text() or "(Без заголовка)"
                note_id = self.current_note_id
                success = self.store.delete_note(self.current_note_id)
                
                if success:
                    self.update_status(f"Заметка удалена: {note_title}")
                    logger.info("Заметка удалена: %s", note_id[:8])
                    
                    # Очищаем редактор
                    self.current_note_id = None
                    self.title_edit.clear()
                    self.body_edit.clear()
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
        if self.current_note_id:
            self.has_unsaved_changes = True
            self.btn_save.setEnabled(True)
            self.update_status("Есть несохраненные изменения")
    
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
        # ВАЖНО: Сначала разблокируем кнопки, потом показываем диалоги
        # Иначе модальный диалог может заблокировать выполнение finally
        self._sync_in_progress = False
        self.btn_sync.setEnabled(True)
        self.btn_sync_settings.setEnabled(True)
        
        try:
            if success:
                self.load_notes_list()
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
                self.update_status("Ошибка синхронизации")
                QMessageBox.critical(self, "Ошибка синхронизации", "Не удалось выполнить синхронизацию.\nПроверьте логи для деталей.")
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
