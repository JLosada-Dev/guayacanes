# Plan de migración V1 → V2

**Fecha:** 2026-04-28
**Rama:** `refactor/arquitectura-multiapp` (backend y frontend)
**Estrategia:** prototipo — drop & recreate. Sin `SeparateDatabaseAndState`.

---

## Documentos relacionados

- `ARQUITECTURA-V2.md` — diseño objetivo
- `MAPA-MODELOS.md` — qué se mueve a dónde
- `REGISTRY-PATTERN.md` — patrón de handlers SLA

---

## Pre-flight

1. ✅ Rama `refactor/arquitectura-multiapp` creada en backend y frontend.
2. ✅ Documentación de datos verificada: `geodatos.md`, `rutas-y-servicios.md`, `RUTAS-URBASER-2024.md`, cronogramas zonas verdes 2026 (Ene–Dic), `reporte_barrios_popayan.md`. Cubre todo lo necesario para repoblar.
3. ⏳ Bajar contenedores actuales y limpiar BD:
   ```bash
   docker compose down -v
   docker compose up -d
   ```

---

## Fase 1 — Backend: estructura nueva

### 1.1 Crear apps vacías

```bash
cd backend-guayacanes
mkdir -p apps/geodata apps/veeduria
touch apps/geodata/__init__.py apps/veeduria/__init__.py
```

Crear `apps.py` en cada una con `AppConfig` y `default_auto_field = 'django.db.models.BigAutoField'`.

### 1.2 Borrar lo que sale

```bash
rm -rf apps/infra_servicios_publicos_urbaser_facturacion
```

Borrar carpetas de migraciones (manteniendo `__init__.py`):

```bash
find apps -path '*/migrations/*' -name '*.py' ! -name '__init__.py' -delete
find apps -path '*/migrations/__pycache__*' -delete
```

Mover fixtures:
```bash
mkdir -p apps/core/fixtures apps/infra_servicios_publicos_urbaser/fixtures
git mv fixtures/core_services.json        apps/core/fixtures/services.json
git mv fixtures/core_aspects.json         apps/core/fixtures/aspects.json
git mv fixtures/core_service_content.json apps/infra_servicios_publicos_urbaser/fixtures/service_content.json
git mv fixtures/core_aspect_content.json  apps/infra_servicios_publicos_urbaser/fixtures/aspect_content.json
rmdir fixtures
```

Actualizar el contenido de los fixtures de urbaser para usar el nuevo modelo `urbaser.ServiceContent` / `urbaser.AspectContent` (cambiar `model: "core.servicecontent"` → `"infra_servicios_publicos_urbaser.servicecontent"`).

### 1.3 Actualizar `INSTALLED_APPS`

`config/settings/base.py`:

```python
INSTALLED_APPS = [
    # Django y libs (sin cambios)
    ...
    # Local
    'apps.core',
    'apps.geodata',
    'apps.veeduria',
    'apps.infra_servicios_publicos_urbaser',
]
```

Eliminar la línea de `_facturacion`.

### 1.4 Modelos por app

Crear/refactorizar archivos según el `MAPA-MODELOS.md`:

**`apps/core/models/`** (limpieza):
- `geography.py` igual.
- `catalog.py` queda solo con `Service` y `Aspect`. Se eliminan `ServiceContent` y `AspectContent`.

**`apps/geodata/models/`** (nuevo):
- `__init__.py` exporta `PublicSpace`.
- `public_space.py` con el modelo descrito en `ARQUITECTURA-V2.md §3.2`.

**`apps/veeduria/models/`** (nuevo):
- `__init__.py` exporta `Complaint`, `Evidence`, `SLAAlert`, `MetricByCommune`.
- `complaint.py`: `Complaint`, `Evidence`. Tablas `vee_complaint`, `vee_evidence`.
- `alert.py`: `SLAAlert` con `route_type=CharField(50)` (sin choices), `route_label`, `extra_int` y `extra_data=JSONField`.
- `metric.py`: `MetricByCommune` (renombrado de `CommuneMetric`).

**`apps/veeduria/signals.py`** (nuevo):
- Define `complaint_created = Signal()`.
- `post_save` receiver de `Complaint` que emite `complaint_created`.

**`apps/veeduria/metrics.py`** (nuevo):
- `recalculate_for(commune_id, service_slug)` — lógica idéntica a la `_recalculate_commune_metric` de V1.

**`apps/infra_servicios_publicos_urbaser/models/`** (refactor):
- `operaciones.py`:
  - `SweepingMacroRoute`, `SweepingMicroRoute` igual.
  - Reemplazar `GreenZone` por `GreenZoneAssignment` (apunta por soft FK a `geodata.PublicSpace`).
  - `CuttingSchedule` y `Intervention` apuntan a `GreenZoneAssignment`.
- `contenido.py` (nuevo): `ServiceContent`, `AspectContent`. Tablas `urbaser_service_content`, `urbaser_aspect_content`. FK dura a `core.Service` / `core.Aspect`.
- Eliminar `veeduria.py` y `auditoria.py` de la app urbaser.

