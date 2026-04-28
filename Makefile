.PHONY: up down dev reset logs shell migrate data seed demo

# Levantar DB + Redis en background
up:
	docker compose up -d

# Bajar contenedores
down:
	docker compose down

# Servidor de desarrollo (levanta Docker y espera que PostgreSQL esté listo)
dev: up
	@echo "Esperando PostgreSQL..."
	@until docker exec guyacanes_db pg_isready -q; do sleep 1; done
	uv run python manage.py runserver 0.0.0.0:8000

# Migraciones
migrate:
	uv run python manage.py migrate

# Cargar datos iniciales (fixtures + geodatos)
data:
	uv run python manage.py loaddata apps/core/fixtures/services.json
	uv run python manage.py loaddata apps/core/fixtures/aspects.json
	uv run python manage.py loaddata apps/infra_servicios_publicos_urbaser/fixtures/service_content.json
	uv run python manage.py loaddata apps/infra_servicios_publicos_urbaser/fixtures/aspect_content.json
	uv run python manage.py load_communes
	uv run python manage.py load_neighborhoods
	uv run python manage.py load_public_spaces
	uv run python manage.py load_sweeping
	uv run python manage.py load_green_zone_assignments
	uv run python manage.py load_cutting_schedule

# Denuncias de prueba para demo
seed:
	uv run python manage.py seed_complaints

# Setup completo para demo (datos + seed)
demo: reset seed
	@echo "Demo listo: abrir /admin y /api/v1/"

# Setup completo desde cero
reset: migrate data
	@echo "Base de datos lista."

# Logs de Docker
logs:
	docker compose logs -f

# Shell de Django
shell:
	uv run python manage.py shell
