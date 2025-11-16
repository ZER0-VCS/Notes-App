"""
Тест UI улучшений:
1. Длинные заголовки отображают начало, а не конец
2. Spacing между заметками в списке
3. Подсветка результатов поиска (📌 заголовок / 📄 текст / 🏷️ тег)
"""

import sys
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from gui import NotesApp


def test_ui_improvements():
    """Тест UI улучшений."""
    print("\n" + "="*70)
    print("🎨 ТЕСТ UI УЛУЧШЕНИЙ")
    print("="*70)
    
    app = QApplication(sys.argv)
    window = NotesApp()
    window.show()
    QApplication.processEvents()
    
    # Тест 1: Длинные заголовки - начало видно
    print("\n1️⃣ Тест: Длинные заголовки отображают начало")
    
    long_title = "Это очень длинный заголовок который не помещается в поле ввода и должен показывать начало а не конец"
    
    window.create_new_note()
    QApplication.processEvents()
    
    window.title_edit.setText(long_title)
    window.save_current_note()
    QApplication.processEvents()
    time.sleep(0.3)
    
    note_id = window.current_note_id
    
    # Перезагружаем заметку
    window.create_new_note()
    QApplication.processEvents()
    window.load_note(note_id)
    QApplication.processEvents()
    time.sleep(0.2)
    
    cursor_pos = window.title_edit.cursorPosition()
    print(f"   Заголовок: '{long_title[:50]}...'")
    print(f"   Позиция курсора: {cursor_pos}")
    print(f"   Видимый текст начинается с: '{window.title_edit.text()[:20]}...'")
    
    if cursor_pos != 0:
        print(f"   ❌ ОШИБКА: Курсор не в начале (позиция {cursor_pos})")
        return False
    
    print("   ✅ Курсор установлен в начало заголовка")
    
    # Тест 2: Spacing между заметками
    print("\n2️⃣ Тест: Spacing между заметками в списке")
    
    spacing = window.notes_list.spacing()
    print(f"   Spacing между заметками: {spacing}px")
    
    if spacing < 2:
        print(f"   ❌ ОШИБКА: Spacing слишком маленький ({spacing}px)")
        return False
    
    print(f"   ✅ Spacing установлен корректно ({spacing}px)")
    
    # Тест 3: Подсветка результатов поиска
    print("\n3️⃣ Тест: Подсветка результатов поиска")
    
    # Создаём заметки с разными типами совпадений
    test_notes = [
        ("Python Tutorial", "Изучаем основы программирования", "обучение, курс"),
        ("Встреча завтра", "Обсудить проект с командой", "работа, встреча"),
        ("Список покупок", "Молоко, хлеб, яйца", "покупки, дом"),
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
    time.sleep(0.3)
    
    # Проверяем индикаторы для разных типов поиска
    
    # A) Поиск по заголовку (должен быть 📌)
    print("\n   A) Поиск 'Python' (в заголовке)")
    window.search_box.setText("Python")
    QApplication.processEvents()
    time.sleep(0.2)
    
    found_title_indicator = False
    for i in range(window.notes_list.count()):
        item = window.notes_list.item(i)
        if not item.isHidden():
            text = item.text()
            print(f"      Найдено: '{text}'")
            if "📌" in text:
                found_title_indicator = True
                print("      ✅ Индикатор заголовка (📌) присутствует")
    
    if not found_title_indicator:
        print("      ❌ ОШИБКА: Индикатор заголовка не найден")
        return False
    
    # B) Поиск по тексту (должен быть 📄)
    print("\n   B) Поиск 'молоко' (в тексте)")
    window.search_box.setText("молоко")
    QApplication.processEvents()
    time.sleep(0.2)
    
    found_body_indicator = False
    for i in range(window.notes_list.count()):
        item = window.notes_list.item(i)
        if not item.isHidden():
            text = item.text()
            print(f"      Найдено: '{text}'")
            if "📄" in text:
                found_body_indicator = True
                print("      ✅ Индикатор текста (📄) присутствует")
    
    if not found_body_indicator:
        print("      ❌ ОШИБКА: Индикатор текста не найден")
        return False
    
    # C) Поиск по тегу (должен быть 🏷️)
    print("\n   C) Поиск 'работа' (в тегах)")
    window.search_box.setText("работа")
    QApplication.processEvents()
    time.sleep(0.2)
    
    found_tag_indicator = False
    for i in range(window.notes_list.count()):
        item = window.notes_list.item(i)
        if not item.isHidden():
            text = item.text()
            print(f"      Найдено: '{text}'")
            if "🏷️" in text:
                found_tag_indicator = True
                print("      ✅ Индикатор тега (🏷️) присутствует")
    
    if not found_tag_indicator:
        print("      ❌ ОШИБКА: Индикатор тега не найден")
        return False
    
    # D) Очистка поиска - индикаторы должны исчезнуть
    print("\n   D) Очистка поиска (индикаторы исчезают)")
    window.search_box.clear()
    QApplication.processEvents()
    time.sleep(0.2)
    
    indicators_removed = True
    for i in range(window.notes_list.count()):
        item = window.notes_list.item(i)
        text = item.text()
        if "📌" in text or "📄" in text or "🏷️" in text:
            print(f"      ❌ Индикатор остался: '{text}'")
            indicators_removed = False
    
    if not indicators_removed:
        print("      ❌ ОШИБКА: Индикаторы не удалены после очистки")
        return False
    
    print("      ✅ Индикаторы удалены после очистки поиска")
    
    print("\n" + "="*70)
    print("🎉 ВСЕ ТЕСТЫ UI УЛУЧШЕНИЙ ПРОЙДЕНЫ!")
    print("="*70)
    print("\n📌 Заголовок | 📄 Текст | 🏷️ Тег - индикаторы работают корректно")
    
    # Закрываем через 2 секунды
    QTimer.singleShot(2000, app.quit)
    app.exec()
    
    return True


if __name__ == "__main__":
    success = test_ui_improvements()
    sys.exit(0 if success else 1)
