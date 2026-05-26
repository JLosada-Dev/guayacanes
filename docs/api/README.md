# Guyacanes API v1 — Referencia completa

Base URL: `http://localhost:8000/api/v1/`

---

## Documentación interactiva (Swagger / OpenAPI)

Generada automáticamente con `drf-spectacular` a partir del código.

| URL | Formato | Uso |
|-----|---------|-----|
| `http://localhost:8000/api/docs/` | Swagger UI | Navegación + prueba interactiva |
| `http://localhost:8000/api/redoc/` | ReDoc | Lectura detallada de la API |
| `http://localhost:8000/api/schema/` | OpenAPI 3.0 YAML | Schema descargable (integración con otras tools) |

Los tres endpoints se actualizan automáticamente cada vez que se modifica un ViewSet o Serializer. No requieren sincronización manual con este archivo — este README es la referencia conceptual, Swagger es la referencia técnica.

---

## Endpoints disponibles

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/core/services/` | Servicios activos + contenido editorial |
| GET | `/core/aspects/?service=<slug>` | Aspectos de un servicio |
| GET | `/core/communes/` | 9 comunas de Popayán con geometría |
| GET | `/core/neighborhoods/?commune_id=<id>` | Barrios de una comuna (para fuzzy search en cliente) |
| POST | `/urbaser/complaints/` | Crear denuncia ciudadana |
| GET | `/urbaser/complaints/` | Listar denuncias (con filtros) |
| GET | `/urbaser/complaints/{id}/` | Detalle de denuncia |
| GET | `/urbaser/complaints/geojson/` | Denuncias como GeoJSON FeatureCollection |
| POST | `/urbaser/evidence/` | Subir foto de evidencia |
| GET | `/urbaser/alerts/` | Alertas SLA (con filtros) |
| GET | `/urbaser/alerts/{id}/` | Detalle de alerta SLA |
| GET | `/urbaser/metrics/` | Métricas heatmap por comuna |
| GET | `/urbaser/metrics/{id}/` | Detalle métrica de una comuna |

---

## Colecciones disponibles

### Importar en Bruno (recomendado)
1. Abrir Bruno
2. Open Collection
3. Seleccionar carpeta `docs/api/guyacanes.bruno/`
4. Activar environment `local`

**Requests incluidos (13):**

```
core/
  services.bru              GET /api/v1/core/services/
  aspects.bru               GET /api/v1/core/aspects/?service=<slug>
  communes.bru              GET /api/v1/core/communes/

veeduria/
  complaint-gps.bru         POST /complaints/ (con GPS)
  complaint-centroid.bru    POST /complaints/ (fallback centroide)
  complaints-list.bru       GET /complaints/ (con filtros)
  complaint-detail.bru      GET /complaints/{id}/
  complaints-geojson.bru    GET /complaints/geojson/
  evidence-upload.bru       POST /evidence/ (multipart)

auditoria/
  alerts-list.bru           GET /alerts/ (con filtros)
  alerts-detail.bru         GET /alerts/{id}/
  metrics-heatmap.bru       GET /metrics/
  metrics-detail.bru        GET /metrics/{id}/
```

### Importar en Postman
1. Abrir Postman → Import → Upload Files
2. Seleccionar `docs/api/guyacanes.postman_collection.json`
3. Configurar variable `base_url` = `http://localhost:8000`

---

## Core — Catálogo

### GET /api/v1/core/services/

Retorna los servicios activos (`active=True`). Los servicios inactivos (Fase 2) no aparecen.

**Respuesta 200:**
```json
[
  {
    "id": 1,
    "name": "Barrido y Limpieza",
    "slug": "sweeping-cleaning",
    "description": "...",
    "active": true,
    "order": 1,
    "content": {
      "icon": "trash-2",
      "summary": "Descripción corta para el ciudadano",
      "full_description": "Texto completo del servicio...",
      "frequency": "Semanal según macroruta asignada",
      "citizen_rights": "Texto de derechos del ciudadano según PPS 2024",
      "updated_at": "2026-04-14T10:00:00Z"
    }
  },
  {
    "id": 2,
    "name": "Corte de Césped y Zonas Verdes",
    "slug": "green-zones",
    "description": "...",
    "active": true,
    "order": 2,
    "content": null
  }
]
```

> `content` es `null` hasta que un líder de operaciones cargue el texto desde el admin de Django.

