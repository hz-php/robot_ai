# Инструкция по миграции БД voice_profiles

Таблица `voice_profiles` требует обновления структуры для поддержки распознавания голоса.

## Вариант 1: Автоматическая миграция (рекомендуется)

```bash
python migration_voice_profiles.py
```

Скрипт автоматически добавит необходимые колонки:
- `profile_features` (JSON) - MFCC коэффициенты голоса
- `profile_std` (JSON) - стандартное отклонение признаков
- `samples_count` (INT) - количество образцов для обучения
- `updated_at` (TIMESTAMP) - время последнего обновления
- INDEX на `user_id`

## Вариант 2: Ручная миграция через phpMyAdmin

```sql
-- Добавить колонку profile_features
ALTER TABLE voice_profiles 
ADD COLUMN profile_features JSON;

-- Добавить колонку profile_std
ALTER TABLE voice_profiles 
ADD COLUMN profile_std JSON;

-- Добавить колонку samples_count
ALTER TABLE voice_profiles 
ADD COLUMN samples_count INT DEFAULT 0;

-- Добавить колонку updated_at
ALTER TABLE voice_profiles 
ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- Добавить индекс на user_id
ALTER TABLE voice_profiles 
ADD INDEX idx_user_id (user_id);
```

## Проверка структуры после миграции

```sql
DESCRIBE voice_profiles;
```

Должно быть:
```
id              | int       | PRIMARY KEY, AUTO_INCREMENT
user_id         | int       | FOREIGN KEY, INDEX
profile_features| json      | 
profile_std     | json      |
samples_count   | int       |
voice_file      | varchar   | (старое поле, может быть удалено)
created_at      | timestamp |
updated_at      | timestamp |
```

## После миграции

Приложение готово использовать распознавание голоса с сохранением профилей в БД!

Процесс обучения:
1. Пользователь говорит "запомни мой голос"
2. Запись 5 голосовых образцов
3. Вычисление MFCC признаков
4. Сохранение в таблице `voice_profiles`
5. При следующем разговоре робот узнаёт пользователя по голосу
