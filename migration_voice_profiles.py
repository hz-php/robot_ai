"""
Migration script to update voice_profiles table structure

Run this script to update the database schema:
    python migration_voice_profiles.py
"""

from database.db import engine
from sqlalchemy import text


def migrate_voice_profiles():
    """Обновляет структуру таблицы voice_profiles"""

    with engine.connect() as connection:
        
        print("[MIGRATION] Starting voice_profiles table migration...")

        try:
            # Проверяем существует ли колонка profile_features
            result = connection.execute(
                text("""
                    SELECT COLUMN_NAME 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME='voice_profiles' AND COLUMN_NAME='profile_features'
                """)
            )
            
            if not result.fetchone():
                print("[MIGRATION] Adding profile_features column...")
                connection.execute(
                    text("""
                        ALTER TABLE voice_profiles 
                        ADD COLUMN profile_features JSON
                    """)
                )
                connection.commit()
                print("[MIGRATION] ✅ Added profile_features")

            # Проверяем существует ли колонка profile_std
            result = connection.execute(
                text("""
                    SELECT COLUMN_NAME 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME='voice_profiles' AND COLUMN_NAME='profile_std'
                """)
            )
            
            if not result.fetchone():
                print("[MIGRATION] Adding profile_std column...")
                connection.execute(
                    text("""
                        ALTER TABLE voice_profiles 
                        ADD COLUMN profile_std JSON
                    """)
                )
                connection.commit()
                print("[MIGRATION] ✅ Added profile_std")

            # Проверяем существует ли колонка samples_count
            result = connection.execute(
                text("""
                    SELECT COLUMN_NAME 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME='voice_profiles' AND COLUMN_NAME='samples_count'
                """)
            )
            
            if not result.fetchone():
                print("[MIGRATION] Adding samples_count column...")
                connection.execute(
                    text("""
                        ALTER TABLE voice_profiles 
                        ADD COLUMN samples_count INT DEFAULT 0
                    """)
                )
                connection.commit()
                print("[MIGRATION] ✅ Added samples_count")

            # Проверяем существует ли колонка updated_at
            result = connection.execute(
                text("""
                    SELECT COLUMN_NAME 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME='voice_profiles' AND COLUMN_NAME='updated_at'
                """)
            )
            
            if not result.fetchone():
                print("[MIGRATION] Adding updated_at column...")
                connection.execute(
                    text("""
                        ALTER TABLE voice_profiles 
                        ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    """)
                )
                connection.commit()
                print("[MIGRATION] ✅ Added updated_at")

            # Проверяем индекс на user_id
            result = connection.execute(
                text("""
                    SELECT INDEX_NAME 
                    FROM INFORMATION_SCHEMA.STATISTICS 
                    WHERE TABLE_NAME='voice_profiles' AND COLUMN_NAME='user_id'
                """)
            )
            
            if not result.fetchone():
                print("[MIGRATION] Adding index on user_id...")
                connection.execute(
                    text("""
                        ALTER TABLE voice_profiles 
                        ADD INDEX idx_user_id (user_id)
                    """)
                )
                connection.commit()
                print("[MIGRATION] ✅ Added index on user_id")

            print("[MIGRATION] ✅ Migration completed successfully!")

        except Exception as e:
            print(f"[MIGRATION ERROR] {e}")
            return False

    return True


if __name__ == "__main__":
    migrate_voice_profiles()
