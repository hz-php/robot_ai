"""
Репозиторий для работы с событиями.
"""

from database.models import Event
from datetime import datetime, timedelta


class EventRepository:
    """
    Repository для управления событиями системы.
    
    Предоставляет операции для логирования и чтения событий.
    """

    def __init__(self, db):
        self.db = db

    def create(self, event_type, payload=None):
        """
        Создать событие.
        
        Args:
            event_type: Тип события (строка)
            payload: Данные события (JSON, опционально)
            
        Returns:
            Созданное Event
        """
        event = Event(
            event_type=event_type,
            payload=payload
        )

        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        return event

    def get_all(self):
        """
        Получить все события.
        
        Returns:
            Список всех событий
        """
        return (
            self.db.query(Event)
            .all()
        )

    def get_recent(self, limit=100):
        """
        Получить последние события.
        
        Args:
            limit: Максимальное количество событий
            
        Returns:
            Список последних событий
        """
        return (
            self.db.query(Event)
            .order_by(Event.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_by_type(self, event_type, limit=100):
        """
        Получить события по типу.
        
        Args:
            event_type: Тип события для фильтра
            limit: Максимальное количество
            
        Returns:
            Список событий указанного типа
        """
        return (
            self.db.query(Event)
            .filter(Event.event_type == event_type)
            .order_by(Event.created_at.desc())
            .limit(limit)
            .all()
        )

    def clear_old_events(self, days=30):
        """
        Удалить события старше N дней.
        
        Args:
            days: Количество дней для отсечения
            
        Returns:
            True
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        self.db.query(Event).filter(Event.created_at < cutoff_date).delete()
        self.db.commit()

        return True