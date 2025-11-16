# Для разработчиков

## 🚀 Быстрый старт разработки

```bash
# 1. Клонирование
git clone https://github.com/ZER0-VCS/Notes-App.git
cd Notes-App

# 2. Окружение
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate     # Linux/macOS

# 3. Установка
pip install -r requirements.txt

# 4. Запуск
python main.py
```

## 📂 Структура кода

```
Notes-App/
├── notes.py          # Модель данных
│   ├── Note          # Класс заметки
│   └── NoteStore     # CRUD + JSON
├── gui.py            # GUI (PySide6)
│   └── NotesApp      # Главное окно
├── sync.py           # Менеджер синхронизации
│   └── SyncManager   # LWW алгоритм
├── themes.py         # Система тем
│   ├── Theme         # Dataclass темы
│   └── ThemeManager  # Управление темами
├── main.py           # Entry point
└── tests/            # Все тесты
    ├── test_search.py
    ├── test_highlight_all_fields.py
    └── ... (другие тесты)
```

## 🧪 Тестирование

```bash
# Тест модуля данных
python notes.py

# Проверка логов
tail -f notes_app.log  # Linux/macOS
Get-Content notes_app.log -Wait  # Windows
```

## 🔧 Полезное

### Файлы данных
- **JSON**: `~/.notes_app/notes.json`
- **Бэкапы**: `~/.notes_app/backups/`
- **Логи**: `notes_app.log`

### Горячие клавиши
- `Ctrl+S` - Сохранить
- `Ctrl+N` - Создать
- `Ctrl+D` - Удалить

### Логирование

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Информация")
logger.warning("Предупреждение")
logger.error("Ошибка")
```

## 📝 Следующие задачи

### Версия 0.5.0 (Приоритет)
- [ ] GUI выбора темы (Меню "Вид" → "Тема")
- [ ] Диалог настроек приложения
- [ ] Экспорт в Markdown/TXT/HTML

См. подробный план в [ROADMAP.md](ROADMAP.md) и раздел `[Unreleased]` в [CHANGELOG.md](CHANGELOG.md)

## 🤝 Контрибьюция

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/amazing`)
3. Commit изменений (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing`)
5. Создайте Pull Request

## 📚 Документация

- **README.md** - Пользовательская документация
- **CHANGELOG.md** - История версий
- **Код** - Все функции имеют docstrings

## 🐛 Известные проблемы

На данный момент нет критических багов.

Для сообщений об ошибках используйте [GitHub Issues](https://github.com/ZER0-VCS/Notes-App/issues).
