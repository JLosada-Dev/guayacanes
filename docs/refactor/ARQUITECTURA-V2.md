# Arquitectura V2 — Multi-app de la Alcaldía

**Fecha:** 2026-04-28
**Rama:** `refactor/arquitectura-multiapp`
**Estado:** propuesta aprobada — pendiente implementación

---

## 1. Motivación

La V1 acopló todo lo de Urbaser dentro de una sola app (`infra_servicios_publicos_urbaser`) y contaminó `core` con contenido editorial específico del PPS 2024 (frecuencias, "ciclo 11 días", etc.). Cuando lleguen otros servicios públicos (vivienda, acueducto, estratificación), tendrían que:

- Duplicar el modelo `Complaint` y toda la lógica de evidencias.
- Duplicar la signal `complaint_created` y el receiver de auditoría.
- Reescribir la mecánica de métricas por comuna.
- Pelear con un `core` que ya tiene contenido de Urbaser hard-coded.

V2 separa **estructura genérica** (Alcaldía) de **lógica operativa** (servicio) y extrae la veeduría como capa transversal con un patrón de registro de handlers SLA.

---

## 2. Apps resultantes

```
guyacanes/
  apps/
    core/                                   # catálogo administrativo Alcaldía
    geodata/                                # capas POT reutilizables (geometría)
    veeduria/                               # denuncias + evidencias + alertas + métricas
    infra_servicios_publicos_urbaser/       # operaciones específicas Urbaser
```

App `infra_servicios_publicos_urbaser_facturacion` se elimina. Cuando llegue Fase 2 se crea limpia.

---

## 3. Responsabilidades por app

### 3.1 `core/` — catálogo administrativo

Toda la Alcaldía lee de aquí. Nunca importa de otras apps.

| Modelo | Tabla | Contenido |
|---|---|---|
| `Commune` | `core_commune` | 9 comunas urbanas Popayán + geometría |
| `Neighborhood` | `core_neighborhood` | Barrios + geometría (cuando esté) |
| `Service` | `core_service` | Servicios públicos auditables (estructura, sin contenido editorial) |
| `Aspect` | `core_aspect` | Subcategorías de queja por servicio (estructura) |

**Sale de core:** `ServiceContent` y `AspectContent` (se mueven a urbaser).

### 3.2 `geodata/` — capas POT

Capas espaciales del POT de Popayán reutilizables por cualquier app de servicio. Cargadas desde shapefiles `guayacanes_docs/SHAPESPOT/SHAPES POT/`.

| Modelo | Tabla | Fuente | Uso |
|---|---|---|---|
| `PublicSpace` | `geodata_public_space` | U-19 ESPACIO PUBLICO (1,2,3,5) + SEPARADOR | parques, separadores, corredores, nodos |
| `Road` (opcional) | `geodata_road` | U18_VIAL | vial — reservado por si vivienda/POT lo necesita |

`PublicSpace` campos:
```
external_id      IntegerField UNIQUE     # ID compuesto por capa fuente
name             CharField(300)
space_type       CharField(20)           # park / road_divider / corridor / node / sports / other
area_sqm         DecimalField null
source_layer     CharField(50)           # 'U19_EP1', 'U19_EP2', 'SEPARADOR', etc.
neighborhood_id  IntegerField null       # soft FK a core_neighborhood
geom             MultiPolygonField(4326)
```

Urbaser referencia `PublicSpace` por soft FK en `GreenZoneAssignment`. Otra app puede referenciar el mismo polígono con su propia lógica sin tocar nada.

### 3.3 `veeduria/` — denuncias transversales

Plataforma de quejas ciudadanas que sirve a todos los servicios. No conoce la lógica de SLA — la delega a handlers registrados.

| Modelo | Tabla | Notas |
|---|---|---|
| `Complaint` | `vee_complaint` | Soft FKs a `core_service`/`core_aspect` con snapshots de texto |
| `Evidence` | `vee_evidence` | Fotos en `media_local/complaints/YYYY/MM/` |
| `SLAAlert` | `vee_sla_alert` | Alerta genérica (`service_slug`, `route_type`, `route_id`) |
| `MetricByCommune` | `vee_metric_by_commune` | Caché agregado por `(commune, service_slug, period)` |

Signal pública: `veeduria.signals.complaint_created` (cualquier app de servicio se conecta).

`SLAAlert.route_type` queda como `CharField` libre (no choices) para que cada servicio aporte sus propios tipos sin migración en veeduría.

### 3.4 `infra_servicios_publicos_urbaser/` — operaciones Urbaser

Solo lo específico del contrato PPS 2024.

| Modelo | Tabla |
|---|---|
| `SweepingMacroRoute` | `urbaser_sweeping_macroroute` |
| `SweepingMicroRoute` | `urbaser_sweeping_microroute` |
| `GreenZoneAssignment` | `urbaser_green_zone_assignment` |
| `CuttingSchedule` | `urbaser_cutting_schedule` |
| `Intervention` | `urbaser_intervention` |
| `ServiceContent` | `urbaser_service_content` |
| `AspectContent` | `urbaser_aspect_content` |

