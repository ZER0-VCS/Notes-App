"""
Тест для проверки улучшений UI версии 0.4.0.
Проверяет: отображение начала длинных заголовков, отступы, подсветку при поиске.
"""

import sys
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from gui import NotesApp


def test_ui_improvements():
    """Тест улучшений UI с визуальной обратной связью."""
    print("\n" + "="*70)
    print("🎨 ТЕСТ УЛУЧШЕНИЙ UI v0.4.0")
    print("="*70)
    
    app = QApplication(sys.argv)
    window = NotesApp()
    window.show()
    QApplication.processEvents()
    
    # Тест 1: Отображение длинного заголовка (начало вместо конца)
    print("\n1️⃣ Тест: Отображение начала длинного заголовка")
    
    long_title = "Это очень длинный заголовок заметки который должен быть обрезан и показывать начало а не конец"
    window.create_new_note()
    QApplication.processEvents()
    window.title_edit.setText(long_title)
    window.body_edit.setPlainText("Тестовый текст")
    window.save_current_note()
    QApplication.processEvents()
    time.sleep(0.5)
    
    # Проверяем, что в списке отображается начало
    first_item = window.notes_list.item(0)
    displayed_text = first_item.text()
    
    print(f"   Оригинал: '{long_title[:60]}...'")
    print(f"   В списке: '{displayed_text}'")
    
    if displayed_text.startswith("Это очень длинный"):
        print("   ✅ Отображается начало заголовка")
    else:
        print("   ❌ ОШИБКА: Отображается не начало заголовка")
        return False
    
    # Тест 2: Проверка отступов между заметками
    print("\n2️⃣ Тест: Отступы между заметками")
    
    spacing = window.notes_list.spacing()
    print(f"   Отступ между заметками: {spacing}px")
    
    if spacing >= 4:
        print("   ✅ Отступы настроены корректно")
    else:
        print("   ❌ ОШИБКА: Отступы отсутствуют или недостаточны")
        return False
    
    # Тест 3: Подсветка найденных сегментов
    print("\n3️⃣ Тест: Подсветка найденных сегментов при поиске")
    
    # Создаём заметки для поиска
    test_notes = [
        ("Заметка про Python", "Изучаем Python", "программирование, python"),
        ("Список покупок", "Купить молоко и хлеб", "личное, дом"),
        ("Рабочая задача", "Завершить проект до пятницы", "работа, срочно"),
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
    
    # Поиск по тегу "работа"
    print("\n   📌 Поиск 'работа' (должен найти в теге)")
    window.search_box.setText("работа")
    QApplication.processEvents()
    time.sleep(0.3)
    
    # Проверяем подсказки у найденных заметок
    found_with_highlight = False
    for i in range(window.notes_list.count()):
        item = window.notes_list.item(i)
        if not item.isHidden():
            tooltip = item.toolTip()
            if "Найдено в:" in tooltip and "🏷️ тег" in tooltip:
                found_with_highlight = True
                print(f"   ✅ Найдена заметка с подсветкой")
                print(f"      Tooltip: {tooltip[:80]}...")
                break
    
    if not found_with_highlight:
        print("   ❌ ОШИБКА: Подсветка найденных сегментов не работает")
        return False
    
    # Поиск по заголовку
    print("\n   📌 Поиск 'Python' (должен найти в заголовке)")
    window.search_box.setText("Python")
    QApplication.processEvents()
    time.sleep(0.3)
    
    found_title_highlight = False
    for i in range(window.notes_list.count()):
        item = window.notes_list.item(i)
        if not item.isHidden():
            tooltip = item.toolTip()
            if "Найдено в:" in tooltip and "📝 заголовок" in tooltip:
                found_title_highlight = True
                print(f"   ✅ Найдена заметка с подсветкой в заголовке")
                break
    
    if not found_title_highlight:
        print("   ❌ ОШИБКА: Подсветка заголовка не работает")
        return False
    
    # Поиск по тексту
    print("\n   📌 Поиск 'молоко' (должен найти в тексте)")
    window.search_box.setText("молоко")
    QApplication.processEvents()
    time.sleep(0.3)
    
    found_body_highlight = False
    for i in range(window.notes_list.count()):
        item = window.notes_list.item(i)
        if not item.isHidden():
            tooltip = item.toolTip()
            if "Найдено в:" in tooltip and "📄 текст" in tooltip:
                found_body_highlight = True
                print(f"   ✅ Найдена заметка с подсветкой в тексте")
                break
    
    if not found_body_highlight:
        print("   ❌ ОШИБКА: Подсветка текста не работает")
        return False
    
    print("\n" + "="*70)
    print("🎉 ВСЕ ТЕСТЫ УЛУЧШЕНИЙ UI ПРОЙДЕНЫ УСПЕШНО!")
    print("="*70)
    print("\n✨ Проверенные улучшения:")
    print("   • Отображение начала длинных заголовков")
    print("   • Отступы между заметками (4px)")
    print("   • Подсветка найденных сегментов:")
    print("     - 📝 Заголовок")
    print("     - 📄 Текст")
    print("     - 🏷️ Теги")
    
    # Закрываем через 2 секунды
    QTimer.singleShot(2000, app.quit)
    app.exec()
    
    return True


if __name__ == "__main__":
    success = test_ui_improvements()
    sys.exit(0 if success else 1)