**`apps/infra_servicios_publicos_urbaser/apps.py`** (modificar):
- En `ready()`: conectar `sla_handlers.handle_complaint` a `veeduria.signals.complaint_created` con `dispatch_uid='urbaser.handle_complaint'`.

**`apps/infra_servicios_publicos_urbaser/sla_handlers.py`** (nuevo):
- Reescribir el contenido de `receivers.py` V1 como el patrón descrito en `REGISTRY-PATTERN.md §3`.
- Usa `geodata.PublicSpace` + `urbaser.GreenZoneAssignment` para el cruce de zonas verdes.
- Crea alertas en `veeduria.SLAAlert` (no en urbaser).
- Llama `veeduria.metrics.recalculate_for(...)` al final.

Eliminar `apps/infra_servicios_publicos_urbaser/signals.py` y `receivers.py` V1.

### 1.5 Serializers, views, urls

**`apps/core/`** (limpieza):
- `urls.py` y `views/serializers` quedan: `services_list`, `aspects_list`, `communes_list`, `communes_geojson`. Las respuestas siguen incluyendo `content` populado vía `select_related`, pero ahora `content` viene del lado urbaser (acceso vía `service.urbaser_content` / `aspect.urbaser_content` con `related_name`).

**`apps/geodata/urls.py`** (nuevo, mínimo):
- `GET /geodata/public-spaces/` lista paginada (opcional, para debugging admin).
- `GET /geodata/public-spaces/geojson/` (opcional, para overlay en frontend si se quiere).

**`apps/veeduria/urls.py`** (nuevo):
```
POST /veeduria/complaints/
GET  /veeduria/complaints/
GET  /veeduria/complaints/{id}/
GET  /veeduria/complaints/geojson/
POST /veeduria/evidence/
GET  /veeduria/alerts/
GET  /veeduria/alerts/{id}/
GET  /veeduria/metrics/
GET  /veeduria/metrics/{id}/
```

**`apps/infra_servicios_publicos_urbaser/urls.py`** (refactor):
```
GET /urbaser/sweeping-macroroutes/
GET /urbaser/sweeping-microroutes/
GET /urbaser/green-zone-assignments/
GET /urbaser/cutting-schedules/        (opcional)
GET /urbaser/interventions/            (opcional)
```

**`config/urls.py`** (refactor):
- Registrar los 4 prefijos: `core/`, `geodata/`, `veeduria/`, `urbaser/`.

### 1.6 Admin

Reubicar registros de admin a la app correspondiente:
- `Complaint`, `Evidence`, `SLAAlert`, `MetricByCommune` → `apps/veeduria/admin.py`.
- `PublicSpace` → `apps/geodata/admin.py`.
- `SweepingMacroRoute`, `SweepingMicroRoute`, `GreenZoneAssignment`, `CuttingSchedule`, `Intervention`, `ServiceContent`, `AspectContent` → `apps/infra_servicios_publicos_urbaser/admin.py`.

### 1.7 Management commands

Reubicar y dividir:
- `apps/core/management/commands/` (sin cambios): `load_communes`, `load_neighborhoods`.
- `apps/geodata/management/commands/load_public_spaces.py` (nuevo) — carga 313 polígonos de los 5 shapefiles a `geodata_public_space`.
- `apps/infra_servicios_publicos_urbaser/management/commands/`:
  - `load_sweeping` (sin cambios).
  - `load_green_zone_assignments.py` (nuevo) — crea un assignment por cada PublicSpace cargado, con `cycle_days=11`.
  - `load_cutting_schedule.py` (apunta a `GreenZoneAssignment`).
- `apps/veeduria/management/commands/seed_complaints.py` (movido).

### 1.8 Generar migraciones desde cero

```bash
uv run python manage.py makemigrations core geodata veeduria infra_servicios_publicos_urbaser
uv run python manage.py migrate
```

### 1.9 `Makefile`

Actualizar el target `data`:
```makefile
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
```

`make demo` mantiene su definición pero apunta al nuevo `data` y al nuevo `seed_complaints`.

---

## Fase 2 — Frontend

### 2.1 Renombrar archivo de API

```bash
cd frontend-guayacanes
git mv src/api/urbaser.ts src/api/veeduria.ts
```

### 2.2 Actualizar paths en `src/api/veeduria.ts`

`/urbaser/complaints/` → `/veeduria/complaints/`
`/urbaser/evidence/` → `/veeduria/evidence/`
`/urbaser/alerts/` → `/veeduria/alerts/`
`/urbaser/metrics/` → `/veeduria/metrics/`
`/urbaser/complaints/geojson/` → `/veeduria/complaints/geojson/`

### 2.3 Actualizar imports

Buscar `from '../api/urbaser'` y reemplazar por `from '../api/veeduria'` en:
- `pages/CitizenPortal.tsx`
- `pages/SupervisorDashboard.tsx`
- `store/complaintStore.ts`
- `store/dashboardStore.ts`
- componentes que importen funciones de urbaser

### 2.4 (Opcional) crear `src/api/urbaser.ts` mínimo

Si más adelante se quiere mostrar rutas/zonas en UI. Por ahora omitir.

