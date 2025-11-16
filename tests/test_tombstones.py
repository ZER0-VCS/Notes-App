"""
Тестовый скрипт для проверки tombstones и обработки конфликтных файлов OneDrive.

Проверяет:
1. Мягкое удаление заметок (tombstones)
2. Синхронизацию удаления между устройствами
3. Автоматическое слияние конфликтных файлов OneDrive
4. Очистку старых tombstones
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from notes import Note, NoteStore
from sync import SyncManager

def print_header(text):
    """Красивый заголовок."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")

def create_test_environment():
    """Создание тестового окружения."""
    print_header("🔧 СОЗДАНИЕ ТЕСТОВОГО ОКРУЖЕНИЯ")
    
    # Пути
    test_cloud = Path.home() / ".notes_app" / "test_tombstone_sync"
    test_cloud.mkdir(parents=True, exist_ok=True)
    
    print(f"✅ Тестовая облачная папка: {test_cloud}")
    
    # Очистка предыдущих тестов
    for file in test_cloud.glob("*.json"):
        file.unlink()
    
    return test_cloud

def test_tombstone_sync():
    """Тест синхронизации удаления через tombstones."""
    print_header("🗑️ ТЕСТ 1: Синхронизация удаления (Tombstones)")
    
    test_cloud = create_test_environment()
    
    # Устройство 1: создаём заметки
    print("📱 Устройство 1: Создание заметок...")
    store1 = NoteStore()
    store1.notes = {}  # Очищаем для чистого теста
    
    note1 = Note(title="Заметка для удаления", body="Эта заметка будет удалена")
    note2 = Note(title="Обычная заметка", body="Эта заметка останется")
    
    store1.add_note(note1)
    store1.add_note(note2)
    print(f"   ✓ Создано 2 заметки")
    
    # Синхронизация с облаком
    sync1 = SyncManager(store1, test_cloud)
    success, count, conflicts = sync1.sync()
    print(f"   ✓ Синхронизация: {count} заметок в облаке")
    
    # Устройство 2: загружает заметки
    print("\n📱 Устройство 2: Загрузка заметок из облака...")
    store2 = NoteStore()
    store2.notes = {}
    sync2 = SyncManager(store2, test_cloud)
    success, count, conflicts = sync2.sync()
    
    active_notes = [n for n in store2.get_all_notes()]
    print(f"   ✓ Загружено {len(active_notes)} активных заметок")
    
    # Устройство 1: удаляем заметку (создаём tombstone)
    print("\n📱 Устройство 1: Удаление заметки...")
    store1.delete_note(note1.id)
    all_notes_with_tombstones = store1.get_all_notes_including_deleted()
    active_notes_dev1 = store1.get_all_notes()
    tombstones = [n for n in all_notes_with_tombstones if n.deleted]
    
    print(f"   ✓ Активных заметок: {len(active_notes_dev1)}")
    print(f"   ✓ Tombstones: {len(tombstones)}")
    
    # Синхронизация удаления
    success, count, conflicts = sync1.sync()
    print(f"   ✓ Синхронизация: {count} активных заметок в облаке")
    
    # Устройство 2: проверяет удаление
    print("\n📱 Устройство 2: Синхронизация и проверка удаления...")
    success, count, conflicts = sync2.sync()
    
    active_notes_dev2 = store2.get_all_notes()
    all_notes_dev2 = store2.get_all_notes_including_deleted()
    tombstones_dev2 = [n for n in all_notes_dev2 if n.deleted]
    
    print(f"   ✓ Активных заметок: {len(active_notes_dev2)}")
    print(f"   ✓ Tombstones: {len(tombstones_dev2)}")
    
    # Проверка результата
    print("\n🎯 РЕЗУЛЬТАТ:")
    if len(active_notes_dev2) == 1 and len(tombstones_dev2) == 1:
        print("   ✅ Удаление синхронизировано корректно!")
        print(f"   ✅ Устройство 2 видит tombstone для '{note1.title}'")
        return True
    else:
        print("   ❌ Ошибка синхронизации удаления!")
        return False

