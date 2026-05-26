# Contrato de eventos — `apps.veeduria.signals.complaint_created`

**Producer:** `apps.veeduria` (post_save de `Complaint`).
**Consumers:** cualquier app de sección que se conecte vía
`complaint_created.connect(handler, dispatch_uid='<seccion>.handle_complaint')`
desde su `AppConfig.ready()`. Patrón documentado en `REGISTRY-PATTERN.md`.

---

## ¿Por qué un contrato explícito?

El día que esto se mueva a Kafka/RabbitMQ, el payload viaja serializado
como JSON. Por eso el contrato del evento solo usa primitivos. Si un
consumer empieza a depender de objetos GeoDjango o `datetime`, se
rompe la portabilidad.

---

## Schema del payload

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `complaint_id` | `int` | sí | PK de `vee_complaint`. Soft FK estable entre apps/servicios |
| `section_slug` | `str` | sí | Slug de la sección dueña del servicio. Snapshot al crear |
| `service_slug` | `str` | sí | Slug del servicio dentro de la sección |
| `aspect_slug` | `str` | sí | Slug del aspecto dentro del servicio |
| `location_wkt` | `str` | sí | Geometría en formato WKT (`POINT (-76.6 2.47)`) — SRID implícito 4326 |
| `location_lat` | `float` | sí | Conveniencia: latitud (eje Y), redundante con WKT |
| `location_lng` | `float` | sí | Conveniencia: longitud (eje X), redundante con WKT |
| `location_source` | `str` | sí | Uno de `gps`, `manual`, `centroid`. Confianza de la coordenada |
| `commune_id` | `int \| None` | no | Soft FK a `core_commune`. Puede ser `None` si la denuncia es rural |
| `created_at` | `str` | sí | ISO 8601 con timezone (`2026-04-28T15:30:00-05:00`) |

`sender` (de Django Signal) es siempre la clase `Complaint`.

---

## Reglas para los consumers

1. **Filtrar por slug primero.** Cada handler debe descartar denuncias
   que no le corresponden. Los matches válidos son por
   `section_slug` (toda la sección) o por `service_slug` (granularidad
   por servicio). Convención: usar un `set` constante por handler.

   ```python
   URBASER_SLUGS = {'sweeping-cleaning', 'green-zones'}

   def handle_complaint(sender, service_slug, **kwargs):
       if service_slug not in URBASER_SLUGS:
           return
       ...
   ```

2. **Reconstruir objetos pesados localmente.** Si necesitas el `Point`
   de GeoDjango, constrúyelo desde lat/lng. Si necesitas el `datetime`,
   parsea `created_at` con `datetime.fromisoformat`. Veeduría no envía
   estos objetos para mantener serializabilidad.

3. **No mutar el payload.** Cada handler recibe el mismo dict. Tratar
   `kwargs` como inmutable.

4. **Idempotencia en lo posible.** En el futuro con bus de eventos,
   un evento puede entregarse más de una vez. Los handlers deberían
   tolerar reentrada — por ejemplo, usar `update_or_create` para
   alertas o un identificador externo de mensaje.

5. **`dispatch_uid` único.** Al conectar, usar un identificador con
   prefijo del dominio (`urbaser.handle_complaint`,
   `vivienda.handle_complaint`). Esto evita duplicados si Django
   recarga el módulo (autoreload de runserver).

---

## Equivalencia futura — Kafka/RabbitMQ

```
Tema:        complaint.created
Particiones: por commune_id (preserva orden por comuna)
Retención:   30 días (suficiente para reprocesar fallos de handler)
Esquema:     JSON Schema generado a partir de esta tabla

Productor:   veeduria-service (después del INSERT en vee_complaint)
Consumidores: urbaser-service, vivienda-service, ...
```

El cuerpo del mensaje JSON es **idéntico al payload de la signal de hoy**.
Por eso esta documentación sirve también como schema de Kafka cuando
llegue el momento.

---

## Versionado

Cualquier cambio al payload pasa por las siguientes reglas:

- **Agregar un campo nuevo:** OK siempre (los handlers existentes lo ignoran).
- **Renombrar un campo:** breaking change, requiere bump de versión.
- **Cambiar el tipo de un campo:** breaking change.
- **Quitar un campo:** breaking change.

Cuando sea inevitable un cambio breaking:

1. Marcar el evento como `complaint.created.v2` y publicar ambos por un
   tiempo (en monolito: dos signals en paralelo; en bus de eventos:
   dos topics).
2. Migrar consumers uno a uno.
3. Apagar `v1`.

---

## Histórico

| Versión | Fecha | Cambios |
|---|---|---|
| v0 | 2026-04 | Pre-V2: payload contenía `Point` y `datetime` (no serializable) |
| v1 | 2026-04-28 | V2.1 — payload primitivo con `location_wkt`/`location_lat`/`location_lng` y `created_at` ISO. Agregado `section_slug` y `aspect_slug` |
