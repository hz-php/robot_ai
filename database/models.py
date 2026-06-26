"""
ORM модели проекта Robot AI.

Определяет структуру таблиц: пользователи, лица, голосовые профили, события.
"""

from sqlalchemy.orm import declarative_base
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    TIMESTAMP
)
from datetime import datetime

# Базовый класс для всех моделей
Base = declarative_base()


class User(Base):
    """
    Пользователь системы.
    
    Атрибуты:
        id: Уникальный идентификатор
        name: Имя пользователя
        role: Роль (ADMIN, GUEST, OPERATOR)
        active: Флаг активности
        created_at: Дата создания
        updated_at: Дата обновления
    """

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    name = Column(
        String(255),
        nullable=False
    )

    role = Column(
        String(50),
        nullable=False,
        default="GUEST"
    )

    active = Column(
        Boolean,
        default=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


class FaceProfile(Base):
    """
    Профиль лица пользователя.
    
    Атрибуты:
        id: Уникальный идентификатор
        user_id: Ссылка на пользователя
        face_label: Метка для LBPH распознавателя
        model_path: Путь к модели (опционально)
        created_at: Дата создания
    """

    __tablename__ = "face_profiles"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    face_label = Column(
        Integer,
        nullable=False,
        unique=True
    )

    model_path = Column(
        String(255),
        nullable=True,
        default=None
    )

    created_at = Column(
        TIMESTAMP,
        nullable=True,
        default=datetime.utcnow
    )


class VoiceProfile(Base):
    """
    Голосовой профиль пользователя.
    
    Атрибуты:
        id: Уникальный идентификатор
        user_id: Ссылка на пользователя
        profile_features: MFCC признаки голоса (JSON)
        profile_std: Стандартные отклонения признаков (JSON)
        samples_count: Количество записей для обучения
        created_at: Дата создания
        updated_at: Дата обновления
    """

    __tablename__ = "voice_profiles"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    profile_features = Column(
        JSON,
        nullable=True
    )

    profile_std = Column(
        JSON,
        nullable=True
    )

    samples_count = Column(
        Integer,
        default=0
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


class Event(Base):
    """
    Событие в системе.
    
    Атрибуты:
        id: Уникальный идентификатор
        event_type: Тип события
        payload: Данные события (JSON)
        created_at: Дата создания
    """

    __tablename__ = "events"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    event_type = Column(
        String(255)
    )

    payload = Column(
        JSON
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )