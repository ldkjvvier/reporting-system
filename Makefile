.PHONY: up down logs build test create-admin

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api worker beat

build:
	docker compose build

test:
	docker compose run --rm api pytest -q

# Crea/promueve el administrador global inicial (no hay registro público).
# Uso: make create-admin EMAIL=admin@empresa.com PASSWORD=CambiaEsto123
create-admin:
	docker compose run --rm api python -m app.create_admin --email "$(EMAIL)" --password "$(PASSWORD)"
