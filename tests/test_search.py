"""
Тест для проверки функции поиска заметок.
Проверяет фильтрацию по заголовку и тексту, счётчик результатов, горячую клавишу Ctrl+F.
"""

import sys
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt
from PySide6.QtTest import QTest
from gui import NotesApp


def test_search():
    """Тест поиска с визуальной обратной связью."""
    print("\n" + "="*70)
    print("🔍 ТЕСТ ПОИСКА ПО ЗАМЕТКАМ")
    print("="*70)
    
    app = QApplication(sys.argv)
    window = NotesApp()
    window.show()
    QApplication.processEvents()
    
    # Получаем начальное количество заметок
    initial_count = window.notes_list.count()
    print(f"\n📊 Начальное количество заметок: {initial_count}")
    
    # Создаём тестовые заметки для поиска
    print("\n📝 Создаём тестовые заметки для поиска...")
    test_notes = [
        ("Python Tutorial", "Изучаем основы программирования на Python"),
        ("JavaScript Guide", "Современный JavaScript ES6+"),
        ("Список покупок", "Молоко, хлеб, яйца, сыр"),
        ("Встреча с командой", "Обсудить новый проект и распределить задачи"),
    ]
    
    for title, body in test_notes:
        window.create_new_note()
        QApplication.processEvents()
        window.title_edit.setText(title)
        window.body_edit.setPlainText(body)
        window.save_current_note()
        QApplication.processEvents()
        time.sleep(0.1)
    
    window.load_notes_list()
    QApplication.processEvents()
    time.sleep(0.2)
    
    total_count = window.notes_list.count()
    print(f"✅ Создано {len(test_notes)} тестовых заметок. Всего в базе: {total_count}")
    
    # Тест 1: Проверка видимости всех заметок без фильтра
    print("\n1️⃣ Тест: Все заметки видимы без фильтра")
    visible = sum(1 for i in range(window.notes_list.count()) if not window.notes_list.item(i).isHidden())
    print(f"   Видимых заметок: {visible}/{total_count}")
    
    if visible != total_count:
        print("❌ ОШИБКА: Не все заметки видимы")
        return False
    
    print("   ✅ Все заметки видимы")
    
    # Тест 2: Поиск по заголовку
    print("\n2️⃣ Тест: Поиск 'Python' (должен найти в заголовке)")
    window.search_box.setText("Python")
    QApplication.processEvents()
    time.sleep(0.2)
    
    visible = sum(1 for i in range(window.notes_list.count()) if not window.notes_list.item(i).isHidden())
    print(f"   Видимых заметок: {visible}")
    print(f"   Текст результатов: '{window.search_results_label.text()}'")
    
    if visible == 0:
        print("   ❌ ОШИБКА: Ничего не найдено")
        return False
    
    print("   ✅ Найдены заметки с 'Python'")
    
    # Тест 3: Поиск по тексту
    print("\n3️⃣ Тест: Поиск 'молоко' (должен найти в тексте)")
    window.search_box.setText("молоко")
    QApplication.processEvents()
    time.sleep(0.2)
    
    visible = sum(1 for i in range(window.notes_list.count()) if not window.notes_list.item(i).isHidden())
    print(f"   Видимых заметок: {visible}")
    print(f"   Текст результатов: '{window.search_results_label.text()}'")
    
    if visible == 0:
        print("   ❌ ОШИБКА: Ничего не найдено")
        return False
    
    print("   ✅ Найдены заметки с 'молоко' в тексте")
    
    # Тест 4: Поиск несуществующего текста
    print("\n4️⃣ Тест: Поиск 'НЕСУЩЕСТВУЮЩИЙТЕКСТ123' (не должен ничего найти)")
    window.search_box.setText("НЕСУЩЕСТВУЮЩИЙТЕКСТ123")
    QApplication.processEvents()
    time.sleep(0.2)
    
    visible = sum(1 for i in range(window.notes_list.count()) if not window.notes_list.item(i).isHidden())
    print(f"   Видимых заметок: {visible}")
    print(f"   Текст результатов: '{window.search_results_label.text()}'")
    
    if visible != 0:
        print("   ❌ ОШИБКА: Найдены заметки для несуществующего запроса")
        return False
    
    if "не найдено" not in window.search_results_label.text().lower():
        print(f"   ❌ ОШИБКА: Неверное сообщение: '{window.search_results_label.text()}'")
        return False
    
    print("   ✅ Корректно показано 'Ничего не найдено'")
    
    # Тест 5: Очистка поиска
    print("\n5️⃣ Тест: Очистка поиска (все заметки снова видимы)")
    window.search_box.clear()
    QApplication.processEvents()
    time.sleep(0.2)
    
    visible = sum(1 for i in range(window.notes_list.count()) if not window.notes_list.item(i).isHidden())
    print(f"   Видимых заметок: {visible}/{total_count}")
    
    if visible != total_count:
        print("   ❌ ОШИБКА: Не все заметки восстановлены")
        return False
    
    if window.search_results_label.text():
        print(f"   ❌ ОШИБКА: Счётчик не очищен: '{window.search_results_label.text()}'")
        return False
    
    print("   ✅ Все заметки снова видимы")
    
    # Тест 6: Горячая клавиша Ctrl+F
    print("\n6️⃣ Тест: Горячая клавиша Ctrl+F")
    
    # Устанавливаем фокус на другой элемент
    window.title_edit.setFocus()
    QApplication.processEvents()
    time.sleep(0.1)
    
    initial_focus = window.search_box.hasFocus()
    print(f"   Фокус на поиске ДО нажатия: {initial_focus}")
    
    # Нажимаем Ctrl+F
    QTest.keyClick(window, Qt.Key_F, Qt.ControlModifier)
    QApplication.processEvents()
    time.sleep(0.2)
    
    final_focus = window.search_box.hasFocus()
    print(f"   Фокус на поиске ПОСЛЕ нажатия: {final_focus}")
    
    if not final_focus:
        print("   ❌ ОШИБКА: Ctrl+F не установил фокус на поле поиска")
        return False
    
    print("   ✅ Ctrl+F работает корректно")
    
    # Тест 7: Регистронезависимый поиск
    print("\n7️⃣ Тест: Регистронезависимый поиск 'PYTHON' vs 'python'")
    
    window.search_box.setText("PYTHON")
    QApplication.processEvents()
    time.sleep(0.1)
    visible_upper = sum(1 for i in range(window.notes_list.count()) if not window.notes_list.item(i).isHidden())
    
    window.search_box.setText("python")
    QApplication.processEvents()
    time.sleep(0.1)
    visible_lower = sum(1 for i in range(window.notes_list.count()) if not window.notes_list.item(i).isHidden())
    
    print(f"   'PYTHON': {visible_upper} заметок")
    print(f"   'python': {visible_lower} заметок")
    
    if visible_upper != visible_lower or visible_upper == 0:
        print("   ❌ ОШИБКА: Регистронезависимый поиск не работает")
        return False
    
    print("   ✅ Регистронезависимый поиск работает")
    
    print("\n" + "="*70)
    print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("="*70)
    
    # Закрываем через 2 секунды
    QTimer.singleShot(2000, app.quit)
    app.exec()
    
    return True


if __name__ == "__main__":
    success = test_search()
    sys.exit(0 if success else 1)
