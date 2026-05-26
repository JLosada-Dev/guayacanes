# Guyacanes — Backend

API REST GeoDjango para el sistema de **veeduría ciudadana** sobre servicios públicos de la Alcaldía de Popayán. Soporta el portal ciudadano público (denuncia anónima georeferenciada) y el portal interno de gestión para personal de la alcaldía (veedor / coordinador).

> Sistema bajo **Ley 850 de 2003** (veeduría ciudadana — control social colectivo). **No es PQR** (Ley 1755/2015): las denuncias son anónimas y no generan derecho a respuesta individual.

---

## Tabla de contenido

- [Stack](#stack)
- [Requisitos del sistema](#requisitos-del-sistema)
- [Setup local](#setup-local)
- [Variables de entorno](#variables-de-entorno)
- [Base de datos y PostGIS](#base-de-datos-y-postgis)
- [Datos geoespaciales (shapefiles y fixtures)](#datos-geoespaciales-shapefiles-y-fixtures)
- [Management commands](#management-commands)
- [Estructura de apps](#estructura-de-apps)
- [Modelos GeoDjango](#modelos-geodjango)
- [API REST](#api-rest)
- [Autenticación y roles](#autenticación-y-roles)
- [Flujo de estado de una denuncia](#flujo-de-estado-de-una-denuncia)
- [Tests](#tests)
- [Admin Django](#admin-django)
- [Documentación adicional](#documentación-adicional)
- [Makefile](#makefile)

---

## Stack

| Componente              | Versión        | Propósito                                    |
| ----------------------- | -------------- | -------------------------------------------- |
| Python                  | `>=3.13`       | Runtime                                      |
| Django                  | `>=6.0, <7.0`  | Framework web                                |
| Django REST Framework   | `>=3.17`       | API REST                                     |
| djangorestframework-gis | `>=1.0`        | Serialización GeoJSON                        |
| djangorestframework-simplejwt | `>=5.5`  | Autenticación JWT (portal staff)             |
| drf-spectacular         | `>=0.29`       | OpenAPI 3, Swagger UI, ReDoc                 |
| PostgreSQL + PostGIS    | `16 + 3.4`     | Base de datos espacial                       |
| GeoPandas               | `>=1.1`        | Lectura de shapefiles en management commands |
| pdfplumber              | `>=0.11`       | Extracción de cronogramas Urbaser (PDF)      |
| Pillow                  | `>=12.1`       | Validación / procesamiento de imágenes       |
| uv                      | —              | Gestor de dependencias y entorno virtual     |

**Gestor de paquetes:** `uv` exclusivamente. No usar `pip install` global.

---

## Requisitos del sistema

### macOS (Apple Silicon)

```bash
brew install python@3.13 postgresql@16 postgis gdal geos uv
```

GeoDjango necesita rutas explícitas a las librerías nativas; ya vienen configuradas en `config/settings/local.py` apuntando a `/opt/homebrew/opt/gdal` y `/opt/homebrew/opt/geos`. Si tu instalación de Homebrew está en otra ruta, sobreescribe con env vars (ver más abajo).

### Linux / WSL

Postgres + PostGIS desde repos oficiales; GDAL y GEOS vía `apt install gdal-bin libgdal-dev libgeos-dev`. Más detalle en [`docs/entorno-python-gdal.md`](docs/entorno-python-gdal.md).

### Docker (alternativa)

`docker-compose.yml` levanta PostgreSQL+PostGIS (puerto 5432) y Redis (6379) listos para usar.

```bash
docker compose up -d
```

---

## Setup local

```bash
# 1. Clonar e instalar deps
git clone git@github.com:JLosada-Dev/backend-guayacanes.git
cd backend-guayacanes
uv sync                                            # crea .venv e instala todo

# 2. Variables de entorno
cp .env.example .env                               # ajustar contraseñas/hosts si hace falta

# 3. Base de datos (si no usas docker compose)
createdb guyacanes_dev
psql guyacanes_dev -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# 4. Migraciones
uv run python manage.py migrate

# 5. Datos (catálogos + geodatos + usuarios staff)
make data                                          # ver detalle más abajo
uv run python manage.py seed_staff                 # 3 veedores + 2 coordinadores

# 6. Servidor
uv run python manage.py runserver 0.0.0.0:8000
```

API disponible en `http://localhost:8000/api/v1/`. Swagger UI en `http://localhost:8000/api/docs/`.

---

## Variables de entorno

Copia `.env.example` a `.env` y completa:

| Variable                | Requerida (prod) | Default                                       | Descripción                                  |
| ----------------------- | ---------------- | --------------------------------------------- | -------------------------------------------- |
| `SECRET_KEY`            | Sí               | (insegura)                                    | Clave de firma Django                        |
| `DEBUG`                 | No               | `False`                                       | Solo true en desarrollo                      |
| `ALLOWED_HOSTS`         | Sí               | —                                             | CSV de hosts permitidos                      |
| `DB_NAME`               | Sí               | `guyacanes_dev`                               | Nombre BD                                    |
| `DB_USER`               | Sí               | `guyacanes`                                   | Usuario BD                                   |
| `DB_PASSWORD`           | Sí               | `guyacanes`                                   | Password BD                                  |
| `DB_HOST`               | No               | `localhost`                                   | Host BD                                      |
| `DB_PORT`               | No               | `5432`                                        | Puerto BD                                    |
| `CORS_ALLOWED_ORIGINS`  | No               | —                                             | CSV de orígenes CORS                         |
| `GDAL_LIBRARY_PATH`     | No (solo macOS)  | `/opt/homebrew/opt/gdal/lib/libgdal.dylib`    | Solo si tu Homebrew está en otra ruta        |
| `GEOS_LIBRARY_PATH`     | No (solo macOS)  | `/opt/homebrew/opt/geos/lib/libgeos_c.dylib`  | Igual que GDAL                               |

---

## Base de datos y PostGIS

El proyecto requiere **PostgreSQL 16 con la extensión PostGIS 3.4 habilitada**. SRID estándar: **EPSG:4326 (WGS84)** para almacenamiento; se reproyecta a **EPSG:3116 (Colombia Oeste)** cuando hay que calcular áreas en metros.

```sql
CREATE DATABASE guyacanes_dev;
\c guyacanes_dev
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_raster;   -- opcional, ya viene con la imagen Docker
```

El backend nunca habla con la BD sin pasar por GeoDjango (`django.contrib.gis.db.backends.postgis`).

---

## Datos geoespaciales (shapefiles y fixtures)

### Organización del directorio de shapes

Todos los shapefiles del POT de Popayán viven bajo:

```
guayacanes_docs/SHAPESPOT/SHAPES POT/
├── U1_POPAYAN BASE/
│   ├── MANZANAS.shp           # manzanas urbanas
│   ├── PERIMETRO.shp          # perímetro urbano
│   ├── RIO.shp                # hidrografía
│   └── SEPARADOR.shp          # separadores viales (cargados en PublicSpace)
├── U2_COMUNAS/
│   └── U2_COMUNAS.shp         # 9 comunas urbanas
├── U18_VIAL/
│   └── U18_VIAL.shp           # 3,800 segmentos viales (rutas de barrido)
├── U-19 ESPACIO PUBLICO/
│   ├── U19_ESPACIO_PUBLICO1.shp   # espacio público (2)
│   ├── U19_ESPACIO_PUBLICO2.shp   # parques urbanos (11)
│   ├── U19_ESPACIO_PUBLICO3.shp   # nodos con NOMBRE (96)
│   └── U19_ESPACIO_PUBLICO5.shp   # corredores verdes / rondas de río (72)
├── U16_DESLIZAMIENTOS/        # análisis de riesgo (Fase 2, no cargado)
└── U17_INUNDACIONES/          # análisis de riesgo (Fase 2, no cargado)
```

**Convención:** los shapes son archivos grandes y no se versionan en `git`. Cuando clones el repo, debes copiar/descargar el árbol `guayacanes_docs/SHAPESPOT/SHAPES POT/` desde el respaldo del proyecto.

Todos los shapefiles fuente vienen en **PCS_CAUCA_POPAYAN** y son reproyectados automáticamente a EPSG:4326 al cargar.

### Tipos de fuentes que el sistema consume

| Tipo            | Formato | Origen                            | Comando que lo carga                  |
| --------------- | ------- | --------------------------------- | ------------------------------------- |
| Polígonos       | `.shp`  | POT Popayán                       | `load_communes`, `load_public_spaces` |
| LineStrings     | `.shp`  | POT Popayán                       | `load_sweeping`                       |
| Catálogos       | `.json` | Fixtures Django                   | `loaddata`                            |
| Cronogramas     | `.pdf`  | Boletines Urbaser                 | `load_cutting_schedule`               |

### Fixtures JSON (en `apps/*/fixtures/`)

| Fixture                                                            | Modelo                | Contenido                                        |
| ------------------------------------------------------------------ | --------------------- | ------------------------------------------------ |
| `apps/core/fixtures/sections.json`                                 | `Section`             | 5 secciones (urbaser, vivienda, cultura, …)      |
| `apps/infra_servicios_publicos_urbaser/fixtures/services.json`     | `Service`             | 5 servicios de Urbaser                           |
| `apps/infra_servicios_publicos_urbaser/fixtures/aspects.json`      | `Aspect`              | 11 aspectos (7 barrido + 4 zonas verdes)         |
| `apps/infra_servicios_publicos_urbaser/fixtures/service_content.json` | `ServiceContent`   | Descripciones, frecuencias, iconos               |
| `apps/infra_servicios_publicos_urbaser/fixtures/aspect_content.json`  | `AspectContent`    | Guías ciudadanas, tiempos de respuesta           |

### Orden recomendado de carga

```bash
# 1. Catálogos (cero dependencias)
uv run python manage.py loaddata apps/core/fixtures/sections.json
uv run python manage.py loaddata apps/infra_servicios_publicos_urbaser/fixtures/services.json
uv run python manage.py loaddata apps/infra_servicios_publicos_urbaser/fixtures/aspects.json
uv run python manage.py loaddata apps/infra_servicios_publicos_urbaser/fixtures/service_content.json
uv run python manage.py loaddata apps/infra_servicios_publicos_urbaser/fixtures/aspect_content.json

# 2. Geodatos transversales
uv run python manage.py load_communes
uv run python manage.py load_neighborhoods   # (hard-coded, sin shapefile)
uv run python manage.py load_public_spaces

# 3. Operaciones Urbaser (dependen de PublicSpace y Section/Service)
uv run python manage.py load_sweeping
uv run python manage.py load_green_zone_assignments
uv run python manage.py load_cutting_schedule   # opcional, requiere PDF

# 4. Usuarios y demo
uv run python manage.py seed_staff
uv run python manage.py seed_complaints         # opcional, datos de prueba
```

`make data` automatiza los pasos 1–3.

---

## Management commands

| App                                       | Comando                          | Descripción                                                                                |
| ----------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------ |
| `accounts`                                | `seed_staff`                     | Crea 3 veedores + 2 coordinadores con passwords conocidas. Idempotente.                    |
| `core`                                    | `load_communes`                  | Carga las 9 comunas desde `U2_COMUNAS.shp`. Reproyecta a EPSG:4326.                        |
| `core`                                    | `load_neighborhoods`             | Carga ~370 barrios (datos en código, sin shapefile).                                       |
| `geodata`                                 | `load_public_spaces`             | Carga ~313 polígonos desde los 5 shapefiles de espacio público + separadores viales.       |
| `infra_servicios_publicos_urbaser`        | `load_sweeping`                  | Crea 8 macrorutas + ~3,800 microrutas de barrido desde `U18_VIAL.shp`.                     |
| `infra_servicios_publicos_urbaser`        | `load_green_zone_assignments`    | Asigna `GreenZoneAssignment` por cada `PublicSpace` activo (responsabilidad Urbaser).      |
| `infra_servicios_publicos_urbaser`        | `load_cutting_schedule`          | Parsea PDF mensual de Urbaser (`cronograma-de-cesped-*.pdf`) y crea `CuttingSchedule`s.    |
| `veeduria`                                | `seed_complaints`                | Crea ~15 denuncias de prueba que disparan alertas SLA (para demos).                        |

Todos aceptan `--clear` para borrar antes de cargar. Detalle completo:

```bash
uv run python manage.py <comando> --help
```

---

## Estructura de apps

```
apps/
├── core/            # Sections, Communes, Neighborhoods, ServiceProvider registry
├── geodata/         # PublicSpace (polígonos POT)
├── accounts/        # Auth JWT, roles (Groups), seed_staff
├── veeduria/        # Complaint, Evidence, ComplaintStatusEvent, SLAAlert, MetricByCommune, statistics
├── infra_servicios_publicos_urbaser/                    # Servicio público "Urbaser" (barrido, zonas verdes)
└── infra_servicios_publicos_urbaser_facturacion/        # Facturación Urbaser (Fase 2, no activa)
```

**Patrón "una app por servicio público + core transversal"**: cada empresa/sección de servicio público tiene su propia app Django (`infra_servicios_publicos_<nombre>`) que registra dinámicamente sus servicios mediante el **ServiceProvider Protocol**.

### ServiceProvider Protocol

Definido en `apps/core/registry.py`:

```python
class ServiceProvider(Protocol):
    section_slug: str
    def get_services(self) -> list[ServiceInfo]: ...
    def get_aspects(self, service_slug: str) -> list[AspectInfo]: ...
```

Cada app de servicio registra su provider en su `AppConfig.ready()`:

```python
# apps/infra_servicios_publicos_urbaser/apps.py
def ready(self):
    from .registry import UrbaserServiceProvider
    from apps.core.registry import register
    register(UrbaserServiceProvider())
```

Los endpoints `/core/services/` y `/core/aspects/` iteran todos los providers registrados — añadir un nuevo servicio público (vivienda, cultura, etc.) es solo crear una nueva app que registre su `ServiceProvider`.

Más detalle en [`docs/refactor/SECTION-REGISTRY.md`](docs/refactor/SECTION-REGISTRY.md) y [`docs/refactor/REGISTRY-PATTERN.md`](docs/refactor/REGISTRY-PATTERN.md).

---

## Modelos GeoDjango

| Modelo                  | App                | Geom                 | SRID  | Descripción                                                   |
| ----------------------- | ------------------ | -------------------- | ----- | ------------------------------------------------------------- |
| `Commune`               | core               | `PolygonField`       | 4326  | 9 comunas urbanas de Popayán                                  |
| `Neighborhood`          | core               | `MultiPolygonField`  | 4326  | Barrios por comuna; centroide se usa como fallback de location |
| `PublicSpace`           | geodata            | `MultiPolygonField`  | 4326  | ~313 polígonos POT (parques, separadores, rondas de río)      |
| `SweepingMacroRoute`    | urbaser            | `MultiPolygonField`  | 4326  | 8 áreas de cobertura de barrido (B211/B212/…)                 |
| `SweepingMicroRoute`    | urbaser            | `LineStringField`    | 4326  | ~3,800 segmentos viales individuales                          |
| `Complaint`             | veeduria           | `PointField`         | 4326  | Ubicación de la denuncia (cascada: GPS → manual → centroide)  |

**Regla crítica de `Complaint.location`:** nunca puede ser NULL. El serializer aplica cascada GPS → pin manual → centroide de comuna; si nada está disponible rechaza el POST con 400.

Modelos sin geometría: `Section`, `Service`, `Aspect`, `ServiceContent`, `AspectContent`, `GreenZoneAssignment`, `CuttingSchedule`, `Intervention`, `Evidence`, `SLAAlert`, `MetricByCommune`, `ComplaintStatusEvent`.

---

## API REST

Base URL: `http://localhost:8000/api/v1/`

### Documentación interactiva

| URL              | Herramienta              |
| ---------------- | ------------------------ |
| `/api/docs/`     | Swagger UI (prueba)      |
| `/api/redoc/`    | ReDoc (referencia)       |
| `/api/schema/`   | OpenAPI 3.0 YAML         |

### Endpoints principales

#### Auth `/api/v1/auth/`

| Método | Endpoint     | Descripción                                                |
| ------ | ------------ | ---------------------------------------------------------- |
| POST   | `/login/`    | Devuelve `{access, refresh, user}` para staff de alcaldía  |
| POST   | `/refresh/`  | Renueva el access token (rotación de refresh activa)       |
| GET    | `/me/`       | Perfil del usuario autenticado (incluye `role` y `groups`) |

#### Core `/api/v1/core/`

| Método | Endpoint                              | Descripción                                  |
| ------ | ------------------------------------- | -------------------------------------------- |
| GET    | `/sections/`                          | Lista de secciones activas                   |
| GET    | `/services/?section=<slug>`           | Servicios agregados de todos los providers   |
| GET    | `/aspects/?service=<slug>`            | Aspectos de un servicio                      |
| GET    | `/communes/`                          | 9 comunas (sin geometría)                    |
| GET    | `/communes/geojson/`                  | Comunas como GeoJSON FeatureCollection       |
| GET    | `/neighborhoods/?commune_id=<id>`     | Barrios de una comuna                        |

#### Veeduría `/api/v1/veeduria/`

| Método | Endpoint                                  | Descripción                                                |
| ------ | ----------------------------------------- | ---------------------------------------------------------- |
| POST   | `/complaints/`                            | Crear denuncia (anónimo, sin auth)                         |
| GET    | `/complaints/`                            | Listar denuncias con filtros (status, severity, …)         |
| GET    | `/complaints/<id>/`                       | Detalle (incluye `status_events` y `evidence`)             |
| PATCH  | `/complaints/<id>/`                       | **Staff:** caracterizar (servicio, aspecto, ubicación…)    |
| POST   | `/complaints/<id>/transition/`            | **Staff:** aplicar transición de estado validada por rol   |
| GET    | `/complaints/<id>/events/`                | Timeline de cambios de estado                              |
| GET    | `/complaints/geojson/`                    | Denuncias como GeoJSON (para mapa)                         |
| POST   | `/evidence/`                              | Subir foto (multipart; máx 2 por denuncia, 5 MB c/u)       |
| GET    | `/alerts/`                                | Alertas SLA generadas automáticamente                      |
| GET    | `/metrics/`                               | Métricas por comuna (heatmap)                              |
| GET    | `/statistics/`                            | **Staff:** KPIs agregados, distribuciones y rankings       |

#### Urbaser `/api/v1/urbaser/`

| Método | Endpoint                       | Descripción                          |
| ------ | ------------------------------ | ------------------------------------ |
| GET    | `/sweeping-macroroutes/`       | 8 macrorutas con horarios            |
| GET    | `/sweeping-microroutes/`       | ~3,800 segmentos de barrido          |
| GET    | `/green-zone-assignments/`     | Asignaciones de zonas verdes         |

---

## Autenticación y roles

Sistema de **dos universos**:

- **Ciudadano** (`POST /veeduria/complaints/`): completamente anónimo, sin auth.
- **Staff alcaldía** (`/alcaldia/*` del frontend): login con JWT.

### Roles (Django Groups)

Definidos en [`apps/accounts/roles.py`](apps/accounts/roles.py):

| Rol           | Group name     | Puede                                                                                  |
| ------------- | -------------- | -------------------------------------------------------------------------------------- |
| Veedor        | `veedor`       | Ver denuncias, caracterizar, mover a `triaged`/`in_field`/`escalated`, subir evidencia |
| Coordinador   | `coordinador`  | Todo lo del veedor + `resolved`/`rejected` + reabrir denuncias cerradas                |

Los superusers tienen privilegios de coordinador automáticamente.

### Seed de usuarios para desarrollo

```bash
uv run python manage.py seed_staff
```

Crea:

| Username  | Password    | Rol          | Nombre               |
| --------- | ----------- | ------------ | -------------------- |
| veedor1   | veedor123   | veedor       | Carolina Rivera      |
| veedor2   | veedor123   | veedor       | Andrés Mosquera      |
| veedor3   | veedor123   | veedor       | Sara Caicedo         |
| coord1    | coord123    | coordinador  | Mauricio Vásquez     |
| coord2    | coord123    | coordinador  | Diana Quintero       |

> **Importante:** estas credenciales son para **desarrollo** únicamente. En producción rota los passwords inmediatamente tras el primer despliegue.

### Crear un usuario manualmente

```bash
uv run python manage.py createsuperuser
uv run python manage.py shell
```
```python
from django.contrib.auth.models import Group, User
u = User.objects.get(username='nuevo')
u.groups.add(Group.objects.get(name='coordinador'))
```

---

## Flujo de estado de una denuncia

Pipeline operativo de 6 estados (matriz en [`apps/veeduria/transitions.py`](apps/veeduria/transitions.py)):

```
received  →  triaged  →  in_field  →  escalated  →  resolved
                                                 ↘  rejected
```

| Estado       | Significado                                                      | Quién                |
| ------------ | ---------------------------------------------------------------- | -------------------- |
| `received`   | Inicial automático al crear (ciudadano)                          | sistema              |
| `triaged`    | Veedor revisó y clasificó                                        | veedor / coordinador |
| `in_field`   | Veedor desplazado a inspeccionar físicamente                     | veedor / coordinador |
| `escalated`  | Remitido al operador/entidad responsable                         | veedor / coordinador |
| `resolved`   | Problema solucionado y verificado                                | **solo coordinador** |
| `rejected`   | Duplicada, improcedente o sin fundamento                         | **solo coordinador** |

Cada transición se registra en `ComplaintStatusEvent` (audit log) con autor, rol, nota opcional y timestamp.

---

## Tests

```bash
uv run pytest                        # todo
uv run pytest apps/veeduria/tests/   # por app
uv run pytest -k transitions         # por keyword
uv run pytest --reuse-db             # reusar DB (default por config)
```

Estructura:

```
apps/core/tests/
apps/veeduria/tests/test_serializers.py
apps/veeduria/tests/test_signals.py
apps/infra_servicios_publicos_urbaser/tests/test_sla_handlers.py
conftest.py
```

---

## Admin Django

```
http://localhost:8000/admin/
```

Acceso con superuser (`createsuperuser`). Permite gestionar manualmente todos los modelos. Ver [`docs/admin-guide.md`](docs/admin-guide.md) para detalle.

---

## Documentación adicional

| Archivo                                                       | Contenido                                                |
| ------------------------------------------------------------- | -------------------------------------------------------- |
| [`docs/CONTEXT_GUYACANES.md`](docs/CONTEXT_GUYACANES.md)      | Arquitectura completa y decisiones de diseño             |
| [`docs/geodatos.md`](docs/geodatos.md)                        | Inventario detallado de shapefiles y datos POT           |
| [`docs/entorno-python-gdal.md`](docs/entorno-python-gdal.md)  | Setup de GDAL/GEOS por sistema operativo                 |
| [`docs/admin-guide.md`](docs/admin-guide.md)                  | Cómo usar el panel admin de Django                       |
| [`docs/demo-guide.md`](docs/demo-guide.md)                    | Pasos para levantar una demo desde cero                  |
| [`docs/estado-actual.md`](docs/estado-actual.md)              | Estado actual del proyecto y próximos pasos              |
| [`docs/refactor/SECTION-REGISTRY.md`](docs/refactor/SECTION-REGISTRY.md) | Diseño del registry de servicios (V2.1)        |
| [`docs/refactor/REGISTRY-PATTERN.md`](docs/refactor/REGISTRY-PATTERN.md) | Patrón ServiceProvider Protocol                |
| [`docs/refactor/EVENTS.md`](docs/refactor/EVENTS.md)          | Contrato del evento `complaint_created`                  |
| [`docs/api/`](docs/api/)                                      | Colecciones Bruno y Postman para probar la API           |

---

## Makefile

```bash
make up         # docker compose up -d
make down       # docker compose down
make dev        # up + esperar Postgres + runserver
make migrate    # migrate
make data       # fixtures + load_communes + load_neighborhoods + load_public_spaces + load_sweeping + load_green_zone_assignments
make seed       # seed_complaints
make demo       # reset + data + seed
make reset      # flush DB + migrate
make logs       # docker compose logs -f
make shell      # python manage.py shell
```
