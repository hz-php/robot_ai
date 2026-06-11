from database.models import Event
from datetime import datetime, timedelta


class EventRepository:

    def __init__(self, db):
        self.db = db

    def create(self, event_type, payload=None):
        """Создать событие"""

        event = Event(
            event_type=event_type,
            payload=payload
        )

        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        return event

    def get_all(self):
        """Получить все события"""

        return (
            self.db.query(Event)
            .all()
        )

    def get_recent(self, limit=100):
        """Получить последние события"""

        return (
            self.db.query(Event)
            .order_by(Event.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_by_type(self, event_type, limit=100):
        """Получить события по типу"""

        return (
            self.db.query(Event)
            .filter(Event.event_type == event_type)
            .order_by(Event.created_at.desc())
            .limit(limit)
            .all()
        )

    def clear_old_events(self, days=30):
        """Удалить события старше N дней"""

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        self.db.query(Event).filter(Event.created_at < cutoff_date).delete()
        self.db.commit()

        return True