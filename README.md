# Guyacanes

Sistema de supervisión y veeduría ciudadana para el servicio público
de aseo urbano — Alcaldía de Popayán, Cauca.

---

## ¿Qué es este sistema?

Cruza el "deber ser" (rutas contractuales del PPS 2024 de Urbaser) contra
la "realidad" (denuncias ciudadanas georeferenciadas) usando PostGIS para
detectar incumplimientos SLA automáticamente.

---

## Stack

- **Backend:** Django 6 + DRF + GeoDjango + djangorestframework-gis
- **Base de datos:** PostgreSQL 16 + PostGIS 3.4
- **Cache/Queue:** Redis 7
- **Python:** 3.13.12 (gestionado con uv)
- **Versiones exactas:** ver `docs/CONTEXT_GUYACANES.md`

---

## Arranque rápido

### Con uv (desarrollador principal)

```bash
git clone <url-del-repo>
cd guyacanes

# Levantar base de datos y Redis
docker compose up -d

# Instalar dependencias
uv sync

# Variables de entorno
cp .env.example .env
# Editar .env con las credenciales

# Migraciones y datos iniciales
uv run python manage.py migrate
uv run python manage.py loaddata fixtures/core_services.json
uv run python manage.py loaddata fixtures/core_aspects.json
uv run python manage.py load_communes
uv run python manage.py load_sweeping

# Servidor de desarrollo
uv run python manage.py runserver 0.0.0.0:8000
```

### Con pip (resto del equipo)

```bash
git clone <url-del-repo>
cd guyacanes

# Levantar base de datos y Redis
docker compose up -d

# Entorno virtual
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# Instalar dependencias
pip install -r requirements.txt

# Variables de entorno
cp .env.example .env
# Editar .env con las credenciales

# Migraciones y datos iniciales
python manage.py migrate
python manage.py loaddata fixtures/core_services.json
python manage.py loaddata fixtures/core_aspects.json
python manage.py load_communes
python manage.py load_sweeping

# Servidor de desarrollo
python manage.py runserver 0.0.0.0:8000
```

---

## Variables de entorno requeridas

Copiar `.env.example` a `.env` y completar:

| Variable               | Requerida | Default     |
| ---------------------- | --------- | ----------- |
| `SECRET_KEY`           | Sí        | —           |
| `DEBUG`                | No        | `False`     |
| `ALLOWED_HOSTS`        | No        | `""`        |
| `DB_NAME`              | Sí        | —           |
| `DB_USER`              | Sí        | —           |
| `DB_PASSWORD`          | Sí        | —           |
| `DB_HOST`              | No        | `localhost` |
| `DB_PORT`              | No        | `5432`      |
| `CORS_ALLOWED_ORIGINS` | No        | `""`        |

---

## Requisitos del sistema

- Docker Desktop
- Python 3.13+
- GDAL 3.8+ (requerido por GeoDjango)
  - macOS: `brew install gdal`
  - Ubuntu: `sudo apt install gdal-bin libgdal-dev`
  - Windows: ver `docs/guia-dependencias.md`

---

## Estructura del proyecto

```
guyacanes/
  apps/
    core/                                         # Catálogo transversal (Commune, Neighborhood, Service, Aspect)
    infra_servicios_publicos_urbaser/             # Servicio de aseo (Veeduría + Operaciones + Auditoría)
    infra_servicios_publicos_urbaser_facturacion/ # Facturación (Fase 2 — pendiente)
  config/
    settings/
      base.py       # Settings comunes
      local.py      # Desarrollo
      production.py # Producción
  data/shapefiles/  # Geodatos POT Popayán (U2_COMUNAS.shp, U18_VIAL.shp, etc.)
  docs/             # Documentación técnica
    api/            # Colecciones Bruno y Postman + referencia API
  fixtures/         # Datos iniciales del catálogo
  media_local/      # Archivos subidos en desarrollo (evidencias)
```

---

## API v1

Base URL: `http://localhost:8000/api/v1/`

### Documentación interactiva

| URL            | Descripción                     |
| -------------- | ------------------------------- |
| `/api/docs/`   | Swagger UI — prueba interactiva |
| `/api/redoc/`  | ReDoc — referencia navegable    |
| `/api/schema/` | OpenAPI 3.0 schema (YAML)       |

Ver referencia conceptual completa en `docs/api/README.md`.

### Core

| Método | Endpoint                        | Descripción           |
| ------ | ------------------------------- | --------------------- |
| GET    | `/core/services/`               | Servicios activos     |
| GET    | `/core/aspects/?service=<slug>` | Aspectos por servicio |
| GET    | `/core/communes/`               | 9 comunas de Popayán  |

### Veeduría

