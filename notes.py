"""
Модуль для работы с заметками.
Содержит классы Note и NoteStore для управления заметками.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


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
        version: int = 1
    ):
        """
        Инициализация заметки.
        
        Args:
            nid: ID заметки (если None, генерируется новый UUID)
            title: Заголовок заметки
            body: Текст заметки
            last_modified: Время последнего изменения (если None, используется текущее время)
            version: Версия заметки
        """
        self.id = nid or str(uuid.uuid4())
        self.title = title
        self.body = body
        self.last_modified = last_modified or datetime.now(timezone.utc).isoformat()
        self.version = version
    
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
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Note':
        """
        Десериализация заметки из словаря.
        
        Args:
            data: Словарь с данными заметки
            
        Returns:
            Note: Объект заметки
        """
        return cls(
            nid=data.get("id"),
            title=data.get("title", ""),
            body=data.get("body", ""),
            last_modified=data.get("last_modified"),
            version=data.get("version", 1)
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
        """
        self.notes[note.id] = note
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
        Удаление заметки.
        
        Args:
            note_id: ID заметки для удаления
            
        Returns:
            bool: True если заметка удалена, False если заметка не найдена
        """
        if note_id in self.notes:
            del self.notes[note_id]
            self.save()
            return True
        return False
    
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
        Получение всех заметок.
        
        Returns:
            List[Note]: Список всех заметок
        """
        return list(self.notes.values())
    
    def save(self) -> None:
        """
        Сохранение всех заметок в JSON файл.
        """
        data = {
            "notes": {note_id: note.to_dict() for note_id, note in self.notes.items()},
            "meta": {
                "created": datetime.now(timezone.utc).isoformat(),
                "count": len(self.notes)
            }
        }
        
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self) -> None:
        """
        Загрузка заметок из JSON файла.
        """
        if not self.storage_path.exists():
            # Файл не существует, создаем пустое хранилище
            self.notes = {}
            self.save()
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            notes_data = data.get("notes", {})
            self.notes = {note_id: Note.from_dict(note_data) 
                         for note_id, note_data in notes_data.items()}
        
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Ошибка при загрузке заметок: {e}")
            # В случае ошибки создаем пустое хранилище
            self.notes = {}
            self.save()
    
    def __len__(self) -> int:
        """Количество заметок в хранилище."""
        return len(self.notes)
    
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