**Campos de `content`:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `icon` | string | Nombre del ícono Lucide (ej: `trash-2`, `leaf`) |
| `summary` | string | Descripción corta (máx 300 chars) para tarjeta del portal |
| `full_description` | string | Texto completo del servicio |
| `frequency` | string | Frecuencia según contrato PPS 2024 |
| `citizen_rights` | string | Derechos del ciudadano según PPS 2024 |
| `updated_at` | datetime | Última actualización del contenido |

---

### GET /api/v1/core/aspects/?service=\<slug\>

Retorna los aspectos activos del servicio especificado.

**Parámetros:**

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `service` | string | Sí | Slug del servicio (ej: `sweeping-cleaning`) |

**Respuesta 200:**
```json
[
  {
    "id": 1,
    "service": 1,
    "slug": "scope",
    "description": "Alcance del barrido incompleto",
    "active": true,
    "content": {
      "icon": "map",
      "what_is": "Qué es este problema y cuándo ocurre...",
      "how_to_evidence": "Cómo documentarlo con fotos...",
      "response_time": "72 horas según contrato",
      "updated_at": "2026-04-14T10:00:00Z"
    }
  }
]
```

**Campos de `content`:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `icon` | string | Nombre del ícono Lucide |
| `what_is` | string | Explicación del problema para el ciudadano |
| `how_to_evidence` | string | Instrucciones para documentar con fotos |
| `response_time` | string | Tiempo de respuesta según contrato PPS |
| `updated_at` | datetime | Última actualización |

---

### GET /api/v1/core/communes/

Retorna las 9 comunas de Popayán con su geometría en EPSG:4326.

**Respuesta 200:**
```json
[
  {
    "id": 1,
    "number": 1,
    "name": "Comuna 1",
    "area_hectares": "643.01",
    "geom": {
      "type": "Polygon",
      "coordinates": [[[...], ...]]
    }
  }
]
```

---

### GET /api/v1/core/neighborhoods/?commune_id=\<id\>

Lista los barrios de una comuna, ordenados alfabéticamente. Pensado
para alimentar un selector con búsqueda aproximada (fuzzy) en cliente:
la respuesta es plana, sin geometría, y no pagina (≤60 barrios por
comuna).

**Parámetros:**

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `commune_id` | integer | Sí | PK de la comuna (`Commune.id`, no `Commune.number`) |

**Respuesta 200:**
```json
[
  { "id": 1,  "name": "Alcalá",  "commune_id": 8 },
  { "id": 2,  "name": "Antonio Nariño", "commune_id": 8 },
  { "id": 3,  "name": "Belalcázar", "commune_id": 8 }
]
```

**Respuestas de error:**
- `400` si `commune_id` falta o no es entero.
- Lista vacía (`[]`) si la comuna existe pero aún no tiene barrios cargados.

---

## Veeduría — Denuncias

### POST /api/v1/urbaser/complaints/

Crea una denuncia ciudadana. Dispara automáticamente el pipeline SLA via signal `post_save`.

**Body JSON:**
```json
{
  "service_id": 1,
  "aspect_id": 2,
  "commune_id": 4,
  "commune_name": "Comuna 4",
  "neighborhood_id": null,
  "neighborhood_name": "",
  "is_rural": false,
  "hamlet_name": "",
  "latitude": 2.4448,
  "longitude": -76.6147,
  "location_source": "gps",
  "description": "No pasaron a barrer esta semana"
}
```

**Campos del body:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `service_id` | integer | Sí | ID del servicio (obtenido de `/core/services/`) |
| `aspect_id` | integer | Sí | ID del aspecto (obtenido de `/core/aspects/`) |
| `commune_id` | integer | Sí si no hay GPS | ID de la comuna seleccionada |
| `commune_name` | string | No | Nombre snapshot de la comuna |
| `neighborhood_id` | integer | No | ID del barrio (soft FK) |
| `neighborhood_name` | string | No | Nombre snapshot del barrio |
| `is_rural` | boolean | No | `true` si es zona rural |
| `hamlet_name` | string | No | Nombre de la vereda si `is_rural=true` |
| `latitude` | float | No* | Latitud GPS (EPSG:4326) |
| `longitude` | float | No* | Longitud GPS (EPSG:4326) |
| `location_source` | string | No | `gps` / `manual` / `centroid` |
| `description` | string | No | Descripción opcional de la denuncia |

> *Si no se envían `latitude`/`longitude`, se usa el centroide de `commune_id` como fallback.

#### Cascada de coordenada (location_source)

