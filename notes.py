"""
Модуль для работы с заметками.
Содержит классы Note и NoteStore для управления заметками.
"""

import json
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('notes_app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Note:
    """
    Класс для представления заметки.
    
    Атрибуты:
        id (str): Уникальный идентификатор заметки (UUID)
        title (str): Заголовок заметки
        body (str): Текст заметки
        last_modified (str): Время последнего изменения в формате ISO
        version (int): Версия заметки (увеличивается при изменении)
    """
    
    def __init__(
        self,
        nid: Optional[str] = None,
        title: str = "",
        body: str = "",
        last_modified: Optional[str] = None,
        version: int = 1,
        deleted: bool = False
    ):
        """
        Инициализация заметки.
        
        Args:
            nid: ID заметки (если None, генерируется новый UUID)
            title: Заголовок заметки
            body: Текст заметки
            last_modified: Время последнего изменения (если None, используется текущее время)
            version: Версия заметки
            deleted: Флаг удаления (tombstone для синхронизации)
        """
        self.id = nid or str(uuid.uuid4())
        self.title = title
        self.body = body
        self.last_modified = last_modified or datetime.now(timezone.utc).isoformat()
        self.version = version
        self.deleted = deleted
    
    def validate(self) -> bool:
        """
        Проверка корректности данных заметки.
        
        Returns:
            bool: True если данные корректны, False иначе
        """
        if not self.id or not isinstance(self.id, str):
            logger.error("Некорректный ID заметки")
            return False
        
        if not isinstance(self.title, str) or len(self.title) > 100:
            logger.error("Некорректный заголовок заметки (макс. 100 символов)")
            return False
        
        if not isinstance(self.body, str) or len(self.body) > 1_000_000:  # 1MB текста
            logger.error("Текст заметки слишком большой")
            return False
        
        try:
            # Проверка формата даты
            datetime.fromisoformat(self.last_modified.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            logger.error("Некорректный формат даты: %s", self.last_modified)
            return False
        
        return True
    
    def to_dict(self) -> Dict:
        """
        Сериализация заметки в словарь для JSON.
        
        Returns:
            Dict: Словарь с данными заметки
        """
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "last_modified": self.last_modified,
            "deleted": self.deleted,
            "version": self.version
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'Note':
        """
        Десериализация заметки из словаря.
        
        Args:
            data: Словарь с данными заметки
            
        Returns:
            Note: Созданная заметка
        """
        return Note(
            nid=data.get("id"),
            title=data.get("title", ""),
            body=data.get("body", ""),
            last_modified=data.get("last_modified"),
            version=data.get("version", 1),
            deleted=data.get("deleted", False)
        )
    
    def update(self, title: Optional[str] = None, body: Optional[str] = None):
        """
        Обновление заметки с автоматическим увеличением версии и времени изменения.
        
        Args:
            title: Новый заголовок (если None, остается прежним)
            body: Новый текст (если None, остается прежним)
        """
        if title is not None:
            self.title = title
        if body is not None:
            self.body = body
        
        self.last_modified = datetime.now(timezone.utc).isoformat()
        self.version += 1
    
    def __repr__(self) -> str:
        """Строковое представление заметки."""
        return f"Note(id={self.id[:8]}..., title='{self.title}', version={self.version})"


class NoteStore:
    """
    Класс для управления коллекцией заметок и их хранением.
    
    Атрибуты:
        storage_path (Path): Путь к файлу хранения заметок
        notes (Dict[str, Note]): Словарь заметок (ключ - ID заметки)
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Инициализация хранилища заметок.
        
        Args:
            storage_path: Путь к файлу хранения (если None, используется ~/.notes_app/notes.json)
        """
        if storage_path is None:
            # Используем домашнюю директорию пользователя
            home = Path.home()
            storage_dir = home / ".notes_app"
            storage_dir.mkdir(exist_ok=True)
            self.storage_path = storage_dir / "notes.json"
        else:
            self.storage_path = Path(storage_path)
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.notes: Dict[str, Note] = {}
        self.load()
    
    def add_note(self, note: Note) -> None:
        """
        Добавление новой заметки.
        
        Args:
            note: Объект заметки для добавления
            
        Raises:
            ValueError: Если данные заметки некорректны
        """
        if not note.validate():
            raise ValueError("Некорректные данные заметки")
        
        self.notes[note.id] = note
        logger.info("Добавлена заметка: %s", note.id[:8])
        self.save()
    
    def update_note(self, note_id: str, title: Optional[str] = None, body: Optional[str] = None) -> bool:
        """
        Обновление существующей заметки.
        
        Args:
            note_id: ID заметки для обновления
            title: Новый заголовок (опционально)
            body: Новый текст (опционально)
            
        Returns:
            bool: True если заметка обновлена, False если заметка не найдена
        """
        if note_id in self.notes:
            self.notes[note_id].update(title=title, body=body)
            self.save()
            return True
        return False
    
    def delete_note(self, note_id: str) -> bool:
        """
        Мягкое удаление заметки (установка флага deleted для синхронизации).
        
        Args:
            note_id: ID заметки для удаления
            
        Returns:
            bool: True если заметка удалена, False если заметка не найдена
        """
        if note_id in self.notes:
            # Устанавливаем флаг deleted вместо физического удаления
            self.notes[note_id].deleted = True
            self.notes[note_id].last_modified = datetime.now(timezone.utc).isoformat()
            self.notes[note_id].version += 1
            self.save()
            logger.info("Заметка помечена удалённой (tombstone): %s", note_id[:8])
            return True
        
        logger.warning("Попытка удалить несуществующую заметку: %s", note_id[:8])
        return False
    
    def cleanup_tombstones(self, older_than_days: int = 30) -> int:
        """
        Очистка старых tombstones (физическое удаление помеченных заметок).
        
        Args:
            older_than_days: Удалить tombstones старше указанного количества дней
            
        Returns:
            int: Количество удалённых tombstones
        """
        now = datetime.now(timezone.utc)
        deleted_count = 0
        
        for note_id in list(self.notes.keys()):
            note = self.notes[note_id]
            if note.deleted:
                try:
                    modified_time = datetime.fromisoformat(note.last_modified.replace('Z', '+00:00'))
                    age_days = (now - modified_time).days
                    
                    if age_days > older_than_days:
                        del self.notes[note_id]
                        deleted_count += 1
                        logger.info("Tombstone физически удалён: %s (возраст: %d дней)", note_id[:8], age_days)
                except Exception as e:
                    logger.error("Ошибка при очистке tombstone %s: %s", note_id[:8], e)
        
        if deleted_count > 0:
            self.save()
            logger.info("Очищено tombstones: %d", deleted_count)
        
        return deleted_count
    
    def get_note(self, note_id: str) -> Optional[Note]:
        """
        Получение заметки по ID.
        
        Args:
            note_id: ID заметки
            
        Returns:
            Optional[Note]: Объект заметки или None если не найдена
        """
        return self.notes.get(note_id)
    
    def get_all_notes(self) -> List[Note]:
        """
        Получение всех активных заметок (без удалённых).
        
        Returns:
            List[Note]: Список всех активных заметок
        """
        return [note for note in self.notes.values() if not note.deleted]
    
    def get_all_notes_including_deleted(self) -> List[Note]:
        """
        Получение всех заметок включая удалённые (tombstones).
        
        Returns:
            List[Note]: Список всех заметок
        """
        return list(self.notes.values())
    
    def save(self) -> None:
        """
        Сохранение всех заметок в JSON файл с атомарной записью.
        
        Raises:
            IOError: Если не удалось сохранить файл
        """
        try:
            data = {
                "notes": {note_id: note.to_dict() for note_id, note in self.notes.items()},
                "meta": {
                    "created": datetime.now(timezone.utc).isoformat(),
                    "count": len(self.notes)
                }
            }
            
            # Атомарная запись через временный файл
            temp_path = self.storage_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Замена файла только после успешной записи
            temp_path.replace(self.storage_path)
            logger.info("Заметки успешно сохранены: %d записей", len(self.notes))
            
        except (IOError, OSError) as e:
            logger.error("Ошибка при сохранении заметок: %s", e)
            raise IOError(f"Не удалось сохранить заметки: {e}") from e
        except Exception as e:
            logger.error("Неожиданная ошибка при сохранении: %s", e)
            raise
    
    def load(self) -> None:
        """
        Загрузка заметок из JSON файла с обработкой ошибок.
        
        Raises:
            IOError: Если не удалось прочитать файл
        """
        if not self.storage_path.exists():
            # Файл не существует, создаем пустое хранилище
            logger.info("Файл заметок не найден, создается новый")
            self.notes = {}
            self.save()
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            notes_data = data.get("notes", {})
            self.notes = {note_id: Note.from_dict(note_data) 
                         for note_id, note_data in notes_data.items()}
            
            logger.info("Загружено заметок: %d", len(self.notes))
        
        except json.JSONDecodeError as e:
            logger.error("Ошибка при разборе JSON: %s", e)
            # Создаем резервную копию поврежденного файла
            backup_path = self.storage_path.with_suffix('.backup')
            try:
                import shutil
                shutil.copy2(self.storage_path, backup_path)
                logger.warning("Резервная копия сохранена: %s", backup_path)
            except Exception as backup_error:
                logger.error("Не удалось создать резервную копию: %s", backup_error)
            
            self.notes = {}
            self.save()
        
        except (IOError, OSError) as e:
            logger.error("Ошибка при чтении файла: %s", e)
            self.notes = {}
            raise IOError(f"Не удалось загрузить заметки: {e}") from e
        
        except Exception as e:
            logger.error("Неожиданная ошибка при загрузке: %s", e)
            self.notes = {}
            raise
    
    def __len__(self) -> int:
        """Количество заметок в хранилище."""
        return len(self.notes)
    
    def create_backup(self) -> Optional[Path]:
        """
        Создание резервной копии файла заметок.
        
        Returns:
            Optional[Path]: Путь к резервной копии или None если файл не существует
        """
        if not self.storage_path.exists():
            logger.warning("Нет файла для резервного копирования")
            return None
        
        try:
            backup_dir = self.storage_path.parent / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"notes_backup_{timestamp}.json"
            
            import shutil
            shutil.copy2(self.storage_path, backup_path)
            logger.info("Создана резервная копия: %s", backup_path)
            
            # Хранить только последние 10 резервных копий
            backups = sorted(backup_dir.glob("notes_backup_*.json"), reverse=True)
            for old_backup in backups[10:]:
                old_backup.unlink()
                logger.info("Удалена старая резервная копия: %s", old_backup)
            
            return backup_path
        
        except Exception as e:
            logger.error("Ошибка при создании резервной копии: %s", e)
            return None
    
    def __repr__(self) -> str:
        """Строковое представление хранилища."""
        return f"NoteStore(path={self.storage_path}, notes={len(self.notes)})"


if __name__ == "__main__":
    # Пример использования
    print("Тестирование модуля notes.py\n")
    
    # Создаем хранилище
    store = NoteStore()
    print(f"Хранилище создано: {store}\n")
    
    # Создаем заметку
    note1 = Note(title="Моя первая заметка", body="Это текст первой заметки")
    store.add_note(note1)
    print(f"Добавлена заметка: {note1}")
    
    # Создаем еще одну заметку
    note2 = Note(title="Вторая заметка", body="Текст второй заметки")
    store.add_note(note2)
    print(f"Добавлена заметка: {note2}")
    
    # Получаем все заметки
    print(f"\nВсего заметок: {len(store)}")
    for note in store.get_all_notes():
        print(f"  - {note.title}")
    
    # Обновляем заметку
    print(f"\nОбновление заметки {note1.id[:8]}...")
    store.update_note(note1.id, title="Обновленный заголовок", body="Обновленный текст")
    updated_note = store.get_note(note1.id)
    print(f"Версия после обновления: {updated_note.version}")
    
    # Удаляем заметку
    print(f"\nУдаление заметки {note2.id[:8]}...")
    store.delete_note(note2.id)
    print(f"Осталось заметок: {len(store)}")
    
    print("\n✓ Тестирование завершено успешно!")
