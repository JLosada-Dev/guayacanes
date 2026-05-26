# Mapa de modelos — antes y después

**Fecha:** 2026-04-28
**Propósito:** referencia rápida de dónde vivía cada modelo en V1 y dónde queda en V2.

---

## Tabla maestra

| V1 archivo | V1 modelo | V1 tabla | → | V2 app | V2 modelo | V2 tabla | Cambios |
|---|---|---|---|---|---|---|---|
| `core/models/geography.py` | `Commune` | `core_commune` | → | `core` | `Commune` | `core_commune` | sin cambios |
| `core/models/geography.py` | `Neighborhood` | `core_neighborhood` | → | `core` | `Neighborhood` | `core_neighborhood` | sin cambios |
| `core/models/catalog.py` | `Service` | `core_service` | → | `core` | `Service` | `core_service` | sin cambios |
| `core/models/catalog.py` | `Aspect` | `core_aspect` | → | `core` | `Aspect` | `core_aspect` | sin cambios |
| `core/models/catalog.py` | `ServiceContent` | `core_service_content` | → | `urbaser` | `ServiceContent` | `urbaser_service_content` | mover de app, renombrar tabla |
| `core/models/catalog.py` | `AspectContent` | `core_aspect_content` | → | `urbaser` | `AspectContent` | `urbaser_aspect_content` | mover de app, renombrar tabla |
| `urbaser/models/operaciones.py` | `SweepingMacroRoute` | `urbaser_sweeping_macroroute` | → | `urbaser` | `SweepingMacroRoute` | `urbaser_sweeping_macroroute` | sin cambios |
| `urbaser/models/operaciones.py` | `SweepingMicroRoute` | `urbaser_sweeping_microroute` | → | `urbaser` | `SweepingMicroRoute` | `urbaser_sweeping_microroute` | sin cambios |
| `urbaser/models/operaciones.py` | `GreenZone` | `urbaser_green_zone` | → | `geodata` + `urbaser` | `PublicSpace` + `GreenZoneAssignment` | `geodata_public_space` + `urbaser_green_zone_assignment` | dividido en 2: geometría va a geodata, ciclo y operación queda en urbaser |
| `urbaser/models/operaciones.py` | `CuttingSchedule` | `urbaser_cutting_schedule` | → | `urbaser` | `CuttingSchedule` | `urbaser_cutting_schedule` | apunta a `GreenZoneAssignment` |
| `urbaser/models/operaciones.py` | `Intervention` | `urbaser_intervention` | → | `urbaser` | `Intervention` | `urbaser_intervention` | apunta a `GreenZoneAssignment` |
| `urbaser/models/veeduria.py` | `Complaint` | `urbaser_complaint` | → | `veeduria` | `Complaint` | `vee_complaint` | mover de app, renombrar tabla |
| `urbaser/models/veeduria.py` | `Evidence` | `urbaser_evidence` | → | `veeduria` | `Evidence` | `vee_evidence` | mover de app, renombrar tabla |
| `urbaser/models/auditoria.py` | `SLAAlert` | `urbaser_sla_alert` | → | `veeduria` | `SLAAlert` | `vee_sla_alert` | genérica: `route_type` ahora `CharField` libre, sin choices duros |
| `urbaser/models/auditoria.py` | `CommuneMetric` | `urbaser_commune_metric` | → | `veeduria` | `MetricByCommune` | `vee_metric_by_commune` | renombrado para enfatizar que es transversal |

---

## Modelos nuevos en V2

### `geodata.PublicSpace`

Reemplaza la **geometría** de `GreenZone`. Genérico para cualquier app que necesite consultar espacio público del POT.

```
external_id      IntegerField UNIQUE     # ID compuesto por capa fuente
name             CharField(300)
space_type       CharField(20)           # park / road_divider / corridor / node / sports / other
area_sqm         DecimalField null
source_layer     CharField(50)           # 'U19_EP1', 'U19_EP2', 'U19_EP3', 'U19_EP5', 'SEPARADOR'
neighborhood_id  IntegerField null       # soft FK
neighborhood_name CharField(150)
active           BooleanField default=True
geom             MultiPolygonField(4326)
```

Fuente: 5 shapefiles combinados (mismos que cargaba `load_green_zones`).

### `urbaser.GreenZoneAssignment`

Reemplaza la **lógica operativa** de `GreenZone`. Cada `PublicSpace` puede o no tener un `GreenZoneAssignment` urbaser.

```
public_space_id   IntegerField           # soft FK a geodata_public_space
public_space_name CharField(300)         # snapshot
external_id       IntegerField UNIQUE    # ID del cronograma PDF Urbaser
cycle_days        IntegerField default=11
active            BooleanField default=True
```

`CuttingSchedule.zone` y `Intervention.zone` apuntan a `GreenZoneAssignment` ahora (no a `GreenZone`).

### `veeduria.SLAAlert` (refactor de auditoría)

Versión genérica de la antigua `urbaser_sla_alert`:

