"""
Репозиторий для работы с пользователями.
"""

from database.models import User


class UserRepository:
    """
    Repository для управления пользователями.
    
    Предоставляет CRUD операции для модели User.
    """

    def __init__(self, db):
        self.db = db

    def get_by_id(self, user_id):
        """
        Получить пользователя по ID.
        
        Args:
            user_id: Уникальный идентификатор пользователя
            
        Returns:
            User или None
        """
        return (
            self.db.query(User)
            .filter(User.id == user_id)
            .first()
        )

    def get_by_name(self, name):
        """
        Получить пользователя по имени.
        
        Args:
            name: Имя пользователя
            
        Returns:
            User или None
        """
        return (
            self.db.query(User)
            .filter(User.name == name)
            .first()
        )

    def get_all(self):
        """
        Получить всех пользователей.
        
        Returns:
            Список всех пользователей
        """
        return (
            self.db.query(User)
            .all()
        )

    def create(self, name, role="GUEST"):
        """
        Создать нового пользователя.
        
        Args:
            name: Имя пользователя
            role: Роль (по умолчанию GUEST)
            
        Returns:
            Созданный пользователь
        """
        user = User(
            name=name,
            role=role
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def delete(self, user_id):
        """
        Удалить пользователя.
        
        Args:
            user_id: ID пользователя для удаления
            
        Returns:
            True если удалено, False если не найден
        """
        user = self.get_by_id(user_id)

        if not user:
            return False

        self.db.delete(user)
        self.db.commit()

        return True