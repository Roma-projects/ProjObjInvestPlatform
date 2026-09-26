-- Для чего нужен этот файл:
-- Создаёт базы данных PostgreSQL для сервисов проекта при первоначальной настройке.

-- Инициализация БД для каждого микросервиса
-- Используется при раскомментировании Docker (docker-entrypoint-initdb.d)

CREATE DATABASE auth_db;
CREATE DATABASE listing_db;
CREATE DATABASE messaging_db;
CREATE DATABASE analytics_db;
