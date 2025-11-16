"""
Тест для проверки функции автоматической синхронизации.
Проверяет, что синхронизация происходит автоматически каждые 60 секунд.
"""

import sys
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from gui import NotesApp


def test_autosync():
    """Тест автосинхронизации с визуальной обратной связью."""
    print("\n" + "="*70)
    print("🔄 ТЕСТ АВТОСИНХРОНИЗАЦИИ")
    print("="*70)
    
    app = QApplication(sys.argv)
    window = NotesApp()
    window.show()
    QApplication.processEvents()
    
    # Проверяем наличие настроенной папки синхронизации
    if not window.sync_manager.cloud_path:
        print("\n❌ ОШИБКА: Папка синхронизации не настроена")
        print("   Для тестирования автосинхронизации необходимо настроить папку")
        return False
    
    print(f"\n✅ Папка синхронизации: {window.sync_manager.cloud_path}")
    
    # Тест 1: Проверка включения автосинхронизации
    print("\n1️⃣ Тест: Автосинхронизация включена при запуске")
    print(f"   Автосинхронизация активна: {window.autosync_enabled}")
    print(f"   Таймер активен: {window.autosync_timer.isActive()}")
    print(f"   Интервал: {window.autosync_interval // 1000} секунд")
    
    if not window.autosync_enabled:
        print("   ⚠️ Автосинхронизация не активна, пробуем включить...")
        window.enable_autosync()
        QApplication.processEvents()
        time.sleep(0.2)
        
        if not window.autosync_enabled:
            print("   ❌ ОШИБКА: Не удалось включить автосинхронизацию")
            return False
    
    print("   ✅ Автосинхронизация включена")
    
    # Тест 2: Создание тестовой заметки
    print("\n2️⃣ Тест: Создание тестовой заметки")
    initial_count = window.notes_list.count()
    print(f"   Заметок до создания: {initial_count}")
    
    window.create_new_note()
    QApplication.processEvents()
    window.title_edit.setText("Тест автосинхронизации")
    window.body_edit.setPlainText("Эта заметка должна автоматически синхронизироваться")
    window.save_current_note()
    QApplication.processEvents()
    time.sleep(0.5)
    
    new_count = window.notes_list.count()
    print(f"   Заметок после создания: {new_count}")
    
    if new_count != initial_count + 1:
        print("   ❌ ОШИБКА: Заметка не создана")
        return False
    
    print("   ✅ Заметка создана")
    
    # Тест 3: Уменьшаем интервал для быстрого тестирования
    print("\n3️⃣ Тест: Изменение интервала на 10 секунд для быстрого тестирования")
    original_interval = window.autosync_interval
    window.autosync_interval = 10000  # 10 секунд
    window.autosync_timer.stop()
    window.autosync_timer.start(window.autosync_interval)
    print(f"   Интервал изменён с {original_interval // 1000} сек на {window.autosync_interval // 1000} сек")
    print("   ✅ Интервал изменён")
    
    # Тест 4: Ожидание автосинхронизации
    print("\n4️⃣ Тест: Ожидание автосинхронизации (12 секунд)")
    print("   Следим за статусом приложения...")
    
    sync_detected = False
    status_history = []
    
    for i in range(120):  # 12 секунд по 0.1 сек
        time.sleep(0.1)
        QApplication.processEvents()
        
        current_status = window.status_label.text()
        
        # Захватываем статус автосинхронизации
        if "автосинхронизация" in current_status.lower() and not sync_detected:
            sync_detected = True
            status_history.append(f"[{i/10:.1f}с] {current_status}")
            print(f"\n   📊 Обнаружена автосинхронизация на {i/10:.1f} сек!")
            print(f"   📝 Статус: '{current_status}'")
        
        # Показываем прогресс каждую секунду
        if (i + 1) % 10 == 0:
            percentage = int((i + 1) / 120 * 100)
            print(f"   {percentage}% ({(i+1)/10:.0f}/12 сек)", end="", flush=True)
            if (i + 1) % 30 == 0:
                print()  # Новая строка каждые 3 секунды
    
    print("\n")
    
    # Тест 5: Проверка результатов
    print("5️⃣ Проверка результатов:")
    print(f"   Автосинхронизация обнаружена: {sync_detected}")
    print(f"   История статусов: {len(status_history)} записей")
    
    if status_history:
        for status in status_history:
            print(f"      - {status}")
    
    if not sync_detected:
        print("   ❌ ОШИБКА: Автосинхронизация не была обнаружена за 12 секунд")
        print("   ⚠️ Возможные причины:")
        print("      - Синхронизация заняла больше времени")
        print("      - Таймер не сработал")
        print(f"      - Таймер активен: {window.autosync_timer.isActive()}")
        return False
    
    print("   ✅ Автосинхронизация работает корректно")
    
    # Восстанавливаем оригинальный интервал
    print(f"\n6️⃣ Восстановление оригинального интервала ({original_interval // 1000} сек)")
    window.autosync_interval = original_interval
    window.autosync_timer.stop()
    window.autosync_timer.start(window.autosync_interval)
    print("   ✅ Интервал восстановлен")
    
    print("\n" + "="*70)
    print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("="*70)
    print("\nℹ️ Примечание: Автосинхронизация продолжит работать каждые 60 секунд")
    
    # Закрываем через 2 секунды
    QTimer.singleShot(2000, app.quit)
    app.exec()
    
    return True


if __name__ == "__main__":
    success = test_autosync()
    sys.exit(0 if success else 1)
