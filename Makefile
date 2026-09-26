# Для чего нужен этот файл:
# Содержит короткие команды для частых задач проекта, например запуск сервисов и применение миграций.

# Real Estate Aggregator — Makefile
# Docker временно отключён (см. docker-compose.yml). Локальный запуск: Start_test.py

.PHONY: help up down rebuild migrate logs start-all start-auth start-listing start-search start-messaging start-analytics start-notification install-shared

help:
	@echo "Commands:"
	@echo "  make start-all          - запуск всех сервисов (Start_test.py)"
	@echo "  make start-auth         - только auth-service :8001"
	@echo "  make start-listing      - только listing-service :8002"
	@echo "  make start-search       - только search-service :8003"
	@echo "  make start-messaging    - только messaging-service :8004"
	@echo "  make start-analytics    - только analytics-service :8005"
	@echo "  make start-notification - только notification-service :8006"
	@echo "  make install-shared     - pip install -e ./shared"
	@echo "  make up/down/rebuild    - Docker (сейчас отключён)"
	@echo "  make migrate            - alembic upgrade head (все сервисы с БД)"
	@echo "  make logs               - подсказка по логам"

# --- Docker (закомментировано в docker-compose.yml) ---
up:
	@echo "[!] Docker Compose временно отключён. Используйте: make start-all"
	@echo "    Чтобы включить: раскомментируйте docker-compose.yml"
	# docker compose up -d --build

down:
	@echo "[!] Docker Compose временно отключён."
	# docker compose down

rebuild:
	@echo "[!] Docker Compose временно отключён."
	# docker compose up -d --build --force-recreate

logs:
	@echo "[!] Docker отключён. Логи пишутся в stdout запущенных Start_test.py процессов."
	# docker compose logs -f

migrate:
	@echo "Running Alembic migrations..."
	cd auth-service && alembic upgrade head || true
	cd listing-service && alembic upgrade head || true
	cd messaging-service && alembic upgrade head || true
	cd analytics-service && alembic upgrade head || true

install-shared:
	pip install -e ./shared

start-all:
	python Start_test.py

start-auth:
	python auth-service/Start_test.py

start-listing:
	python listing-service/Start_test.py

start-search:
	python search-service/Start_test.py

start-messaging:
	python messaging-service/Start_test.py

start-analytics:
	python analytics-service/Start_test.py

start-notification:
	python notification-service/Start_test.py
