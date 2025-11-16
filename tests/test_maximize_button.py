"""
Тестовый скрипт для проверки функциональности кнопки развернуть (maximize).

Проверяет:
1. Работу кнопки развернуть на полный экран
2. Работу кнопки восстановить размер
3. Ограничения размера окна
4. Корректность размеров относительно разрешения экрана
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt
from gui import NotesApp

def test_maximize_functionality():
    """Тест функциональности развертывания окна."""
    app = QApplication.instance() or QApplication(sys.argv)
    window = NotesApp()
    
    print("=" * 70)
    print("🧪 ТЕСТ ФУНКЦИОНАЛЬНОСТИ КНОПКИ РАЗВЕРНУТЬ")
    print("=" * 70)
    
    # Получаем информацию об экране
    screen = QApplication.primaryScreen()
    screen_geometry = screen.availableGeometry()
    screen_size = screen.size()
    
    print(f"\n📺 ИНФОРМАЦИЯ О ЭКРАНЕ:")
    print(f"   • Полный размер экрана: {screen_size.width()}x{screen_size.height()}")
    print(f"   • Доступная область (без панели задач): {screen_geometry.width()}x{screen_geometry.height()}")
    print(f"   • Позиция: x={screen_geometry.x()}, y={screen_geometry.y()}")
    
    # Получаем ограничения окна
    min_size = window.minimumSize()
    max_size = window.maximumSize()
    current_size = window.size()
    
    print(f"\n📏 ОГРАНИЧЕНИЯ ОКНА:")
    print(f"   • Минимальный размер: {min_size.width()}x{min_size.height()}")
    print(f"   • Максимальный размер: {max_size.width()}x{max_size.height()}")
    print(f"   • Текущий размер: {current_size.width()}x{current_size.height()}")
    
    # Проверка 1: Максимальный размер НЕ должен быть ограничен (для работы кнопки)
    print(f"\n✅ ПРОВЕРКА 1: Максимальный размер")
    # QWIDGETSIZE_MAX = 16777215 - это значение по умолчанию в Qt (нет ограничения)
    if max_size.width() >= 16000000 or max_size.width() >= screen_geometry.width():
        print(f"   ✅ Максимальный размер НЕ ограничен (или >= размера экрана)")
        print(f"   ✅ Это позволяет кнопке развернуть работать корректно")
    else:
        print(f"   ⚠️  Максимальный размер жестко ограничен: {max_size.width()}x{max_size.height()}")
        print(f"   ⚠️  Это может блокировать работу кнопки развернуть")
    
    # Показываем окно
    window.show()
    
    # Переменные для хранения результатов тестов
    test_results = []
    
    def check_normal_state():
        """Проверка начального состояния."""
        print(f"\n✅ ПРОВЕРКА 2: Начальное состояние окна")
        is_maximized = window.isMaximized()
        is_fullscreen = window.isFullScreen()
        current = window.size()
        
        print(f"   • Развернуто: {is_maximized}")
        print(f"   • Полный экран: {is_fullscreen}")
        print(f"   • Размер: {current.width()}x{current.height()}")
        
        if not is_maximized and not is_fullscreen:
            print(f"   ✅ Окно в обычном состоянии")
            test_results.append(("Начальное состояние", True))
        else:
            print(f"   ❌ Окно уже развернуто!")
            test_results.append(("Начальное состояние", False))
        
        # Через 500мс разворачиваем
        QTimer.singleShot(500, maximize_window)
    
    def maximize_window():
        """Разворачиваем окно."""
        print(f"\n✅ ПРОВЕРКА 3: Развертывание окна")
        print(f"   🔄 Вызов showMaximized()...")
        window.showMaximized()
        
        # Через 300мс проверяем результат
        QTimer.singleShot(300, check_maximized_state)
    
    def check_maximized_state():
        """Проверка развернутого состояния."""
        is_maximized = window.isMaximized()
        current = window.size()
        
        print(f"   • Развернуто: {is_maximized}")
        print(f"   • Размер: {current.width()}x{current.height()}")
        
        # Проверяем, что размер близок к максимальному (с учетом рамок окна)
        size_ok = (current.width() >= screen_geometry.width() - 50 and 
                   current.height() >= screen_geometry.height() - 50)
        
        if is_maximized and size_ok:
            print(f"   ✅ Окно успешно развернуто на весь экран!")
            test_results.append(("Развертывание", True))
        else:
            print(f"   ❌ Окно НЕ развернулось корректно")
            print(f"      Ожидался размер ~{screen_geometry.width()}x{screen_geometry.height()}")
            print(f"      isMaximized={is_maximized}, size_ok={size_ok}")
            test_results.append(("Развертывание", False))
        
        # Через 500мс восстанавливаем
        QTimer.singleShot(500, restore_window)
    
    def restore_window():
        """Восстанавливаем обычный размер."""
        print(f"\n✅ ПРОВЕРКА 4: Восстановление размера")
        print(f"   🔄 Вызов showNormal()...")
        window.showNormal()
        
        # Через 300мс проверяем результат
        QTimer.singleShot(300, check_restored_state)
    
    def check_restored_state():
        """Проверка восстановленного состояния."""
        is_maximized = window.isMaximized()
        current = window.size()
        
        print(f"   • Развернуто: {is_maximized}")
        print(f"   • Размер: {current.width()}x{current.height()}")
        
        if not is_maximized and current.width() < screen_geometry.width():
            print(f"   ✅ Окно успешно восстановлено в обычный размер!")
            test_results.append(("Восстановление", True))
        else:
            print(f"   ❌ Окно НЕ восстановилось корректно")
            test_results.append(("Восстановление", False))
        
        # Через 500мс повторяем цикл для надежности
        QTimer.singleShot(500, second_maximize)
    
    def second_maximize():
        """Второе развертывание для проверки повторяемости."""
        print(f"\n✅ ПРОВЕРКА 5: Повторное развертывание")
        print(f"   🔄 Вызов showMaximized() снова...")
        window.showMaximized()
        
        QTimer.singleShot(300, check_second_maximize)
    
    def check_second_maximize():
        """Проверка второго развертывания."""
        is_maximized = window.isMaximized()
        current = window.size()
        
        print(f"   • Развернуто: {is_maximized}")
        print(f"   • Размер: {current.width()}x{current.height()}")
        
        size_ok = (current.width() >= screen_geometry.width() - 50 and 
                   current.height() >= screen_geometry.height() - 50)
        
        if is_maximized and size_ok:
            print(f"   ✅ Повторное развертывание работает!")
            test_results.append(("Повторное развертывание", True))
        else:
            print(f"   ❌ Повторное развертывание не работает")
            test_results.append(("Повторное развертывание", False))
        
        # Завершаем через 500мс
        QTimer.singleShot(500, show_results)
    
    def show_results():
        """Показываем итоговые результаты."""
        print("\n" + "=" * 70)
        print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
        print("=" * 70)
        
        passed = 0
        failed = 0
        
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status}  {test_name}")
            if result:
                passed += 1
            else:
                failed += 1
        
        print(f"\n  Пройдено: {passed}/{len(test_results)}")
        
        if failed == 0:
            print("\n  🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            print("  ✅ Кнопка развернуть работает корректно")
            print("  ✅ Максимальный размер адаптируется под экран")
        else:
            print(f"\n  ⚠️  ПРОВАЛЕНО ТЕСТОВ: {failed}")
        
        print("\n  ℹ️  Закройте окно для завершения теста...")
    
    # Запускаем первую проверку через 500мс после показа окна
    QTimer.singleShot(500, check_normal_state)
    
    # Запуск GUI
    sys.exit(app.exec())

if __name__ == "__main__":
    test_maximize_functionality()
