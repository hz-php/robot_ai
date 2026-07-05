"""
Initial migration script for Robot AI database.

Creates all required tables: users, face_profiles, voice_profiles, events.

Run this script to create the initial database schema:
    python migration_initial.py
"""

from database.db import engine
from sqlalchemy import text


def create_tables():
    """Создает начальные таблицы базы данных"""

    with engine.connect() as connection:

        print("[MIGRATION] Starting initial tables creation...")

        try:
            # Создание таблицы users
            print("[MIGRATION] Creating users table...")
            connection.execute(
                text("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        role VARCHAR(50) NOT NULL DEFAULT 'GUEST',
                        active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
            )
            connection.commit()
            print("[MIGRATION] ✅ Created users table")

            # Создание таблицы face_profiles
            print("[MIGRATION] Creating face_profiles table...")
            connection.execute(
                text("""
                    CREATE TABLE IF NOT EXISTS face_profiles (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        face_label INT NOT NULL UNIQUE,
                        model_path VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """)
            )
            connection.commit()
            print("[MIGRATION] ✅ Created face_profiles table")

            # Создание таблицы voice_profiles
            print("[MIGRATION] Creating voice_profiles table...")
            connection.execute(
                text("""
                    CREATE TABLE IF NOT EXISTS voice_profiles (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        profile_features JSON,
                        profile_std JSON,
                        samples_count INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_user_id (user_id),
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """)
            )
            connection.commit()
            print("[MIGRATION] ✅ Created voice_profiles table")

            # Создание таблицы events
            print("[MIGRATION] Creating events table...")
            connection.execute(
                text("""
                    CREATE TABLE IF NOT EXISTS events (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        event_type VARCHAR(255),
                        payload JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            )
            connection.commit()
            print("[MIGRATION] ✅ Created events table")

            print("[MIGRATION] ✅ Initial migration completed successfully!")

        except Exception as e:
            print(f"[MIGRATION ERROR] {e}")
            return False

    return True


if __name__ == "__main__":
    create_tables()