`GreenZoneAssignment` reemplaza al antiguo `GreenZone`:
```
public_space_id   IntegerField (soft FK a geodata_public_space)
external_id       IntegerField UNIQUE     # ID del cronograma PDF Urbaser
cycle_days        IntegerField default=11
active            BooleanField
```
La geometría vive en `geodata.PublicSpace`. Aquí solo la responsabilidad operativa.

`sla_handlers.py` contiene la lógica PostGIS específica de Urbaser y se conecta a `complaint_created` desde `apps.py: ready()`. Detalle del patrón en `REGISTRY-PATTERN.md`.

---

## 4. Endpoints resultantes

| Path base | App | Contenido |
|---|---|---|
| `/api/v1/core/` | core | services, aspects, communes, neighborhoods |
| `/api/v1/geodata/` | geodata | public-spaces (geojson opcional) |
| `/api/v1/veeduria/` | veeduria | complaints, evidence, alerts, metrics |
| `/api/v1/urbaser/` | urbaser | sweeping-macroroutes, sweeping-microroutes, green-zone-assignments |

Frontend cambia de `/urbaser/complaints/` → `/veeduria/complaints/`.

---

## 5. Reglas de dependencia entre apps

1. `core` no importa de nadie.
2. `geodata` solo importa de `core` (para soft FK a `Neighborhood`).
3. `veeduria` solo importa de `core` (para validar `Service`/`Aspect` en serializer).
4. `infra_servicios_publicos_urbaser` puede importar de `core`, `geodata` y `veeduria`. Es el único que tiene acoplamiento amplio porque encarna el dominio.
5. **FK duras** solo dentro del mismo archivo de modelos.
6. **Soft FKs** entre apps con snapshot de texto (igual que V1).
7. Comunicación entre apps de servicio y veeduria es por **signals** (`complaint_created`), nunca import directo.

---

## 6. Convenciones (heredadas de V1)

- Código en inglés, `verbose_name` en español.
- `db_table` explícito siempre. Prefijos: `core_*`, `geodata_*`, `vee_*`, `urbaser_*`.
- SRID 4326 en toda la BD. Reproyección a 3116 solo en cálculos métricos.
- TimeZone `America/Bogota`.

---

## 7. Lo que queda igual

- Stack: Django 6 + DRF + GeoDjango + PostGIS + Redis.
- Frontend: React 19 + Vite + Tailwind + Leaflet.
- Cascada de location en `Complaint`: GPS → manual → centroide.
- Pipeline asíncrono con signals (síncrono en Fase 1, Celery en Fase 2).
- Carga de shapefiles del POT con geopandas + reproyección automática.

---

## 8. Lo que se rompe a propósito

- Tablas se renombran (`urbaser_complaint` → `vee_complaint`, etc.).
- Endpoints se renombran (`/urbaser/complaints/` → `/veeduria/complaints/`).
- Migraciones se borran y se regeneran desde cero (es prototipo).
- Datos se borran y se repueblan con `make demo`.

---

## 9. Diagramas

### Flujo de una denuncia ciudadana

```
Frontend (CitizenPortal)
  POST /veeduria/complaints/ {service_id, aspect_id, lat, lng, ...}

veeduria.serializers.ComplaintSerializer
  valida service/aspect contra core
  resuelve location (gps → manual → centroide)
  guarda Complaint + snapshots de texto

veeduria.signals.complaint_created.send(
  service_slug=..., complaint_id=..., location=..., ...
)

  ├─ urbaser.sla_handlers.handle_sweeping (si service_slug='sweeping-cleaning')
  │    cruza con SweepingMicroRoute, crea SLAAlert genérica en veeduria
  │
  ├─ urbaser.sla_handlers.handle_green_zones (si service_slug='green-zones')
  │    cruza con PublicSpace + GreenZoneAssignment, crea SLAAlert
  │
  └─ veeduria.metrics.recalculate (always)
       actualiza MetricByCommune para (commune, service_slug, mes)
```

### Mapa de FKs

```
core.Service ◄── soft ── veeduria.Complaint.service_slug
                                     │
                                     ├── veeduria.Evidence (hard FK)
                                     └── veeduria.SLAAlert.complaint_id (soft)

core.Commune ◄── soft ── veeduria.MetricByCommune.commune_id

geodata.PublicSpace ◄── soft ── urbaser.GreenZoneAssignment.public_space_id

urbaser.SweepingMacroRoute ◄── hard ── urbaser.SweepingMicroRoute
urbaser.GreenZoneAssignment ◄── hard ── urbaser.CuttingSchedule
                                  └── hard ── urbaser.Intervention
```
