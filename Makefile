# Частые команды проекта. Выполняйте их из корня репозитория.

.PHONY: help up down rebuild restart ps logs build install

help:
	@echo "make up       - собрать образы и запустить весь Compose-контур"
	@echo "make down     - остановить контейнеры, сохранив volumes"
	@echo "make rebuild  - пересобрать образы и перезапустить Compose"
	@echo "make ps       - показать состояние контейнеров"
	@echo "make logs     - следить за логами всех контейнеров"
	@echo "make build    - собрать образы без запуска"
	@echo "make install  - установить корневой requirements.txt в активное venv"

up:
	docker compose up --build -d

down:
	docker compose down

rebuild:
	docker compose down
	docker compose up --build -d

restart:
	docker compose restart

ps:
	docker compose ps

logs:
	docker compose logs -f

build:
	docker compose build

install:
	python -m pip install -r requirements.txt