```
complaint_id              IntegerField db_index  # soft FK
service_slug              CharField(100)
route_type                CharField(50)          # libre — antes choices
route_id                  IntegerField
route_label               CharField(50) blank    # antes 'macroroute_code', ahora genérico
violation                 BooleanField
distance_meters           FloatField null
extra_int                 IntegerField null      # antes 'days_since_intervention' — ahora genérico
extra_data                JSONField default=dict # extensión por servicio
confidence                CharField(6)
generated_at              DateTimeField auto_now_add
```

`extra_data` permite a cada servicio guardar campos que no encajan en el esquema base sin migración en veeduria.

### `veeduria.MetricByCommune`

Renombrado de `CommuneMetric`. Lógica idéntica.

```
commune_id        IntegerField           # soft FK a core_commune
commune_name      CharField(50)
service_slug      CharField(100)
total_complaints  IntegerField default=0
total_alerts      IntegerField default=0
total_violations  IntegerField default=0
violation_rate    FloatField default=0.0
period            DateField              # primer día del mes
updated_at        DateTimeField auto_now
unique_together: [commune_id, service_slug, period]
```

---

## Fixtures — mapeo

| V1 archivo | V1 contenido | → | V2 archivo | V2 app |
|---|---|---|---|---|
| `fixtures/core_services.json` | 5 servicios (Urbaser-céntricos) | → | `apps/core/fixtures/services.json` | core (estructura genérica) |
| `fixtures/core_aspects.json` | 11 aspectos Urbaser | → | `apps/core/fixtures/aspects.json` | core |
| `fixtures/core_service_content.json` | 2 contenidos editoriales Urbaser | → | `apps/infra_servicios_publicos_urbaser/fixtures/service_content.json` | urbaser |
| `fixtures/core_aspect_content.json` | 11 contenidos editoriales Urbaser | → | `apps/infra_servicios_publicos_urbaser/fixtures/aspect_content.json` | urbaser |

Convención nueva: cada app guarda sus fixtures en `apps/<app>/fixtures/`.

---

## Management commands — mapeo

| V1 ubicación | V1 comando | → | V2 ubicación | V2 comando |
|---|---|---|---|---|
| `core/management/commands/load_communes.py` | `load_communes` | → | `core/management/commands/load_communes.py` | `load_communes` |
| `core/management/commands/load_neighborhoods.py` | `load_neighborhoods` | → | `core/management/commands/load_neighborhoods.py` | `load_neighborhoods` |
| `urbaser/management/commands/load_sweeping.py` | `load_sweeping` | → | `urbaser/management/commands/load_sweeping.py` | `load_sweeping` |
| `urbaser/management/commands/load_green_zones.py` | `load_green_zones` | → | **dividido** | `load_public_spaces` (geodata) + `load_green_zone_assignments` (urbaser) |
| `urbaser/management/commands/load_cutting_schedule.py` | `load_cutting_schedule` | → | `urbaser/management/commands/load_cutting_schedule.py` | `load_cutting_schedule` |
| `urbaser/management/commands/seed_complaints.py` | `seed_complaints` | → | `veeduria/management/commands/seed_complaints.py` | `seed_complaints` |

`load_green_zones` se parte en dos comandos:
- `load_public_spaces` (geodata) carga los 313 polígonos de los 5 shapefiles a `geodata_public_space`.
- `load_green_zone_assignments` (urbaser) crea los `GreenZoneAssignment` por cada `PublicSpace` (1:1 inicialmente, con `cycle_days=11` por defecto).

---

## Signals — mapeo

| V1 | → | V2 |
|---|---|---|
| `urbaser/signals.py: complaint_created` | → | `veeduria/signals.py: complaint_created` |
| `urbaser/receivers.py: handle_complaint_created` | → | `urbaser/sla_handlers.py: handle_sweeping`, `handle_green_zones` |

Recalculo de métricas: queda en `veeduria/metrics.py: recalculate_for(commune_id, service_slug)`. Cualquier handler de servicio puede llamarlo después de crear sus alertas.

---

## Archivos a borrar

- `apps/infra_servicios_publicos_urbaser_facturacion/` (app vacía completa).
- Todas las carpetas `migrations/` excepto el `__init__.py`.
- `fixtures/core_services.json`, `core_aspects.json`, `core_service_content.json`, `core_aspect_content.json` (se mueven a `apps/<app>/fixtures/`).

---

## Frontend — mapeo

| V1 | → | V2 |
|---|---|---|
| `src/api/core.ts` | → | `src/api/core.ts` (sin cambios — services, aspects, communes) |
| `src/api/urbaser.ts` | → | `src/api/veeduria.ts` (complaints, evidence, alerts, metrics) |
| — | → | `src/api/urbaser.ts` (queda solo si se exponen rutas/zonas en UI; opcional) |
| `pages/CitizenPortal.tsx` | → | igual; cambia el path en `createComplaint` y `uploadEvidence` |
| `pages/SupervisorDashboard.tsx` | → | igual; cambia paths en `getAlerts`, `getMetrics`, `getComplaintsGeoJSON` |
| `types/index.ts` | → | igual; los tipos siguen siendo los mismos campos |
