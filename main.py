"""
Главный файл приложения "Заметки".
Точка входа для запуска приложения.
"""

import sys
from pathlib import Path

# Добавляем папку src в путь для импорта
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.gui import main

if __name__ == "__main__":
    main()
