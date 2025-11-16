"""
Тест взаимодействия синхронизации и поиска.
Проверяет, что при синхронизации с активным поиском не появляется false-positive has_unsaved_changes.
"""

import sys
import time
import tempfile
import shutil
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt

# Импортируем модули приложения
sys.path.insert(0, str(Path(__file__).parent.parent))
from gui import NotesApp
from notes import NoteStore


def test_sync_search_no_false_changes(qtbot):
    """
    Тест: Синхронизация с активным поиском не должна вызывать has_unsaved_changes.
    
    Сценарий:
    1. Создать несколько заметок
    2. Включить поиск и найти заметку
    3. Открыть найденную заметку
    4. Выполнить синхронизацию
    5. Проверить, что has_unsaved_changes = False
    """
    print("\n" + "="*70)
    print("🔍 ТЕСТ: СИНХРОНИЗАЦИЯ + ПОИСК БЕЗ FALSE-POSITIVE ИЗМЕНЕНИЙ")
    print("="*70 + "\n")
    
    # Создаём временную директорию для облака
    temp_cloud = tempfile.mkdtemp(prefix="notes_test_cloud_")
    
    try:
        # Создаём приложение (использует стандартное хранилище)
        app = NotesApp()
        qtbot.addWidget(app)
        app.show()
        qtbot.waitForWindowShown(app)
        
        print(f"📊 Начальное количество заметок: {app.notes_list.count()}")
        
        # 1. Создаём тестовые заметки с уникальным тегом
        print("\n📝 Создаём тестовые заметки...")
        unique_tag = f"TESTXYZ{time.time()}"
        test_notes = [
            (f"Заметка {unique_tag} #1", f"Тестовое содержание {unique_tag}"),
            (f"Заметка {unique_tag} #2", f"Ещё тестовое содержание {unique_tag}"),
            ("Другая тема", "Это заметка о чём-то другом"),
        ]
        
        for title, body in test_notes:
            app.create_new_note()
            QTest.qWait(100)
            app.title_edit.setText(title)
            app.body_edit.setText(body)
            app.save_current_note()
            QTest.qWait(100)
        
        initial_count = app.notes_list.count()
        print(f"✅ Создано {len(test_notes)} заметок. Всего в базе: {initial_count}")
        
        # 2. Настраиваем синхронизацию
        print("\n🔄 Настройка синхронизации...")
        app.sync_manager.cloud_path = Path(temp_cloud)
        app.enable_autosync()
        print(f"✅ Синхронизация настроена: {temp_cloud}")
        
        # 3. Выполняем первую синхронизацию
        print("\n📤 Первая синхронизация...")
        app._is_manual_sync = False  # Имитируем автосинхронизацию
        success, synced_count, conflict_count = app.sync_manager.sync()
        app._on_sync_complete(success, synced_count, conflict_count)
        QTest.qWait(500)
        print(f"✅ Первая синхронизация: {synced_count} заметок, {conflict_count} конфликтов")
        
        # 4. Включаем поиск по уникальному тегу
        print(f"\n🔍 Включаем поиск по '{unique_tag}'...")
        app.search_box.setText(unique_tag)
        app.filter_notes(unique_tag)
        QTest.qWait(200)
        
        visible_count = sum(1 for i in range(app.notes_list.count()) 
                           if not app.notes_list.item(i).isHidden())
        print(f"   Найдено заметок: {visible_count}")
        assert visible_count == 2, f"Должно быть найдено 2 заметки с '{unique_tag}', найдено: {visible_count}"
        
        # 5. Открываем первую найденную заметку
        print("\n📄 Открываем первую найденную заметку...")
        for i in range(app.notes_list.count()):
            item = app.notes_list.item(i)
            if not item.isHidden():
                app.notes_list.setCurrentItem(item)
                app.on_note_selected(item)
                QTest.qWait(200)
                break
        
        print(f"   Открыта заметка: {app.title_edit.text()}")
        print(f"   has_unsaved_changes ДО синхронизации: {app.has_unsaved_changes}")
        assert not app.has_unsaved_changes, "До синхронизации не должно быть несохранённых изменений"
        
        # 6. Выполняем вторую синхронизацию с открытой заметкой и активным поиском
        print("\n🔄 Синхронизация с активным поиском и открытой заметкой...")
        app._is_manual_sync = False  # Имитируем автосинхронизацию
        success, synced_count, conflict_count = app.sync_manager.sync()
        app._on_sync_complete(success, synced_count, conflict_count)
        QTest.qWait(500)
        print(f"✅ Вторая синхронизация: {synced_count} заметок, {conflict_count} конфликтов")
        
        # 7. Проверяем, что has_unsaved_changes = False
        print(f"\n✅ has_unsaved_changes ПОСЛЕ синхронизации: {app.has_unsaved_changes}")
        assert not app.has_unsaved_changes, \
            "ОШИБКА: После синхронизации появился false-positive has_unsaved_changes!"
        
        # 8. Переключаемся на другую найденную заметку
        print("\n🔄 Переключаемся на другую найденную заметку...")
        found_another = False
        current_note_id = app.current_note_id
        
        for i in range(app.notes_list.count()):
            item = app.notes_list.item(i)
            if not item.isHidden():
                note_id = item.data(Qt.UserRole)
                if note_id != current_note_id:
                    app.notes_list.setCurrentItem(item)
                    app.on_note_selected(item)
                    QTest.qWait(200)
                    found_another = True
                    break
        
        assert found_another, "Не удалось найти вторую заметку"
        print(f"   Переключились на: {app.title_edit.text()}")
        print(f"   has_unsaved_changes после переключения: {app.has_unsaved_changes}")
        assert not app.has_unsaved_changes, \
            "ОШИБКА: После переключения между найденными заметками появился false-positive!"
        
        # 9. Выполняем третью синхронизацию
        print("\n🔄 Третья синхронизация...")
        app._is_manual_sync = False
        success, synced_count, conflict_count = app.sync_manager.sync()
        app._on_sync_complete(success, synced_count, conflict_count)
        QTest.qWait(500)
        print(f"✅ Третья синхронизация: {synced_count} заметок, {conflict_count} конфликтов")
        
        print(f"\n✅ has_unsaved_changes после третьей синхронизации: {app.has_unsaved_changes}")
        assert not app.has_unsaved_changes, \
            "ОШИБКА: После третьей синхронизации появился false-positive has_unsaved_changes!"
        
        print("\n" + "="*70)
        print("🎉 ТЕСТ ПРОЙДЕН УСПЕШНО!")
        print("="*70)
        
        return True
        
    finally:
        # Очистка временной директории
        if Path(temp_cloud).exists():
            shutil.rmtree(temp_cloud)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Создаём фейковый qtbot для ручного запуска
    class FakeQtBot:
        def addWidget(self, widget):
            pass
        def waitForWindowShown(self, widget):
            QTest.qWait(100)
    
    result = test_sync_search_no_false_changes(FakeQtBot())
    
    if result:
        print("\n✅ Все проверки пройдены!")
        sys.exit(0)
    else:
        print("\n❌ Тест провален!")
        sys.exit(1)