```
1. GPS:      latitude + longitude presentes  → location = Point(lng, lat)  → location_source = "gps"
2. Manual:   pin en mapa (mismo que GPS)      → location = Point(lng, lat)  → location_source = "manual"
3. Centroid: sin coordenadas GPS              → location = centroide de commune  → location_source = "centroid"
4. Error:    sin GPS y sin commune_id         → HTTP 400
```

#### Validación del serializer

1. `service_id` se valida contra `core_service` — debe existir y `active=True`
2. `aspect_id` se valida contra los aspectos del servicio — debe existir y `active=True`, y pertenecer al servicio
3. Los campos `service_slug`, `service_name`, `aspect_slug`, `aspect_description` se llenan automáticamente desde el catálogo (snapshot)
4. `commune_name` se llena automáticamente si solo se envía `commune_id`

**Respuesta 201:**
```json
{
  "id": 42,
  "service_id": 1,
  "service_slug": "sweeping-cleaning",
  "service_name": "Barrido y Limpieza",
  "aspect_id": 2,
  "aspect_slug": "frequency",
  "aspect_description": "Frecuencia de barrido no cumplida",
  "commune_id": 4,
  "commune_name": "Comuna 4",
  "neighborhood_id": null,
  "neighborhood_name": "",
  "is_rural": false,
  "hamlet_name": "",
  "location_source": "gps",
  "description": "No pasaron a barrer esta semana",
  "status": "received",
  "created_at": "2026-04-14T10:32:00Z",
  "evidence": []
}
```

**Errores posibles:**

| HTTP | Campo | Mensaje |
|------|-------|---------|
| 400 | `service_id` | `"Servicio no encontrado o inactivo."` |
| 400 | `aspect_id` | `"Aspecto no encontrado o no pertenece al servicio."` |
| 400 | `commune_id` | `"Comuna no encontrada."` |
| 400 | `location` | `"Se requiere coordenada GPS o selección de comuna."` |

---

### GET /api/v1/urbaser/complaints/

Lista denuncias. Ordenadas por `-created_at` por defecto.

**Filtros disponibles:**

| Parámetro | Tipo | Valores válidos | Ejemplo |
|-----------|------|-----------------|---------|
| `status` | string | `received` / `under_review` / `closed` | `?status=received` |
| `service_slug` | string | `sweeping-cleaning` / `green-zones` | `?service_slug=sweeping-cleaning` |
| `commune_id` | integer | 1–9 | `?commune_id=4` |
| `is_rural` | boolean | `true` / `false` | `?is_rural=false` |
| `search` | string | Busca en aspecto, comuna, barrio | `?search=limpieza` |
| `ordering` | string | `created_at` / `status` / `service_slug` (prefijo `-` invierte) | `?ordering=-created_at` |

**Ejemplo:** `GET /api/v1/urbaser/complaints/?status=received&commune_id=4&ordering=-created_at`

**Respuesta 200:**
```json
[
  {
    "id": 42,
    "service_id": 1,
    "service_slug": "sweeping-cleaning",
    "service_name": "Barrido y Limpieza",
    "aspect_id": 2,
    "aspect_slug": "frequency",
    "aspect_description": "Frecuencia de barrido no cumplida",
    "commune_id": 4,
    "commune_name": "Comuna 4",
    "neighborhood_id": null,
    "neighborhood_name": "",
    "is_rural": false,
    "hamlet_name": "",
    "location_source": "gps",
    "description": "No pasaron a barrer esta semana",
    "status": "received",
    "created_at": "2026-04-14T10:32:00Z",
    "evidence": []
  }
]
```

---

### GET /api/v1/urbaser/complaints/{id}/

Detalle de una denuncia. Incluye las fotos de evidencia adjuntas.

**Respuesta 200:**
```json
{
  "id": 42,
  "service_id": 1,
  "service_slug": "sweeping-cleaning",
  "service_name": "Barrido y Limpieza",
  "aspect_id": 2,
  "aspect_slug": "frequency",
  "aspect_description": "Frecuencia de barrido no cumplida",
  "commune_id": 4,
  "commune_name": "Comuna 4",
  "neighborhood_id": null,
  "neighborhood_name": "",
  "is_rural": false,
  "hamlet_name": "",
  "location_source": "gps",
  "description": "No pasaron a barrer esta semana",
  "status": "received",
  "created_at": "2026-04-14T10:32:00Z",
  "evidence": [
    {
      "id": 5,
      "image": "http://localhost:8000/media/complaints/2026/04/foto.jpg",
      "uploaded_at": "2026-04-14T10:33:00Z"
    }
  ]
}
```

---