def test_onedrive_conflict_files():
    """Тест автоматического слияния конфликтных файлов OneDrive."""
    print_header("🔄 ТЕСТ 2: Обработка конфликтных файлов OneDrive")
    
    test_cloud = create_test_environment()
    
    # Создаём основной файл
    print("📝 Создание основного файла заметок...")
    store_main = NoteStore()
    store_main.notes = {}
    
    note_main = Note(title="Заметка в основном файле", body="Основной файл")
    store_main.add_note(note_main)
    
    sync_main = SyncManager(store_main, test_cloud)
    sync_main.sync()
    print(f"   ✓ Основной файл: 1 заметка")
    
    # Имитируем конфликтный файл OneDrive
    print("\n⚠️ Имитация конфликтного файла OneDrive...")
    conflict_file = test_cloud / "notes-DESKTOP-ABC123.json"
    
    note_conflict = Note(title="Заметка из конфликтного файла", body="Конфликтный файл")
    conflict_data = {
        "notes": {note_conflict.id: note_conflict.to_dict()},
        "meta": {"created": datetime.now(timezone.utc).isoformat(), "count": 1}
    }
    
    with open(conflict_file, 'w', encoding='utf-8') as f:
        json.dump(conflict_data, f, ensure_ascii=False, indent=2)
    
    print(f"   ✓ Создан конфликтный файл: {conflict_file.name}")
    
    # Синхронизация должна автоматически слить файлы
    print("\n🔄 Синхронизация (автоматическое слияние)...")
    store_test = NoteStore()
    store_test.notes = {}
    sync_test = SyncManager(store_test, test_cloud)
    success, count, conflicts = sync_test.sync()
    
    print(f"   ✓ Всего заметок после слияния: {count}")
    
    # Проверка что конфликтный файл удалён
    conflict_exists = conflict_file.exists()
    
    # Результат
    print("\n🎯 РЕЗУЛЬТАТ:")
    if count == 2 and not conflict_exists:
        print("   ✅ Конфликтный файл успешно объединён и удалён!")
        print(f"   ✅ Обе заметки теперь в основном файле")
        return True
    else:
        print(f"   ❌ Ошибка слияния! Заметок: {count}, конфликтный файл существует: {conflict_exists}")
        return False

def test_tombstone_cleanup():
    """Тест очистки старых tombstones."""
    print_header("🧹 ТЕСТ 3: Очистка старых Tombstones")
    
    test_cloud = create_test_environment()
    
    # Создаём хранилище с tombstones разного возраста
    print("📝 Создание заметок и tombstones...")
    store = NoteStore()
    store.notes = {}
    
    # Обычная заметка
    note1 = Note(title="Активная заметка", body="Не удалена")
    store.add_note(note1)
    
    # Свежий tombstone (1 день)
    note2 = Note(title="Недавно удалённая", body="", deleted=True)
    note2.last_modified = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    store.notes[note2.id] = note2
    
    # Старый tombstone (40 дней)
    note3 = Note(title="Давно удалённая", body="", deleted=True)
    note3.last_modified = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    store.notes[note3.id] = note3
    
    store.save()
    
    print(f"   ✓ Активных: 1, Tombstones: 2 (1 свежий, 1 старый)")
    
    # Синхронизация (должна очистить старые tombstones)
    sync = SyncManager(store, test_cloud)
    success, count, conflicts = sync.sync()
    
    # Проверка результата
    active = store.get_all_notes()
    all_notes = store.get_all_notes_including_deleted()
    tombstones = [n for n in all_notes if n.deleted]
    
    print(f"\n🔍 После синхронизации:")
    print(f"   • Активных заметок: {len(active)}")
    print(f"   • Tombstones: {len(tombstones)}")
    
    print("\n🎯 РЕЗУЛЬТАТ:")
    if len(active) == 1 and len(tombstones) == 1:
        print("   ✅ Старые tombstones (>30 дней) успешно очищены!")
        print("   ✅ Свежие tombstones (<30 дней) сохранены")
        return True
    else:
        print(f"   ❌ Ошибка очистки! Активных: {len(active)}, Tombstones: {len(tombstones)}")
        return False

def main():
    """Запуск всех тестов."""
    print("\n" + "🧪" * 35)
    print("  ТЕСТИРОВАНИЕ TOMBSTONES И КОНФЛИКТНЫХ ФАЙЛОВ ONEDRIVE")
    print("🧪" * 35)
    
    results = []
    
    # Тест 1: Синхронизация удаления
    results.append(("Синхронизация удаления (Tombstones)", test_tombstone_sync()))
    
    # Тест 2: Обработка конфликтных файлов
    results.append(("Обработка конфликтных файлов OneDrive", test_onedrive_conflict_files()))
    
    # Тест 3: Очистка старых tombstones
    results.append(("Очистка старых Tombstones", test_tombstone_cleanup()))
    
    # Итоги
    print_header("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {test_name}")
    
    print(f"\n  Пройдено: {passed}/{total}")
    
    if passed == total:
        print("\n  🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return 0
    else:
        print("\n  ⚠️  НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        return 1

if __name__ == "__main__":
    sys.exit(main())
