# Patrón de registro — handlers SLA por servicio

**Fecha:** 2026-04-28
**Propósito:** explicar cómo cada app de servicio público se conecta a `veeduria.complaint_created` y aporta su propia lógica SLA sin que veeduria sepa nada del dominio.

---

## 1. Por qué un patrón de registro

Veeduria es transversal. No puede saber:
- Que `sweeping-cleaning` se cruza con `urbaser_sweeping_microroute` a 50m.
- Que `green-zones` se cruza con `urbaser_green_zone_assignment` a 30m con `cycle_days`.
- Que el día de mañana `housing-license` se cruzará con `geodata_road` para detectar denuncias en zonas rurales sin licencia.

Si veeduria conociera esos cruces, cada servicio nuevo requeriría modificar veeduria. Eso es justamente lo que queremos evitar.

**Solución:** veeduria expone una signal pública (`complaint_created`) y cada app de servicio se registra escuchándola. Si la denuncia no es de su servicio, ignora.

---

## 2. Contrato de la signal

```python
# apps/veeduria/signals.py
from django.dispatch import Signal

complaint_created = Signal()
```

Argumentos enviados al receiver:

| Argumento | Tipo | Descripción |
|---|---|---|
| `sender` | `type[Complaint]` | Modelo que disparó la signal (siempre `Complaint`) |
| `complaint_id` | `int` | PK de la denuncia recién creada |
| `service_slug` | `str` | Slug del servicio (soft FK a `core.Service`) |
| `aspect_slug` | `str` | Slug del aspecto |
| `location` | `Point` | Coordenada SRID 4326 |
| `created_at` | `datetime` | Timestamp de creación con TZ Bogotá |
| `location_source` | `str` | `'gps'`, `'manual'` o `'centroid'` |
| `commune_id` | `int \| None` | Soft FK a `core.Commune` |

Veeduria emite la signal **una sola vez por denuncia** después del `save()`. Cada handler decide si le aplica.

---

## 3. Cómo se registra una app de servicio

### 3.1 Un módulo por servicio

```
apps/infra_servicios_publicos_urbaser/
  apps.py                    # AppConfig.ready() conecta los handlers
  sla_handlers.py            # las funciones receiver
```

### 3.2 `apps.py` con `ready()`

```python
# apps/infra_servicios_publicos_urbaser/apps.py
from django.apps import AppConfig


class InfraUrbaserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name              = 'apps.infra_servicios_publicos_urbaser'
    verbose_name      = 'Servicio público de aseo — Urbaser'

    def ready(self):
        from apps.veeduria.signals import complaint_created
        from . import sla_handlers

        complaint_created.connect(
            sla_handlers.handle_complaint,
            dispatch_uid='urbaser.handle_complaint',
        )
```

`dispatch_uid` evita doble registro si Django recarga el módulo.

### 3.3 `sla_handlers.py` con dispatch por slug

```python
# apps/infra_servicios_publicos_urbaser/sla_handlers.py
"""
Handler SLA de Urbaser.
Solo procesa denuncias cuyo service_slug le corresponde.
"""

URBASER_SLUGS = {'sweeping-cleaning', 'green-zones'}


def handle_complaint(sender, service_slug, **kwargs):
    if service_slug not in URBASER_SLUGS:
        return  # no es nuestro servicio, ignorar

    if service_slug == 'sweeping-cleaning':
        _process_sweeping(**kwargs)
    elif service_slug == 'green-zones':
        _process_green_zones(**kwargs)


def _process_sweeping(complaint_id, location, created_at, location_source, commune_id, **_):
    # Cruzar con urbaser_sweeping_microroute, calcular violation,
    # crear SLAAlert en veeduria.
    ...


def _process_green_zones(complaint_id, location, location_source, commune_id, **_):
    # Cruzar con geodata_public_space + urbaser_green_zone_assignment,
    # crear SLAAlert en veeduria.
    ...
```

Cada handler usa `veeduria.SLAAlert.objects.create(...)` con `service_slug`, `route_type`, `route_id`, etc.

### 3.4 Recalculo de métricas

Después de crear sus alertas, el handler invoca el recalculo (que vive en veeduria):

```python
from apps.veeduria.metrics import recalculate_for

def _process_sweeping(...):
    # ... crear alertas ...
    recalculate_for(commune_id=commune_id, service_slug='sweeping-cleaning')
```

`recalculate_for` actualiza `MetricByCommune` para `(commune, service_slug, mes_actual)`.

---

## 4. Cómo añadir un servicio nuevo (ej: vivienda)

1. Crear app `apps/infra_servicios_publicos_vivienda/`.
2. Definir `apps.py` con `ready()` que conecte `vivienda.sla_handlers.handle_complaint` a `veeduria.signals.complaint_created`.
3. En `sla_handlers.py`:
   ```python
   VIVIENDA_SLUGS = {'housing-license', 'illegal-construction'}

   def handle_complaint(sender, service_slug, **kwargs):
       if service_slug not in VIVIENDA_SLUGS:
           return
       _process_vivienda(**kwargs)
   ```
4. Cargar `Service` y `Aspect` con los slugs nuevos en `core` (fixture o admin).
5. Definir modelos propios (ej: `BuildingLicense`) en la app vivienda.
6. Registrar la app en `INSTALLED_APPS`.

Veeduria, core y geodata no se tocan.

---

## 5. Reglas

- **Nunca** import circular: el handler de un servicio importa de veeduria, nunca al revés.
- **Nunca** hard FK desde veeduria a un modelo de servicio.
- Cada handler debe **filtrar por su slug** al inicio. Si recibe una denuncia de otro servicio, retorna sin hacer nada.
- Cada handler usa `dispatch_uid` distinto al conectarse para evitar duplicados.
- Si un handler crea `N` alertas, todas deben ser para el mismo `complaint_id` y `service_slug`.

---

## 6. Tests

Para cada app de servicio:

1. **Test de aislamiento:** mandar una denuncia con un slug ajeno (`sender=Complaint, service_slug='unknown'`) y verificar que el handler no crea alertas.
2. **Test de cruce:** mandar una denuncia con coordenada conocida y verificar que se crean las alertas esperadas con `violation` correcto.
3. **Test de métricas:** verificar que después del handler, `MetricByCommune` para `(commune, service_slug, mes)` quedó actualizado.

---

## 7. Notas de extensibilidad

- Si en el futuro queremos handlers asíncronos (Celery), `complaint_created` puede emitirse hacia un task que despache a los listeners. La interfaz no cambia.
- Si hay servicios que comparten lógica de cruce (ej: dos servicios que cruzan con vías), refactorizar a una utilidad compartida en `geodata.spatial`. Cada handler la consume.
- `SLAAlert.extra_data` (JSONField) permite a cada servicio guardar metadatos sin migrar veeduria. Usar nombres prefijados (`urbaser_macroroute_code`, `vivienda_license_id`) para evitar choques.