### GET /api/v1/urbaser/complaints/geojson/

Retorna denuncias como GeoJSON FeatureCollection. Acepta los mismos filtros que el listado.

**Respuesta 200:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-76.6147, 2.4448]
      },
      "properties": {
        "id": 42,
        "service_slug": "sweeping-cleaning",
        "aspect_description": "Frecuencia de barrido no cumplida",
        "commune_name": "Comuna 4",
        "status": "received",
        "created_at": "2026-04-14T10:32:00Z"
      }
    }
  ]
}
```

> Coordenadas en formato GeoJSON: `[longitud, latitud]` (EPSG:4326).

---

### POST /api/v1/urbaser/evidence/

Sube una foto de evidencia asociada a una denuncia existente.

**Formato:** `multipart/form-data`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `complaint` | integer | ID de la denuncia existente |
| `image` | file | Archivo de imagen (JPG, PNG, etc.) |

**Respuesta 201:**
```json
{
  "id": 5,
  "image": "http://localhost:8000/media/complaints/2026/04/foto.jpg",
  "uploaded_at": "2026-04-14T10:33:00Z"
}
```

> Las imágenes se guardan en `media_local/complaints/{año}/{mes}/`.

---

## Auditoría SLA

### GET /api/v1/urbaser/alerts/

Lista las alertas SLA generadas automáticamente por el pipeline PostGIS.
**Nunca se crean manualmente** — se generan via signal `post_save` al crear una denuncia.

**Filtros disponibles:**

| Parámetro | Tipo | Valores válidos | Ejemplo |
|-----------|------|-----------------|---------|
| `violation` | boolean | `true` / `false` | `?violation=true` |
| `service_slug` | string | `sweeping-cleaning` / `green-zones` | `?service_slug=green-zones` |
| `route_type` | string | `sweeping_microroute` / `green_zone` | `?route_type=sweeping_microroute` |
| `confidence` | string | `high` / `medium` / `low` | `?confidence=high` |
| `complaint_id` | integer | ID de la denuncia | `?complaint_id=42` |
| `ordering` | string | `generated_at` / `violation` / `service_slug` | `?ordering=-generated_at` |

**Respuesta 200:**
```json
[
  {
    "id": 10,
    "complaint_id": 42,
    "service_slug": "sweeping-cleaning",
    "route_type": "sweeping_microroute",
    "route_id": 120,
    "macroroute_code": "B211",
    "violation": true,
    "distance_meters": 34.7,
    "days_since_intervention": null,
    "confidence": "high",
    "generated_at": "2026-04-14T10:32:01Z"
  }
]
```

**Descripción de campos:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `complaint_id` | integer | Soft FK a la denuncia (no FK real en BD) |
| `service_slug` | string | Servicio al que pertenece la alerta |
| `route_type` | string | `sweeping_microroute` (barrido) o `green_zone` (zonas verdes) |
| `route_id` | integer | ID de la ruta o zona verde más cercana |
| `macroroute_code` | string | Código oficial PPS (B211, 611, etc.) — para reportes |
| `violation` | boolean | `true` si hay incumplimiento SLA confirmado |
| `distance_meters` | float | Distancia real en metros (EPSG:3116 Colombia Oeste) a la ruta |
| `days_since_intervention` | integer | Días desde el último corte (solo zonas verdes, null en barrido) |
| `confidence` | string | Confianza en la coordenada: `high`=GPS, `medium`=manual, `low`=centroide |
| `generated_at` | datetime | Timestamp de generación (auto, read-only) |

#### Lógica SLA (cómo se genera una alerta)

**Barrido (`sweeping-cleaning`):**
```
Si la denuncia está dentro de 50m de una SweepingMicroRoute activa (ST_DWithin EPSG:3116)
Y la hora de created_at está FUERA de la ventana de operación de esa macroruta
→ violation = true
```

**Zonas verdes (`green-zones`):**
```
Si la denuncia está dentro de 30m de una GreenZone activa (ST_DWithin EPSG:3116)
Y (fecha_hoy - last_intervention_date) > zone.cycle_days (11 días)
→ violation = true