### 2.5 Tipos

`src/types/index.ts` no cambia — los campos de `Complaint`, `SLAAlert`, `CommuneMetric` se mantienen idénticos. El renombre de `CommuneMetric` → `MetricByCommune` queda solo en backend (la respuesta API tiene los mismos campos).

---

## Fase 3 — Validación

### 3.1 Setup limpio

```bash
cd backend-guayacanes
docker compose down -v
docker compose up -d
make demo
```

Esperado:
- 9 comunas cargadas (`core_commune`).
- 313 espacios públicos (`geodata_public_space`).
- 8 macrorutas + 1,731 microrutas (`urbaser_sweeping_macroroute`, `urbaser_sweeping_microroute`).
- 313 assignments (`urbaser_green_zone_assignment`).
- 31 schedules (`urbaser_cutting_schedule`).
- 5 servicios + 11 aspectos (`core_service`, `core_aspect`).
- Contenidos editoriales (`urbaser_service_content`, `urbaser_aspect_content`).
- 14 denuncias seed (`vee_complaint`).
- 27 alertas SLA generadas vía signal (`vee_sla_alert`).
- 5 métricas (`vee_metric_by_commune`).

### 3.2 Smoke tests manuales

1. `curl http://localhost:8000/api/v1/core/services/` → 5 servicios con `content` populado.
2. `curl http://localhost:8000/api/v1/veeduria/complaints/` → 14 denuncias.
3. `curl http://localhost:8000/api/v1/veeduria/alerts/?violation=true` → 24 violations.
4. `curl http://localhost:8000/api/v1/veeduria/metrics/?service_slug=sweeping-cleaning` → métricas por comuna.
5. Frontend `pnpm dev` → wizard ciudadano crea denuncia → SupervisorDashboard la muestra.

### 3.3 Tests automáticos (mínimos)

Crear `apps/veeduria/tests/test_signals.py`:
- `test_complaint_created_emits_signal` — POST denuncia, verifica handler conectado.
- `test_handler_filters_by_slug` — denuncia con slug desconocido no genera alertas.

Crear `apps/infra_servicios_publicos_urbaser/tests/test_sla_handlers.py`:
- `test_sweeping_handler_creates_alert` — denuncia cerca de microruta crea alerta.
- `test_green_zones_handler_creates_alert` — denuncia cerca de zona verde crea alerta.
- `test_metric_recalculated_after_alert` — `MetricByCommune` actualizada.

---

## Fase 4 — Cierre

1. Actualizar `README.md` (backend y frontend) con el nuevo árbol de apps y endpoints.
2. Actualizar `docs/CONTEXT_GUYACANES.md` con la arquitectura V2.
3. Actualizar `docs/api/README.md` con los nuevos paths.
4. Actualizar `docs/estado-actual.md`.
5. Actualizar Bruno collection (`docs/api/guyacanes.bruno/`) con los paths nuevos.
6. Commit de la rama y PR.

---

## Orden de ejecución sugerido (commits granulares)

| # | Commit | Contenido |
|---|---|---|
| 1 | `docs: refactor architecture V2 (planning)` | los 4 .md de `docs/refactor/` |
| 2 | `refactor: scaffold geodata and veeduria apps` | apps vacías + INSTALLED_APPS |
| 3 | `refactor: remove facturacion app and old migrations` | borrado de archivos obsoletos |
| 4 | `refactor: move ServiceContent/AspectContent to urbaser` | modelos + fixtures + serializers |
| 5 | `refactor: extract PublicSpace to geodata, split GreenZone` | nuevo modelo geodata + GreenZoneAssignment |
| 6 | `refactor: move Complaint/Evidence/SLAAlert/MetricByCommune to veeduria` | modelos + signal pública + métricas |
| 7 | `refactor: register Urbaser SLA handlers via complaint_created` | sla_handlers.py + apps.py ready() |
| 8 | `refactor: rename API paths /urbaser/complaints/ → /veeduria/complaints/` | urls.py + views.py |
| 9 | `refactor: split load_green_zones into load_public_spaces and load_green_zone_assignments` | management commands |
| 10 | `refactor: regenerate migrations from scratch` | makemigrations + migrate |
| 11 | `refactor(frontend): rename urbaser.ts → veeduria.ts and update API paths` | frontend |
| 12 | `test: add veeduria signal and urbaser SLA handler tests` | tests mínimos |
| 13 | `docs: update README, CONTEXT, api/README to V2` | docs finales |

---

## Riesgos y cómo mitigarlos

| Riesgo | Mitigación |
|---|---|
| Olvido de un import circular entre apps | Test: `python manage.py check` después de cada commit |
| Fixtures con label de modelo incorrecto | Renombrar app label en el JSON antes de loaddata |
| GeoDjango no encuentra el shapefile reproyectado | Mantener `load_public_spaces` con la misma lógica de `load_green_zones` |
| Frontend rompe al apuntar a paths nuevos antes del deploy backend | Hacer el cambio de paths en backend primero, frontend después |
| Doble registro del handler en tests | `dispatch_uid` único por handler |