| Método | Endpoint                       | Descripción              |
| ------ | ------------------------------ | ------------------------ |
| POST   | `/urbaser/complaints/`         | Crear denuncia ciudadana |
| GET    | `/urbaser/complaints/`         | Listar denuncias         |
| GET    | `/urbaser/complaints/<id>/`    | Detalle de denuncia      |
| GET    | `/urbaser/complaints/geojson/` | Denuncias como GeoJSON   |
| POST   | `/urbaser/evidence/`           | Subir foto de evidencia  |

### Auditoría SLA

| Método | Endpoint                 | Descripción                 |
| ------ | ------------------------ | --------------------------- |
| GET    | `/urbaser/alerts/`       | Alertas SLA generadas       |
| GET    | `/urbaser/alerts/<id>/`  | Detalle de alerta           |
| GET    | `/urbaser/metrics/`      | Métricas heatmap por comuna |
| GET    | `/urbaser/metrics/<id>/` | Detalle de métrica          |

### Filtros principales

**Complaints:** `?status=received` · `?service_slug=sweeping-cleaning` · `?commune_id=4` · `?is_rural=false` · `?search=limpieza` · `?ordering=-created_at`

**Alerts:** `?violation=true` · `?service_slug=green-zones` · `?route_type=sweeping_microroute` · `?confidence=high` · `?complaint_id=42`

**Metrics:** `?service_slug=sweeping-cleaning` · `?period=2026-04-01` · `?commune_id=4`

---

## Management commands

| Comando            | Descripción                                                      | Fuente                        |
| ------------------ | ---------------------------------------------------------------- | ----------------------------- |
| `load_communes`    | Carga 9 comunas desde shapefile POT                              | `U2_COMUNAS.shp`              |
| `load_sweeping`    | Carga 8 macrorutas + 1,731 microrutas de barrido                 | `U18_VIAL.shp`                |
| `load_green_zones` | Carga 313 zonas verdes (parques, nodos, corredores, separadores) | 5 shapefiles U-19 + SEPARADOR |
| `seed_complaints`  | Genera 14 denuncias de prueba que disparan el pipeline SLA       | —                             |

```bash
# Con Make (recomendado)
make data   # carga fixtures + geodatos
make seed   # denuncias de prueba
make demo   # todo en uno (migrate + data + seed)

# Con uv directamente
uv run python manage.py load_communes
uv run python manage.py load_sweeping
uv run python manage.py load_green_zones
uv run python manage.py seed_complaints
```

---

## Admin

Disponible en `http://localhost:8000/admin`

```bash
python manage.py createsuperuser
```

Ver `docs/admin-guide.md` para la guía completa de modelos, permisos, fieldsets e inlines.

---

## Agregar una dependencia

```bash
# Con uv (desarrollador principal)
uv add nombre-paquete

# Regenerar requirements.txt para el equipo
uv export --format requirements-txt --no-hashes -o requirements.txt
uv export --format requirements-txt --no-hashes --dev -o requirements-dev.txt

# Commitear los tres archivos
git add pyproject.toml uv.lock requirements.txt requirements-dev.txt
```

---

## Documentación

| Documento                                    | Descripción                                                                    |
| -------------------------------------------- | ------------------------------------------------------------------------------ |
| `docs/api/README.md`                         | Referencia completa de la API v1 — endpoints, filtros, ejemplos, campos choice |
| `docs/admin-guide.md`                        | Guía del panel de administración Django                                        |
| `docs/demo-guide.md`                         | Guía paso a paso para correr el demo end-to-end                                |
| `docs/plan-accion-fase1.md`                  | Plan de acción Fase 1 — gaps, pendientes, info faltante                        |
| `docs/changelog-fase-a.md`                   | Changelog de la Fase A — endpoints, fixes, Swagger, fixtures                   |
| `docs/plan-demo-completo.md`                 | Plan de demo completo — integración backend + frontend                         |
| `docs/frontend-changelog.md`                 | Changelog granular del frontend (cambios #1-#5 aplicados)                      |
| `docs/estado-actual.md`                      | **Fuente única de verdad** — estado consolidado del proyecto                   |
| `docs/estrategia-documentacion.md`           | Decisión de dónde vive cada doc (backend vs frontend)                          |
| `docs/CONTEXT_GUYACANES.md`                  | Arquitectura completa, modelos, estado del proyecto                            |
| `docs/rutas-y-servicios.md`                  | Contexto de negocio — rutas PPS 2024, SLA, servicios                           |
| `docs/geodatos.md`                           | Inventario de shapefiles, CRS, comandos de carga                               |
| `docs/barrios-opciones.md`                   | Opciones para cargar barrios (DANE MGN, OSM, Geofabrik)                        |
| `docs/guia-dependencias.md`                  | Setup detallado con uv, GDAL, VS Code                                          |
| `docs/api/guyacanes.bruno/`                  | Colección Bruno (recomendada)                                                  |
| `docs/api/guyacanes.postman_collection.json` | Colección Postman                                                              |
