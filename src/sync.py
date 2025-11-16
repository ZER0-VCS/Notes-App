"""
Модуль синхронизации заметок между устройствами.
Реализует алгоритм Last-Writer-Wins (LWW) для безопасного слияния данных.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional

try:
    from notes import Note, NoteStore
except ImportError:
    from .notes import Note, NoteStore

logger = logging.getLogger(__name__)


class SyncConflict:
    """
    Класс для представления конфликта синхронизации.
    
    Атрибуты:
        note_id (str): ID заметки с конфликтом
        local_note (Note): Локальная версия
        remote_note (Note): Удаленная версия
        conflict_type (str): Тип конфликта
    """
    
    def __init__(self, note_id: str, local_note: Note, remote_note: Note, conflict_type: str = "edit"):
        self.note_id = note_id
        self.local_note = local_note
        self.remote_note = remote_note
        self.conflict_type = conflict_type
    
    def __repr__(self) -> str:
        return f"SyncConflict(id={self.note_id[:8]}, type={self.conflict_type})"


class SyncManager:
    """
    Менеджер синхронизации заметок.
    
    Реализует алгоритм Last-Writer-Wins (LWW) для слияния локальных
    и удаленных заметок с обработкой конфликтов.
    """
    
    def __init__(self, local_store: NoteStore, cloud_path: Optional[Path] = None):
        """
        Инициализация менеджера синхронизации.
        
        Args:
            local_store: Локальное хранилище заметок
            cloud_path: Путь к облачной папке (опционально)
        """
        self.local_store = local_store
        self.cloud_path = cloud_path
        self.conflicts: List[SyncConflict] = []
        self.config_path = Path.home() / ".notes_app" / "config.json"
        
        # Загрузка конфигурации (в т.ч. сохраненного пути к облаку)
        if not cloud_path:
            self._load_config()
        
        logger.info("SyncManager инициализирован")
    
    def set_cloud_path(self, path: Path) -> bool:
        """
        Установка пути к облачной папке синхронизации.
        
        Args:
            path: Путь к папке синхронизации
            
        Returns:
            bool: True если путь валиден, False иначе
        """
        try:
            path = Path(path)
            if not path.exists():
                logger.warning("Облачная папка не существует: %s", path)
                return False
            
            if not path.is_dir():
                logger.error("Путь не является директорией: %s", path)
                return False
            
            self.cloud_path = path
            self._save_config()
            logger.info("Установлен путь к облачной папке: %s", path)
            return True
        
        except Exception as e:
            logger.error("Ошибка при установке пути к облаку: %s", e)
            return False
    
    def get_cloud_file_path(self) -> Optional[Path]:
        """
        Получение пути к файлу заметок в облаке.
        
        Returns:
            Optional[Path]: Путь к файлу или None если облако не настроено
        """
        if not self.cloud_path:
            return None
        
        return self.cloud_path / "notes.json"
    
    def find_conflict_files(self) -> List[Path]:
        """
        Поиск конфликтных копий OneDrive в облачной папке.
        
        OneDrive создаёт файлы типа:
        - notes-DESKTOP-ABC123.json
        - notes (conflicted copy).json
        
        Returns:
            List[Path]: Список путей к конфликтным файлам
        """
        if not self.cloud_path:
            return []
        
        conflict_files = []
        
        try:
            # Ищем файлы с паттерном конфликта
            for file in self.cloud_path.glob("notes*.json"):
                # Исключаем основной файл и временные файлы
                if file.name == "notes.json" or file.suffix == '.tmp':
                    continue
                
                # Конфликтные файлы OneDrive обычно содержат имя компьютера или "conflicted"
                if "conflicted" in file.name.lower() or file.name.startswith("notes-"):
                    conflict_files.append(file)
                    logger.info("Обнаружен конфликтный файл: %s", file.name)
        
        except Exception as e:
            logger.error("Ошибка при поиске конфликтных файлов: %s", e)
        
        return conflict_files
    
    def load_remote_notes(self) -> Optional[Dict[str, Note]]:
        """
        Загрузка заметок из облачного хранилища с автоматическим слиянием конфликтных файлов.
        
        Returns:
            Optional[Dict[str, Note]]: Словарь заметок или None при ошибке
        """
        cloud_file = self.get_cloud_file_path()
        
        if not cloud_file:
            logger.warning("Облачная папка не настроена")
            return None
        
        if not cloud_file.exists():
            logger.info("Облачный файл не существует, создается новый")
            return {}
        
        try:
            # Загружаем основной файл
            with open(cloud_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            notes_data = data.get("notes", {})
            remote_notes = {note_id: Note.from_dict(note_data) 
                           for note_id, note_data in notes_data.items()}
            
            logger.info("Загружено заметок из основного файла: %d", len(remote_notes))
            
            # Ищем и обрабатываем конфликтные файлы OneDrive
            conflict_files = self.find_conflict_files()
            
            if conflict_files:
                logger.warning("Обнаружено конфликтных файлов OneDrive: %d", len(conflict_files))
                
                for conflict_file in conflict_files:
                    try:
                        with open(conflict_file, 'r', encoding='utf-8') as f:
                            conflict_data = json.load(f)
                        
                        conflict_notes_data = conflict_data.get("notes", {})
                        
                        # Сливаем заметки из конфликтного файла
                        for note_id, note_data in conflict_notes_data.items():
                            conflict_note = Note.from_dict(note_data)
                            
                            if note_id in remote_notes:
                                # Применяем LWW для конфликтных заметок
                                existing_note = remote_notes[note_id]
                                existing_time = datetime.fromisoformat(existing_note.last_modified.replace('Z', '+00:00'))
                                conflict_time = datetime.fromisoformat(conflict_note.last_modified.replace('Z', '+00:00'))
                                
                                if conflict_time > existing_time:
                                    remote_notes[note_id] = conflict_note
                                    logger.info("Заметка %s обновлена из конфликтного файла (новее)", note_id[:8])
                            else:
                                # Заметка есть только в конфликтном файле
                                remote_notes[note_id] = conflict_note
                                logger.info("Заметка %s добавлена из конфликтного файла", note_id[:8])
                        
                        # Удаляем обработанный конфликтный файл
                        conflict_file.unlink()
                        logger.info("Конфликтный файл обработан и удалён: %s", conflict_file.name)
                    
                    except Exception as e:
                        logger.error("Ошибка при обработке конфликтного файла %s: %s", conflict_file.name, e)
            
            logger.info("Всего загружено удаленных заметок (включая конфликты): %d", len(remote_notes))
            return remote_notes
        
        except json.JSONDecodeError as e:
            logger.error("Ошибка при разборе облачного JSON: %s", e)
            return None
        
        except Exception as e:
            logger.error("Ошибка при загрузке удаленных заметок: %s", e)
            return None
    
    def save_remote_notes(self, notes: Dict[str, Note]) -> bool:
        """
        Сохранение заметок в облачное хранилище.
        
        Args:
            notes: Словарь заметок для сохранения
            
        Returns:
            bool: True если успешно, False иначе
        """
        cloud_file = self.get_cloud_file_path()
        
        if not cloud_file:
            logger.error("Облачная папка не настроена")
            return False
        
        try:
            data = {
                "notes": {note_id: note.to_dict() for note_id, note in notes.items()},
                "meta": {
                    "last_sync": datetime.now(timezone.utc).isoformat(),
                    "count": len(notes)
                }
            }
            
            # Атомарная запись
            temp_file = cloud_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            temp_file.replace(cloud_file)
            logger.info("Сохранено удаленных заметок: %d", len(notes))
            return True
        
        except Exception as e:
            logger.error("Ошибка при сохранении удаленных заметок: %s", e)
            return False
    
    def detect_conflicts(self, local_note: Note, remote_note: Note) -> bool:
        """
        Определение наличия конфликта между локальной и удаленной версией.
        
        Конфликт возникает когда:
        - Обе заметки изменены (version > 1)
        - Временные метки очень близки (< 5 секунд)
        - Содержимое различается
        
        Args:
            local_note: Локальная версия заметки
            remote_note: Удаленная версия заметки
            
        Returns:
            bool: True если есть конфликт, False иначе
        """
        try:
            # Парсим временные метки
            local_time = datetime.fromisoformat(local_note.last_modified.replace('Z', '+00:00'))
            remote_time = datetime.fromisoformat(remote_note.last_modified.replace('Z', '+00:00'))
            
            # Разница во времени
            time_diff = abs((local_time - remote_time).total_seconds())
            
            # Конфликт если обе изменены недавно и содержимое разное
            if time_diff < 5 and (local_note.body != remote_note.body or local_note.title != remote_note.title):
                logger.warning("Обнаружен конфликт для заметки %s", local_note.id[:8])
                return True
            
            return False
        
        except Exception as e:
            logger.error("Ошибка при определении конфликта: %s", e)
            return False
    
    def merge_notes(self, local_notes: Dict[str, Note], 
                    remote_notes: Dict[str, Note]) -> Tuple[Dict[str, Note], List[SyncConflict]]:
        """
        Слияние локальных и удаленных заметок по алгоритму Last-Writer-Wins с поддержкой tombstones.
        
        Алгоритм:
        1. Для заметок только в одном месте - берем их (включая tombstones)
        2. Для заметок в обоих местах:
           - Если хотя бы одна помечена deleted - берем более свежую версию (tombstone побеждает)
           - Сравниваем last_modified
           - Берем более свежую
           - При конфликте создаем SyncConflict
        
        Args:
            local_notes: Локальные заметки (включая tombstones)
            remote_notes: Удаленные заметки (включая tombstones)
            
        Returns:
            Tuple[Dict[str, Note], List[SyncConflict]]: 
                Объединенные заметки (включая tombstones) и список конфликтов
        """
        merged_notes = {}
        conflicts = []
        
        all_ids = set(local_notes.keys()) | set(remote_notes.keys())
        
        for note_id in all_ids:
            local_note = local_notes.get(note_id)
            remote_note = remote_notes.get(note_id)
            
            # Заметка только локально (включая tombstone)
            if local_note and not remote_note:
                merged_notes[note_id] = local_note
                if local_note.deleted:
                    logger.debug("Tombstone %s только локально", note_id[:8])
                else:
                    logger.debug("Заметка %s только локально", note_id[:8])
                continue
            
            # Заметка только удаленно (включая tombstone)
            if remote_note and not local_note:
                merged_notes[note_id] = remote_note
                if remote_note.deleted:
                    logger.debug("Tombstone %s только удаленно", note_id[:8])
                else:
                    logger.debug("Заметка %s только удаленно", note_id[:8])
                continue
            
            # Заметка в обоих местах - нужно слияние
            if local_note and remote_note:
                # Особая обработка tombstones: всегда берем более свежий tombstone
                if local_note.deleted or remote_note.deleted:
                    local_time = datetime.fromisoformat(local_note.last_modified.replace('Z', '+00:00'))
                    remote_time = datetime.fromisoformat(remote_note.last_modified.replace('Z', '+00:00'))
                    
                    if local_time >= remote_time:
                        merged_notes[note_id] = local_note
                        logger.debug("Tombstone: локальная версия новее для %s", note_id[:8])
                    else:
                        merged_notes[note_id] = remote_note
                        logger.debug("Tombstone: удаленная версия новее для %s", note_id[:8])
                    continue
                
                # Обычное слияние для активных заметок
                # Проверка на конфликт
                if self.detect_conflicts(local_note, remote_note):
                    conflict = SyncConflict(note_id, local_note, remote_note)
                    conflicts.append(conflict)
                    # При конфликте берем локальную версию, удаленная сохранится отдельно
                    merged_notes[note_id] = local_note
                    logger.warning("Конфликт для заметки %s", note_id[:8])
                    continue
                
                # LWW: сравниваем время изменения
                local_time = datetime.fromisoformat(local_note.last_modified.replace('Z', '+00:00'))
                remote_time = datetime.fromisoformat(remote_note.last_modified.replace('Z', '+00:00'))
                
                if local_time >= remote_time:
                    merged_notes[note_id] = local_note
                    logger.debug("Локальная версия новее для %s", note_id[:8])
                else:
                    merged_notes[note_id] = remote_note
                    logger.debug("Удаленная версия новее для %s", note_id[:8])
        
        # Подсчитываем активные заметки и tombstones
        active_count = sum(1 for note in merged_notes.values() if not note.deleted)
        tombstone_count = sum(1 for note in merged_notes.values() if note.deleted)
        
        logger.info("Слияние завершено: %d активных заметок, %d tombstones, %d конфликтов", 
                   active_count, tombstone_count, len(conflicts))
        
        return merged_notes, conflicts
    
    def create_conflict_note(self, conflict: SyncConflict) -> Note:
        """
        Создание заметки-конфликта для ручного разрешения.
        
        Args:
            conflict: Объект конфликта
            
        Returns:
            Note: Заметка с удаленной версией и префиксом конфликта
        """
        remote_note = conflict.remote_note
        conflict_title = f"⚠️ Конфликт: {remote_note.title}"
        
        conflict_note = Note(
            title=conflict_title,
            body=remote_note.body,
            last_modified=remote_note.last_modified,
            version=remote_note.version
        )
        
        logger.info("Создана заметка-конфликт: %s", conflict_note.id[:8])
        return conflict_note
    
    def sync(self) -> Tuple[bool, int, int]:
        """
        Выполнение полной синхронизации.
        
        Returns:
            Tuple[bool, int, int]: (успех, количество синхронизированных, количество конфликтов)
        """
        try:
            if not self.cloud_path:
                logger.error("Облачная папка не настроена")
                return False, 0, 0
            
            logger.info("Начало синхронизации...")
            
            # Загружаем удаленные заметки
            remote_notes = self.load_remote_notes()
            if remote_notes is None:
                logger.error("Не удалось загрузить удаленные заметки")
                return False, 0, 0
            
            # Получаем локальные заметки ВКЛЮЧАЯ TOMBSTONES для правильной синхронизации удаления
            local_notes = {note.id: note for note in self.local_store.get_all_notes_including_deleted()}
            
            # Слияние
            merged_notes, conflicts = self.merge_notes(local_notes, remote_notes)
            
            # Сохраняем конфликты
            self.conflicts = conflicts
            for conflict in conflicts:
                conflict_note = self.create_conflict_note(conflict)
                merged_notes[conflict_note.id] = conflict_note
            
            # Обновляем локальное хранилище
            self.local_store.notes = merged_notes
            self.local_store.save()
            
            # Сохраняем в облако
            if not self.save_remote_notes(merged_notes):
                logger.error("Не удалось сохранить в облако")
                return False, 0, len(conflicts)
            
            # Очистка старых tombstones (удаление заметок, помеченных как deleted более 30 дней назад)
            cleaned_count = self.local_store.cleanup_tombstones(older_than_days=30)
            if cleaned_count > 0:
                # Пересохраняем в облако после очистки tombstones
                self.save_remote_notes(self.local_store.notes)
            
            # Подсчёт активных заметок (без tombstones)
            active_count = sum(1 for note in merged_notes.values() if not note.deleted)
            conflict_count = len(conflicts)
            
            logger.info("Синхронизация завершена: %d активных заметок, %d конфликтов, %d tombstones очищено", 
                       active_count, conflict_count, cleaned_count)
            
            return True, active_count, conflict_count
        
        except Exception as e:
            logger.error("Ошибка при синхронизации: %s", e)
            return False, 0, 0
    
    def _load_config(self):
        """Загрузка конфигурации из файла."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    cloud_path_str = config.get('cloud_path')
                    if cloud_path_str:
                        self.cloud_path = Path(cloud_path_str)
                        logger.info("Загружен путь к облаку из конфига: %s", self.cloud_path)
        except Exception as e:
            logger.warning("Не удалось загрузить конфигурацию: %s", e)
    
    def _save_config(self):
        """Сохранение конфигурации в файл."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            config = {
                'cloud_path': str(self.cloud_path) if self.cloud_path else None
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info("Конфигурация сохранена")
        except Exception as e:
            logger.error("Не удалось сохранить конфигурацию: %s", e)


if __name__ == "__main__":
    # Тестирование модуля синхронизации
    print("Тестирование модуля sync.py\n")
    
    # Создаем локальное хранилище
    store = NoteStore()
    print(f"Локальное хранилище: {len(store)} заметок\n")
    
    # Создаем менеджер синхронизации
    sync_manager = SyncManager(store)
    print("✓ SyncManager создан")
    
    # Тест установки пути
    test_path = Path.home() / "Desktop"
    if sync_manager.set_cloud_path(test_path):
        print(f"✓ Путь к облаку установлен: {test_path}")
    
    print("\n✓ Модуль синхронизации готов к использованию!")
