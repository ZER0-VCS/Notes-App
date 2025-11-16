"""
Пример использования системы тем в приложении заметок.

Демонстрирует:
1. Загрузку доступных тем
2. Применение темы к приложению
3. Получение цветов из темы

Для использования в будущем можно добавить:
- Меню выбора темы в GUI
- Сохранение выбранной темы в config.json
- Применение темы через QSS stylesheet
"""

from themes import theme_manager


def demo_themes():
    """Демонстрация работы с темами."""
    
    print("=" * 70)
    print("ДЕМОНСТРАЦИЯ СИСТЕМЫ ТЕМ")
    print("=" * 70)
    
    # 1. Получить список доступных тем
    print("\n📋 Доступные темы:")
    themes = theme_manager.get_available_themes()
    for theme_id, theme_name in themes:
        print(f"   • {theme_id}: {theme_name}")
    
    # 2. Получить информацию о конкретной теме
    print("\n🎨 Светлая тема:")
    light_theme = theme_manager.get_theme("light")
    print(f"   Название: {light_theme.name}")
    print(f"   Фон: {light_theme.background}")
    print(f"   Текст: {light_theme.text}")
    print(f"   Цвет выделения при поиске: {light_theme.search_highlight}")
    
    print("\n🌙 Темная тема:")
    dark_theme = theme_manager.get_theme("dark")
    print(f"   Название: {dark_theme.name}")
    print(f"   Фон: {dark_theme.background}")
    print(f"   Текст: {dark_theme.text}")
    print(f"   Цвет выделения при поиске: {dark_theme.search_highlight}")
    
    # 3. Установить текущую тему
    print("\n⚙️ Установка темы:")
    theme_manager.set_theme("blue")
    print(f"   Текущая тема: {theme_manager.current_theme.name}")
    
    # 4. Получить QSS stylesheet для темы
    print("\n📝 Пример QSS stylesheet (первые 300 символов):")
    stylesheet = theme_manager.get_stylesheet()
    print(stylesheet[:300] + "...")
    
    # 5. Получить цвет выделения
    print("\n🎨 Цвет выделения при поиске:")
    highlight_color = theme_manager.get_search_highlight_color()
    print(f"   RGB: ({highlight_color.red()}, {highlight_color.green()}, {highlight_color.blue()})")
    print(f"   Hex: {highlight_color.name()}")
    
    print("\n" + "=" * 70)
    print("✅ Демонстрация завершена!")
    print("=" * 70)
    
    # Примеры для будущей интеграции
    print("\n💡 Для интеграции в GUI:")
    print("   1. Добавьте меню 'Вид' → 'Тема' с выбором темы")
    print("   2. Используйте app.setStyleSheet(theme_manager.get_stylesheet())")
    print("   3. Сохраняйте выбор темы в config.json:")
    print('      {"theme": "dark", ...}')
    print("   4. При запуске загружайте тему из конфигурации")


if __name__ == "__main__":
    demo_themes()
