"""
База данных SQLAlchemy
Создает движок и фабрику сессий для работы с MySQL.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL

# Движок SQLAlchemy с пулом соединений
engine = create_engine(
    DATABASE_URL,
    echo=False,           # Логирование SQL запросов
    pool_pre_ping=True    # Переподключение при падении соединения
)

# Фабрика сессий
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    """
    Генератор сессий для dependency injection.
    
    Yields:
        Session: SQLAlchemy сессия
    """
    db = SessionLocal()
    
    try:
        yield db
    finally:
        db.close()