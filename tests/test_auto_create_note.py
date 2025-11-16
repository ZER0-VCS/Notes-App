"""
Тест для проверки автоматического создания заметки при редактировании без выбранной заметки.
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt

# Импортируем модули приложения
sys.path.insert(0, str(Path(__file__).parent.parent))
from gui import NotesApp


def test_auto_create_note_on_edit(qtbot):
    """
    Тест: Автоматическое создание заметки при начале редактирования без выбранной заметки.
    
    Сценарий:
    1. Запустить приложение
    2. Удалить текущую заметку (если выбрана)
    3. Начать вводить текст в пустое поле
    4. Проверить, что заметка автоматически создалась
    5. Проверить, что можно сохранить изменения
    """
    print("\n" + "="*70)
    print("📝 ТЕСТ: АВТОСОЗДАНИЕ ЗАМЕТКИ ПРИ РЕДАКТИРОВАНИИ")
    print("="*70 + "\n")
    
    # Создаём приложение
    app = NotesApp()
    qtbot.addWidget(app)
    app.show()
    qtbot.waitExposed(app)
    
    initial_count = app.notes_list.count()
    print(f"📊 Начальное количество заметок: {initial_count}")
    
    # Тест 1: Создание заметки при редактировании после запуска без выбранной заметки
    print("\n1️⃣ Тест: Редактирование без выбранной заметки")
    
    # Убедимся, что нет выбранной заметки
    # Блокируем сигналы перед очисткой, чтобы не создать заметку преждевременно
    app.title_edit.blockSignals(True)
    app.body_edit.blockSignals(True)
    app.tags_edit.blockSignals(True)
    
    app.current_note_id = None
    app.title_edit.clear()
    app.body_edit.clear()
    app.tags_edit.clear()
    app.btn_delete.setEnabled(False)
    app.has_unsaved_changes = False
    
    # Разблокируем сигналы
    app.title_edit.blockSignals(False)
    app.body_edit.blockSignals(False)
    app.tags_edit.blockSignals(False)
    
    QTest.qWait(100)
    
    print(f"   current_note_id ДО редактирования: {app.current_note_id}")
    assert app.current_note_id is None, "Должна быть None до редактирования"
    
    # Начинаем вводить текст
    print("   Вводим текст в заголовок...")
    app.title_edit.setText("Тестовая заметка")
    QTest.qWait(200)
    
    # Проверяем, что заметка автоматически создалась
    print(f"   current_note_id ПОСЛЕ ввода заголовка: {app.current_note_id}")
    assert app.current_note_id is not None, "Заметка должна автоматически создаться"
    print("   ✅ Заметка автоматически создана")
    
    # Проверяем, что кнопки активны
    assert app.btn_delete.isEnabled(), "Кнопка удаления должна быть активна"
    assert app.btn_save.isEnabled(), "Кнопка сохранения должна быть активна"
    print("   ✅ Кнопки сохранения и удаления активны")
    
    # Проверяем количество заметок
    new_count = app.notes_list.count()
    assert new_count == initial_count + 1, f"Должна добавиться 1 заметка, было {initial_count}, стало {new_count}"
    print(f"   ✅ Количество заметок увеличилось: {initial_count} → {new_count}")
    
    # Тест 2: Редактирование тела заметки
    print("\n2️⃣ Тест: Редактирование тела заметки")
    
    first_note_id = app.current_note_id
    app.body_edit.setText("Содержимое тестовой заметки")
    QTest.qWait(200)
    
    assert app.current_note_id == first_note_id, "ID заметки не должен меняться"
    assert app.has_unsaved_changes, "Должны быть несохраненные изменения"
    print("   ✅ Изменения корректно отслеживаются")
    
    # Сохраняем
    app.save_current_note()
    QTest.qWait(100)
    assert not app.has_unsaved_changes, "После сохранения не должно быть несохраненных изменений"
    print("   ✅ Сохранение работает корректно")
    
    # Тест 3: Удаление заметки и повторное создание при редактировании
    print("\n3️⃣ Тест: Удаление и повторное автосоздание")
    
    # Удаляем заметку программно (без диалога)
    app.autosave_timer.stop()
    app.store.delete_note(app.current_note_id)
    app.current_note_id = None
    
    # Блокируем сигналы и очищаем поля
    app.title_edit.blockSignals(True)
    app.body_edit.blockSignals(True)
    app.tags_edit.blockSignals(True)
    app.title_edit.clear()
    app.body_edit.clear()
    app.tags_edit.clear()
    app.title_edit.blockSignals(False)
    app.body_edit.blockSignals(False)
    app.tags_edit.blockSignals(False)
    
    app.btn_delete.setEnabled(False)
    app.has_unsaved_changes = False
    app.load_notes_list()
    QTest.qWait(100)
    
    print(f"   current_note_id после удаления: {app.current_note_id}")
    assert app.current_note_id is None, "После удаления должна быть None"
    
    # Начинаем вводить новый текст
    print("   Вводим текст после удаления...")
    app.body_edit.setText("Новая заметка после удаления")
    QTest.qWait(200)
    
    print(f"   current_note_id после нового ввода: {app.current_note_id}")
    assert app.current_note_id is not None, "Должна создаться новая заметка"
    print("   ✅ Новая заметка создана автоматически после удаления")
    
    # Тест 4: Проверка с тегами
    print("\n4️⃣ Тест: Автосоздание при вводе тегов")
    
    # Снова удаляем и очищаем
    app.autosave_timer.stop()
    app.store.delete_note(app.current_note_id)
    app.current_note_id = None
    
    app.title_edit.blockSignals(True)
    app.body_edit.blockSignals(True)
    app.tags_edit.blockSignals(True)
    app.title_edit.clear()
    app.body_edit.clear()
    app.tags_edit.clear()
    app.title_edit.blockSignals(False)
    app.body_edit.blockSignals(False)
    app.tags_edit.blockSignals(False)
    
    app.load_notes_list()
    QTest.qWait(100)
    
    # Вводим теги
    print("   Вводим теги...")
    app.tags_edit.setText("тест, автосоздание")
    QTest.qWait(200)
    
    assert app.current_note_id is not None, "Должна создаться заметка при вводе тегов"
    print("   ✅ Заметка создана при вводе тегов")
    
    # Проверяем, что теги сохранились
    note = app.store.get_note(app.current_note_id)
    assert "тест" in note.tags or "автосоздание" in note.tags, "Теги должны быть сохранены"
    print(f"   ✅ Теги сохранены: {note.tags}")
    
    print("\n" + "="*70)
    print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("="*70)
    
    return True


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Создаём фейковый qtbot для ручного запуска
    class FakeQtBot:
        def addWidget(self, widget):
            pass
        def waitExposed(self, widget):
            QTest.qWait(100)
    
    result = test_auto_create_note_on_edit(FakeQtBot())
    
    if result:
        print("\n✅ Все проверки пройдены!")
        sys.exit(0)
    else:
        print("\n❌ Тест провален!")
        sys.exit(1)
