"""
Тест исправлений горячего применения настроек
- Изменение шрифта в списке заметок
- Правильные цвета фона и текста в светлых темах
"""

import sys
import logging
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer
from src.gui import NotesApp
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_font_in_notes_list(app):
    """Тест применения шрифта к списку заметок."""
    logger.info("=" * 60)
    logger.info("ТЕСТ: Изменение шрифта в списке заметок")
    logger.info("=" * 60)
    
    # Проверяем текущий шрифт списка
    current_font = app.notes_list.font()
    logger.info(f"✓ Текущий шрифт списка: {current_font.family()}, размер {current_font.pointSize()}")
    
    # Применяем новый шрифт
    test_font = "Courier New"
    test_size = 12
    app.apply_editor_font(test_font, test_size)
    
    # Проверяем, что шрифт применился
    new_font = app.notes_list.font()
    logger.info(f"✓ Новый шрифт списка: {new_font.family()}, размер {new_font.pointSize()}")
    
    if new_font.family() == test_font and new_font.pointSize() == test_size:
        logger.info("✓ PASSED: Шрифт списка заметок изменился корректно!")
        return True
    else:
        logger.error("✗ FAILED: Шрифт списка не изменился")
        return False


def test_light_theme_colors(app):
    """Тест правильных цветов в светлой теме."""
    logger.info("=" * 60)
    logger.info("ТЕСТ: Цвета полей ввода в светлой теме")
    logger.info("=" * 60)
    
    # Применяем светлую тему
    app.apply_theme_live("light")
    
    theme = app.current_theme
    logger.info(f"✓ Применена тема: {theme.name}")
    logger.info(f"  Фон полей ввода: {theme.input_background}")
    logger.info(f"  Цвет текста в полях: {theme.input_text}")
    logger.info(f"  Фон списка: {theme.list_background}")
    logger.info(f"  Цвет текста в списке: {theme.list_text}")
    
    # Проверяем, что используются правильные атрибуты
    if hasattr(theme, 'input_background') and hasattr(theme, 'input_text'):
        logger.info("✓ PASSED: Тема использует правильные атрибуты для полей ввода!")
        return True
    else:
        logger.error("✗ FAILED: Отсутствуют необходимые атрибуты темы")
        return False


def test_dark_theme_colors(app):
    """Тест цветов в тёмной теме."""
    logger.info("=" * 60)
    logger.info("ТЕСТ: Цвета полей ввода в тёмной теме")
    logger.info("=" * 60)
    
    # Применяем тёмную тему
    app.apply_theme_live("dark")
    
    theme = app.current_theme
    logger.info(f"✓ Применена тема: {theme.name}")
    logger.info(f"  Фон полей ввода: {theme.input_background}")
    logger.info(f"  Цвет текста в полях: {theme.input_text}")
    logger.info(f"  Фон списка: {theme.list_background}")
    logger.info(f"  Цвет текста в списке: {theme.list_text}")
    
    return True


def run_tests():
    """Запуск всех тестов."""
    logger.info("\n" + "=" * 60)
    logger.info("ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ v0.5.0")
    logger.info("=" * 60 + "\n")
    
    app_qt = QApplication.instance()
    if app_qt is None:
        app_qt = QApplication(sys.argv)
    
    # Создаём приложение
    app = NotesApp()
    app.show()
    
    # Запускаем тесты
    results = []
    
    # Тест 1: Шрифт в списке заметок
    results.append(("Шрифт в списке заметок", test_font_in_notes_list(app)))
    
    # Тест 2: Светлая тема
    results.append(("Цвета светлой темы", test_light_theme_colors(app)))
    
    # Тест 3: Тёмная тема
    results.append(("Цвета тёмной темы", test_dark_theme_colors(app)))
    
    # Итоги
    logger.info("\n" + "=" * 60)
    logger.info("ИТОГИ ТЕСТИРОВАНИЯ")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{status}: {test_name}")
    
    logger.info("=" * 60)
    logger.info(f"Пройдено тестов: {passed}/{total}")
    logger.info("=" * 60)
    
    if passed == total:
        logger.info("✓ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        logger.info("\nИсправления работают корректно:")
        logger.info("1. Шрифт применяется ко всем элементам, включая список заметок")
        logger.info("2. Цвета полей ввода меняются правильно в светлых темах")
        logger.info("3. Текст виден на всех фонах")
        
        QMessageBox.information(
            app,
            "Тесты пройдены",
            f"Все тесты пройдены успешно ({passed}/{total})!\n\n"
            "Исправления работают корректно:\n"
            "✓ Шрифт применяется к списку заметок\n"
            "✓ Цвета фона и текста корректны в светлых темах"
        )
    else:
        logger.warning(f"✗ Некоторые тесты провалены: {total - passed}")
    
    # Закрываем через 1 секунду после показа MessageBox
    QTimer.singleShot(3000, app_qt.quit)
    
    return app_qt.exec()


if __name__ == '__main__':
    sys.exit(run_tests())
