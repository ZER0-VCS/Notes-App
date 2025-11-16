"""
Тест для проверки функции автосохранения заметок.
Проверяет, что заметка автоматически сохраняется через 5 секунд после изменения.
"""

import sys
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from gui import NotesApp


def test_autosave():
    """Тест автосохранения с визуальной обратной связью."""
    print("\n" + "="*70)
    print("🧪 ТЕСТ АВТОСОХРАНЕНИЯ")
    print("="*70)
    
    app = QApplication(sys.argv)
    window = NotesApp()
    window.show()
    
    # Создаем новую заметку
    print("\n1️⃣ Создаём новую заметку...")
    window.create_new_note()
    QApplication.processEvents()
    time.sleep(0.5)
    
    if not window.current_note_id:
        print("❌ ОШИБКА: Заметка не создана")
        return False
    
    note_id = window.current_note_id
    print(f"✅ Заметка создана с ID: {note_id[:8]}")
    
    # Изменяем заголовок
    print("\n2️⃣ Изменяем заголовок заметки...")
    window.title_edit.setText("Тест автосохранения")
    QApplication.processEvents()
    time.sleep(0.2)
    
    # Проверяем, что таймер автосохранения запущен
    if not window.autosave_timer.isActive():
        print("❌ ОШИБКА: Таймер автосохранения не запустился")
        return False
    
    print(f"✅ Таймер автосохранения запущен (интервал: {window.autosave_delay}мс)")
    print(f"✅ Флаг has_unsaved_changes: {window.has_unsaved_changes}")
    print(f"✅ Кнопка сохранения активна: {window.btn_save.isEnabled()}")
    
    # Изменяем текст несколько раз (имитируем набор текста)
    print("\n3️⃣ Имитируем набор текста (перезапуск таймера)...")
    for i in range(3):
        window.body_edit.setPlainText(f"Тестовый текст, попытка {i+1}")
        QApplication.processEvents()
        time.sleep(0.3)
        print(f"   Набор текста {i+1}/3 - таймер активен: {window.autosave_timer.isActive()}")
    
    # Ждём автосохранение
    print("\n4️⃣ Ожидаем автосохранение (6 секунд с проверками каждые 0.1 сек)...")
    print("   0%", end="", flush=True)
    
    status_after_autosave = ""
    autosave_detected = False
    
    for i in range(60):  # 60 итераций по 0.1 сек = 6 секунд
        time.sleep(0.1)
        QApplication.processEvents()
        
        # Захватываем статус сразу когда автосохранение сработало
        if not window.has_unsaved_changes and not autosave_detected:
            autosave_detected = True
            status_after_autosave = window.status_label.text()
            print(f"\n   ✅ Автосохранение сработало на {i/10:.1f} сек!")
        
        # Показываем прогресс каждые 10%
        if (i + 1) % 6 == 0:
            percentage = int((i + 1) / 60 * 100)
            print(f"...{percentage}%", end="", flush=True)
    
    print()  # Новая строка
    
    # Проверяем результаты
    print("\n5️⃣ Проверка результатов:")
    print(f"   Таймер активен: {window.autosave_timer.isActive()}")
    print(f"   Несохранённые изменения: {window.has_unsaved_changes}")
    print(f"   Кнопка сохранения активна: {window.btn_save.isEnabled()}")
    print(f"   Статус после автосохранения: '{status_after_autosave}'")
    
    # Проверяем, что заметка сохранилась
    note = window.store.get_note(note_id)
    if note and note.title == "Тест автосохранения":
        print(f"   Заголовок в базе: '{note.title}' ✅")
    else:
        print(f"   Заголовок в базе: '{note.title if note else 'НЕ НАЙДЕНА'}' ❌")
        return False
    
    if note and "попытка 3" in note.body:
        print(f"   Текст в базе: содержит 'попытка 3' ✅")
    else:
        print(f"   Текст в базе: '{note.body[:50] if note else 'НЕ НАЙДЕНА'}' ❌")
        return False
    
    # Финальные проверки
    if window.has_unsaved_changes:
        print("\n❌ ОШИБКА: Остались несохранённые изменения")
        return False
    
    if window.btn_save.isEnabled():
        print("❌ ОШИБКА: Кнопка сохранения всё ещё активна")
        return False
    
    # Проверяем автосохранение по факту - заметка должна быть сохранена в базе
    # и статус должен был показать автосохранение (даже если потом очистился)
    if autosave_detected:
        print(f"   ✅ Автосохранение сработало корректно")
    else:
        print(f"❌ ОШИБКА: Автосохранение не было обнаружено")
        return False
    
    print("\n" + "="*70)
    print("🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
    print("="*70)
    
    # Закрываем через 2 секунды
    QTimer.singleShot(2000, app.quit)
    app.exec()
    
    return True


if __name__ == "__main__":
    success = test_autosave()
    sys.exit(0 if success else 1)