O si hay CuttingSchedule con fecha pasada y executed = false
→ violation = true directa
```

---

### GET /api/v1/urbaser/alerts/{id}/

Detalle de una alerta SLA específica. Misma estructura que el listado.

---

### GET /api/v1/urbaser/metrics/

Métricas agregadas por comuna y servicio. Alimenta el heatmap del dashboard.
Se recalculan automáticamente cada vez que se genera un `SLAAlert`.

**Filtros disponibles:**

| Parámetro | Tipo | Ejemplo |
|-----------|------|---------|
| `service_slug` | string | `?service_slug=sweeping-cleaning` |
| `period` | date | `?period=2026-04-01` |
| `commune_id` | integer | `?commune_id=4` |
| `ordering` | string | `?ordering=-violation_rate` |

**Respuesta 200:**
```json
[
  {
    "id": 3,
    "commune_id": 4,
    "commune_name": "Comuna 4",
    "service_slug": "sweeping-cleaning",
    "total_complaints": 25,
    "total_alerts": 20,
    "total_violations": 18,
    "violation_rate": 0.72,
    "period": "2026-04-01",
    "updated_at": "2026-04-14T10:32:02Z"
  }
]
```

**Descripción de campos:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `commune_id` | integer | Soft FK a la comuna |
| `commune_name` | string | Nombre snapshot de la comuna |
| `service_slug` | string | Servicio evaluado |
| `total_complaints` | integer | Total de denuncias en el periodo |
| `total_alerts` | integer | Total de alertas SLA generadas |
| `total_violations` | integer | Total de alertas con `violation=true` |
| `violation_rate` | float | Fracción `total_violations / total_alerts` (0.0–1.0) |
| `period` | date | Primer día del mes calculado (ej: `2026-04-01`) |
| `updated_at` | datetime | Última actualización (auto, read-only) |

**Colores del heatmap:**

| `violation_rate` | Color | Significado |
|------------------|-------|-------------|
| `> 0.70` | Rojo | Crítico — incumplimiento sistemático |
| `> 0.40` | Naranja | Atención — incumplimiento parcial |
| `≤ 0.40` | Verde | Conforme — dentro de parámetros SLA |

---

## Campos Choice — Referencia completa

### `Complaint.status`
| Valor | Descripción |
|-------|-------------|
| `received` | Denuncia recibida — estado inicial, automático |
| `under_review` | En revisión — asignado por operaciones |
| `closed` | Cerrada — resuelta o archivada |

> `status` siempre inicia en `received`. No puede ser modificado desde el endpoint de creación (read-only).

### `Complaint.location_source`
| Valor | Descripción |
|-------|-------------|
| `gps` | Coordenadas GPS del dispositivo móvil — confianza alta |
| `manual` | Pin colocado manualmente en el mapa — confianza media |
| `centroid` | Centroide de la comuna seleccionada — confianza baja (fallback) |

### `SLAAlert.route_type`
| Valor | Descripción |
|-------|-------------|
| `sweeping_microroute` | Alerta asociada a ruta de barrido (U18_VIAL.shp) |
| `green_zone` | Alerta asociada a zona verde (espacio público POT) |

### `SLAAlert.confidence`
| Valor | Descripción |
|-------|-------------|
| `high` | Denuncia con coordenada GPS — máxima precisión |
| `medium` | Denuncia con pin manual en mapa |
| `low` | Denuncia con centroide de comuna — mínima precisión |

### `SweepingMacroRoute.zone_type`
| Valor | Descripción |
|-------|-------------|
| `residential` | Zona residencial (B211, B212, B213) |
| `main_roads` | Vías principales (611) |
| `historic_center` | Centro histórico (621, 631b, 117b) |
| `market` | Plazas de mercado (127b) |
| `sunday` | Turno dominical (117b, 127b) |

### `GreenZone.zone_type`
| Valor | Descripción |
|-------|-------------|
| `park` | Parque urbano recreativo |
| `road_divider` | Separador vial |
| `bike_path` | Ciclorruta |
| `roundabout` | Glorieta |
| `sports` | Espacio deportivo |
| `other` | Otro tipo de espacio público |

### `Intervention.intervention_type`
| Valor | Descripción |
|-------|-------------|
| `grass_cut` | Corte de césped |
| `tree_pruning` | Poda de árboles |

---

## Notas técnicas

- Todas las geometrías en **EPSG:4326** (WGS 84)
- Distancias SLA calculadas en **EPSG:3116** (Colombia Oeste — metros reales) via `Transform('geom', 3116)`
- `SLAAlert` y `CommuneMetric` son **siempre read-only** — generados automáticamente
- El campo `location` en `Complaint` **nunca es null** — siempre existe una coordenada
- Las imágenes de evidencia se almacenan en `media_local/complaints/{año}/{mes}/`
- El pipeline SLA es **síncrono en Fase 1** — ocurre en el mismo request de creación de denuncia
