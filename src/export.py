"""
Модуль экспорта заметок в различные форматы.
"""

import logging
from pathlib import Path
from datetime import datetime
from notes import Note

logger = logging.getLogger(__name__)


class NoteExporter:
    """Класс для экспорта заметок в различные форматы."""
    
    @staticmethod
    def export_to_markdown(note: Note, file_path: Path) -> bool:
        """
        Экспорт заметки в формат Markdown с front-matter метаданными.
        
        Args:
            note: Заметка для экспорта
            file_path: Путь к файлу для сохранения
        
        Returns:
            bool: True если успешно, False иначе
        """
        try:
            content = f"""---
title: {note.title}
tags: {', '.join(note.tags) if note.tags else ''}
created: {note.last_modified}
id: {note.id}
---

{note.body}
"""
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Заметка экспортирована в Markdown: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка экспорта в Markdown: {e}")
            return False
    
    @staticmethod
    def export_to_txt(note: Note, file_path: Path) -> bool:
        """
        Экспорт заметки в формат Plain Text (только текст).
        
        Args:
            note: Заметка для экспорта
            file_path: Путь к файлу для сохранения
        
        Returns:
            bool: True если успешно, False иначе
        """
        try:
            content = f"{note.title}\n\n{note.body}"
            
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Заметка экспортирована в TXT: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка экспорта в TXT: {e}")
            return False
    
    @staticmethod
    def export_to_html(note: Note, file_path: Path) -> bool:
        """
        Экспорт заметки в формат HTML с CSS стилями.
        
        Args:
            note: Заметка для экспорта
            file_path: Путь к файлу для сохранения
        
        Returns:
            bool: True если успешно, False иначе
        """
        try:
            # Экранируем HTML
            import html
            title_escaped = html.escape(note.title)
            body_escaped = html.escape(note.body).replace('\n', '<br>\n')
            tags_html = ', '.join([html.escape(tag) for tag in note.tags]) if note.tags else 'Нет тегов'
            
            content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title_escaped}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{
            color: #2196F3;
            border-bottom: 2px solid #2196F3;
            padding-bottom: 10px;
        }}
        .metadata {{
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            font-size: 14px;
        }}
        .metadata strong {{
            color: #555;
        }}
        .content {{
            margin-top: 30px;
            font-size: 16px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <h1>{title_escaped}</h1>
    
    <div class="metadata">
        <p><strong>Теги:</strong> {tags_html}</p>
        <p><strong>Дата изменения:</strong> {note.last_modified}</p>
        <p><strong>ID:</strong> {note.id}</p>
    </div>
    
    <div class="content">
        {body_escaped}
    </div>
    
    <div class="footer">
        <p>Экспортировано из Notes App • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
"""
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Заметка экспортирована в HTML: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка экспорта в HTML: {e}")
            return False
    
    @staticmethod
    def export_all_to_zip(notes: list, zip_path: Path, format_type: str = 'markdown') -> bool:
        """
        Экспорт всех заметок в ZIP архив.
        
        Args:
            notes: Список заметок для экспорта
            zip_path: Путь к ZIP файлу
            format_type: Формат экспорта ('markdown', 'txt', 'html')
        
        Returns:
            bool: True если успешно, False иначе
        """
        import zipfile
        import tempfile
        import shutil
        
        try:
            # Создаем временную директорию
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Экспортируем каждую заметку
                for note in notes:
                    # Безопасное имя файла
                    safe_title = "".join(c for c in note.title if c.isalnum() or c in (' ', '-', '_')).strip()
                    if not safe_title:
                        safe_title = f"note_{note.id[:8]}"
                    
                    if format_type == 'markdown':
                        file_name = f"{safe_title}.md"
                        file_path = temp_path / file_name
                        NoteExporter.export_to_markdown(note, file_path)
                    elif format_type == 'txt':
                        file_name = f"{safe_title}.txt"
                        file_path = temp_path / file_name
                        NoteExporter.export_to_txt(note, file_path)
                    elif format_type == 'html':
                        file_name = f"{safe_title}.html"
                        file_path = temp_path / file_name
                        NoteExporter.export_to_html(note, file_path)
                
                # Создаем ZIP архив
                zip_path.parent.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in temp_path.iterdir():
                        zipf.write(file_path, file_path.name)
                
                logger.info(f"Все заметки экспортированы в ZIP: {zip_path}")
                return True
        except Exception as e:
            logger.error(f"Ошибка экспорта в ZIP: {e}")
            return False
