from database.models import Event


class EventRepository:

    def __init__(self, db):
        self.db = db

    def create(
        self,
        event_type,
        payload=None
    ):

        event = Event(
            event_type=event_type,
            payload=payload
        )

        self.db.add(event)

        self.db.commit()

        self.db.refresh(event)

        return event

    def get_all(self):

        return (
            self.db.query(Event)
            .all()
        )