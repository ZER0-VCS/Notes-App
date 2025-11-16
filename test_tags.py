"""
Тест для проверки функции тегов/категорий.
Проверяет добавление, сохранение, загрузку и поиск по тегам.
"""

import sys
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from gui import NotesApp


def test_tags():
    """Тест тегов с визуальной обратной связью."""
    print("\n" + "="*70)
    print("🏷️  ТЕСТ ТЕГОВ/КАТЕГОРИЙ")
    print("="*70)
    
    app = QApplication(sys.argv)
    window = NotesApp()
    window.show()
    QApplication.processEvents()
    
    # Тест 1: Создание заметки с тегами
    print("\n1️⃣ Тест: Создание заметки с тегами")
    window.create_new_note()
    QApplication.processEvents()
    
    test_title = "Заметка с тегами"
    test_body = "Эта заметка имеет несколько тегов для тестирования"
    test_tags_text = "работа, важное, python"
    
    window.title_edit.setText(test_title)
    window.body_edit.setPlainText(test_body)
    window.tags_edit.setText(test_tags_text)
    
    window.save_current_note()
    QApplication.processEvents()
    time.sleep(0.5)
    
    note_id = window.current_note_id
    print(f"   Заметка создана с ID: {note_id[:8]}")
    print(f"   Заголовок: '{test_title}'")
    print(f"   Теги: '{test_tags_text}'")
    
    # Проверяем, что теги сохранились в базе
    note = window.store.get_note(note_id)
    if not note:
        print("   ❌ ОШИБКА: Заметка не найдена в базе")
        return False
    
    expected_tags = ["работа", "важное", "python"]
    if note.tags != expected_tags:
        print(f"   ❌ ОШИБКА: Теги не совпадают")
        print(f"      Ожидалось: {expected_tags}")
        print(f"      Получено: {note.tags}")
        return False
    
    print(f"   ✅ Теги сохранены корректно: {note.tags}")
    
    # Тест 2: Загрузка заметки с тегами
    print("\n2️⃣ Тест: Загрузка заметки с тегами")
    
    # Создаём новую заметку, чтобы потом вернуться к первой
    window.create_new_note()
    QApplication.processEvents()
    time.sleep(0.2)
    
    # Загружаем заметку с тегами
    window.load_note(note_id)
    QApplication.processEvents()
    time.sleep(0.2)
    
    loaded_tags_text = window.tags_edit.text()
    print(f"   Загружен текст тегов: '{loaded_tags_text}'")
    
    if loaded_tags_text != test_tags_text:
        print(f"   ❌ ОШИБКА: Текст тегов не совпадает")
        print(f"      Ожидалось: '{test_tags_text}'")
        print(f"      Получено: '{loaded_tags_text}'")
        return False
    
    print("   ✅ Теги загружены корректно")
    
    # Тест 3: Редактирование тегов
    print("\n3️⃣ Тест: Редактирование тегов")
    
    new_tags_text = "работа, срочно, проект"
    window.tags_edit.setText(new_tags_text)
    window.save_current_note()
    QApplication.processEvents()
    time.sleep(0.5)
    
    note = window.store.get_note(note_id)
    expected_new_tags = ["работа", "срочно", "проект"]
    
    if note.tags != expected_new_tags:
        print(f"   ❌ ОШИБКА: Обновлённые теги не совпадают")
        print(f"      Ожидалось: {expected_new_tags}")
        print(f"      Получено: {note.tags}")
        return False
    
    print(f"   ✅ Теги обновлены: {note.tags}")
    
    # Тест 4: Поиск по тегам
    print("\n4️⃣ Тест: Поиск по тегам")
    
    # Создаём ещё несколько заметок с разными тегами
    test_notes = [
        ("Задача 1", "Первая задача", "работа, срочно"),
        ("Задача 2", "Вторая задача", "личное, покупки"),
        ("Задача 3", "Третья задача", "работа, проект"),
    ]
    
    for title, body, tags in test_notes:
        window.create_new_note()
        QApplication.processEvents()
        window.title_edit.setText(title)
        window.body_edit.setPlainText(body)
        window.tags_edit.setText(tags)
        window.save_current_note()
        QApplication.processEvents()
        time.sleep(0.1)
    
    window.load_notes_list()
    QApplication.processEvents()
    time.sleep(0.2)
    
    total_notes = window.notes_list.count()
    print(f"   Всего заметок: {total_notes}")
    
    # Поиск по тегу "работа"
    window.search_box.setText("работа")
    QApplication.processEvents()
    time.sleep(0.2)
    
    visible = sum(1 for i in range(window.notes_list.count()) if not window.notes_list.item(i).isHidden())
    print(f"   Поиск 'работа': найдено {visible} заметок")
    
    if visible == 0:
        print("   ❌ ОШИБКА: Не найдено заметок с тегом 'работа'")
        return False
    
    print("   ✅ Поиск по тегам работает")
    
    # Поиск по тегу "личное"
    window.search_box.setText("личное")
    QApplication.processEvents()
    time.sleep(0.2)
    
    visible_personal = sum(1 for i in range(window.notes_list.count()) if not window.notes_list.item(i).isHidden())
    print(f"   Поиск 'личное': найдено {visible_personal} заметок")
    
    if visible_personal == 0:
        print("   ❌ ОШИБКА: Не найдено заметок с тегом 'личное'")
        return False
    
    print("   ✅ Поиск по разным тегам работает")
    
    # Тест 5: Получение всех тегов
    print("\n5️⃣ Тест: Получение всех уникальных тегов")
    
    all_tags = window.store.get_all_tags()
    print(f"   Все уникальные теги: {all_tags}")
    
    expected_tags_set = {"работа", "срочно", "проект", "личное", "покупки"}
    actual_tags_set = set(all_tags)
    
    if not expected_tags_set.issubset(actual_tags_set):
        print(f"   ❌ ОШИБКА: Не все теги найдены")
        print(f"      Ожидалось (минимум): {expected_tags_set}")
        print(f"      Получено: {actual_tags_set}")
        return False
    
    print(f"   ✅ Найдено {len(all_tags)} уникальных тегов")
    
    # Тест 6: Автосохранение с тегами
    print("\n6️⃣ Тест: Автосохранение с тегами")
    
    window.create_new_note()
    QApplication.processEvents()
    
    window.title_edit.setText("Тест автосохранения с тегами")
    window.body_edit.setPlainText("Проверка автосохранения")
    window.tags_edit.setText("тест, автосохранение")
    
    QApplication.processEvents()
    time.sleep(0.5)
    
    autosave_note_id = window.current_note_id
    
    # Ждём автосохранение
    print("   Ожидание автосохранения (6 секунд)...")
    for i in range(12):
        time.sleep(0.5)
        QApplication.processEvents()
        
        if not window.has_unsaved_changes:
            print(f"   ✅ Автосохранение сработало на {(i+1)*0.5:.1f} сек")
            break
    
    # Проверяем теги в базе
    note = window.store.get_note(autosave_note_id)
    expected_autosave_tags = ["тест", "автосохранение"]
    
    if note.tags != expected_autosave_tags:
        print(f"   ❌ ОШИБКА: Теги не сохранились при автосохранении")
        print(f"      Ожидалось: {expected_autosave_tags}")
        print(f"      Получено: {note.tags}")
        return False
    
    print(f"   ✅ Теги сохранены автосохранением: {note.tags}")
    
    # Очистка поиска
    window.search_box.clear()
    QApplication.processEvents()
    
    print("\n" + "="*70)
    print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("="*70)
    print("\nℹ️ Примечание: Теги работают корректно во всех режимах")
    
    # Закрываем через 2 секунды
    QTimer.singleShot(2000, app.quit)
    app.exec()
    
    return True


if __name__ == "__main__":
    success = test_tags()
    sys.exit(0 if success else 1)
