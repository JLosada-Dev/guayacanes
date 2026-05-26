# Section + Service Provider Registry

**Fecha:** 2026-04-28
**Rama:** `refactor/section-registry` (sobre `refactor/arquitectura-multiapp`)
**Estado:** propuesta aprobada — implementación en curso

---

## 1. Por qué

Tras V2 todavía hay un acoplamiento residual: `core.Service` y `core.Aspect`
viven en el catálogo central. Eso significa que cada nueva sección de la
Alcaldía (vivienda, cultura, urbaser-facturación, acueducto, …) tendría
que añadir filas a una tabla compartida y, eventualmente, querría
columnas propias que no caben en un esquema único.

La meta es que **cada sección sea dueña de su catálogo** — sus
servicios, sus aspectos, su contenido editorial — y que el sistema
descubra los servicios disponibles vía un patrón de registro,
exactamente como hoy se descubren los handlers SLA.

Esto prepara también el camino a microservicios sin reescritura: cuando
cada sección sea su propio servicio, el registry deja de ser
in-process y se vuelve service discovery + API gateway.

---

## 2. Modelo final

```
core/
  Section                  ← catálogo administrativo de secciones
                             (Urbaser, Vivienda, Cultura, …)
  registry.py              ← Protocol ServiceProvider + registro global

infra_servicios_publicos_urbaser/
  Service                  ← regresan a urbaser
  Aspect
  ServiceContent / AspectContent
  registry.py              ← UrbaserServiceProvider
  apps.ready()             ← registra el provider y conecta el handler SLA

infra_servicios_publicos_vivienda/   (futuro)
  Service / Aspect propios
  registry.py              ← ViviendaServiceProvider
  apps.ready()             ← registra
```

### Tablas resultantes

| Tabla | App | Cambio |
|---|---|---|
| `core_section` | core | NUEVA |
| `core_commune`, `core_neighborhood` | core | sin cambios |
| `urbaser_service` | urbaser | NUEVA (era `core_service`) |
| `urbaser_aspect` | urbaser | NUEVA (era `core_aspect`) |
| `urbaser_service_content` | urbaser | sin cambios |
| `urbaser_aspect_content` | urbaser | sin cambios |
| `vee_complaint` | veeduria | + `section_slug`, `section_name` |
| el resto | — | sin cambios |

---

## 3. Section

```python
core.Section
  code         CharField(20) UNIQUE      # identificador estable: 'urbaser'
  name         CharField(100)            # 'Urbaser S.A. E.S.P.'
  slug         SlugField UNIQUE          # mismo valor que code
  description  TextField blank
  app_label    CharField(100) blank      # ayuda al registry de auto-discovery
  active       BooleanField default=True
  order        PositiveSmallIntegerField default=0
```

**Tabla:** `core_section`

Section es lo único realmente "de la Alcaldía" en este eje. Es información
cross-cutting: el portal ciudadano la lee para agrupar/filtrar servicios,
el admin de la Alcaldía la edita, cualquier futura app la consulta.

---

## 4. Registry — Protocol + funciones globales

```python
# apps/core/registry.py
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ServiceInfo:
    section_slug: str
    section_name: str
    slug:         str
    name:         str
    description:  str
    active:       bool
    order:        int
    content:      dict | None   # icon, summary, full_description, ...


@dataclass(frozen=True)
class AspectInfo:
    section_slug: str
    service_slug: str
    slug:         str
    description:  str
    active:       bool
    content:      dict | None   # icon, what_is, how_to_evidence, ...


class ServiceProvider(Protocol):
    section_slug: str

    def get_services(self) -> list[ServiceInfo]: ...
    def get_aspects(self, service_slug: str) -> list[AspectInfo]: ...


_providers: dict[str, ServiceProvider] = {}

def register(provider: ServiceProvider) -> None: ...
def all_providers() -> list[ServiceProvider]: ...
def get_provider(section_slug: str) -> ServiceProvider | None: ...
```

Cada app de sección tiene su propio archivo `registry.py` que implementa
el Protocol y se registra desde `AppConfig.ready()`. El mismo método
`ready()` ya conecta el SLA handler — ahora también registra el provider.

---

## 5. Endpoints agregadores

`/core/services/` y `/core/aspects/` ya no leen de tablas en core sino
del registry. Iteran los providers registrados y devuelven el catálogo
unificado, opcionalmente filtrado por `?section=<slug>`.

**Shape de respuesta `GET /core/services/`** — agrega `section_slug` y
`section_name` al objeto Service, todo lo demás queda igual:

```json
[
  {
    "slug": "sweeping-cleaning",
    "name": "Barrido y Limpieza",
    "description": "...",
    "active": true,
    "order": 1,
    "section_slug": "urbaser",
    "section_name": "Urbaser S.A. E.S.P.",
    "content": {
      "icon": "trash-2",
      "summary": "...",
      "full_description": "...",
      "frequency": "...",
      "citizen_rights": "..."
    }
  }
]
```

`section_name` viaja como snapshot para que el frontend lo muestre sin
hacer un fetch extra a `/core/sections/`.

**Nuevo endpoint:** `GET /core/sections/` — listado de secciones activas
ordenadas por `order`. Útil para portal ciudadano si se quiere mostrar
agrupado por sección.

---

## 6. Snapshot en Complaint

`vee_complaint` agrega:

```python
section_slug  CharField(20) blank
section_name  CharField(100) blank
```

El serializer los deriva de `service.section` automáticamente, así el
frontend no los manda. Una denuncia queda autocontenida: aunque la
sección se renombre o desaparezca, la denuncia sigue siendo legible.

---

## 7. Evento `complaint_created` serializable

Para preparar microservicios, el payload del evento usa solo primitivos
(strings, ints, floats). En lugar de pasar un `Point` GeoDjango se
pasan `location_wkt`, `location_lat`, `location_lng`. El timestamp viaja
en formato ISO 8601.

```python
complaint_created.send(
    sender         = Complaint,
    complaint_id   = instance.id,
    section_slug   = instance.section_slug,    # NUEVO
    service_slug   = instance.service_slug,
    aspect_slug    = instance.aspect_slug,
    location_wkt   = instance.location.wkt,
    location_lat   = instance.location.y,
    location_lng   = instance.location.x,
    created_at     = instance.created_at.isoformat(),
    location_source= instance.location_source,
    commune_id     = instance.commune_id,
)
```

El handler de Urbaser reconstruye el `Point` desde `lat`/`lng` cuando lo
necesita para los `ST_DWithin`.

El día que migremos a Kafka, este payload va `json.dumps()` directo y no
se toca código de aplicación — solo la capa de transporte.

---

## 8. Camino a microservicios

Resumen de la equivalencia entre el monolito modular V2.1 (con esto) y
una arquitectura de microservicios futura:

| Concepto | Monolito (hoy) | Microservicios (futuro) |
|---|---|---|
| `core.Section` | tabla en core | catalog-service |
| `urbaser.Service`/`Aspect` | tablas en urbaser | urbaser-service expone `/services/` |
| Registry de providers | dict in-process | service discovery (Consul/DNS) |
| Endpoint agregador | itera providers en proceso | API gateway que llama a cada servicio |
| Signal `complaint_created` | `Signal.send()` síncrono | mensaje JSON a Kafka/RabbitMQ |
| Soft FK `service_id` | IntegerField + snapshot | ID externo + snapshot (idéntico) |
| BD | Postgres con prefijos | Postgres por servicio |

Cada uno de estos pasos es **independiente y reversible**. Cuando llegue
el momento se migra una pieza a la vez (patrón Strangler Fig de Sam
Newman) sin reescribir el sistema.

---

## 9. Plan de commits

```
1. docs(refactor): add SECTION-REGISTRY.md design doc
2. feat(core): add Section model and global registry
3. refactor: move Service, Aspect and *Content from core to urbaser
4. feat(urbaser): implement UrbaserServiceProvider and register in ready()
5. refactor(core): rewrite /core/services and /core/aspects as registry aggregators
6. feat(core): expose /core/sections endpoint
7. feat(veeduria): snapshot section_slug and section_name on Complaint
8. refactor(veeduria): make complaint_created payload serializable
9. docs(veeduria): document event contract in EVENTS.md
10. chore: add Section fixture (urbaser active; rest inactive)
11. refactor: regenerate migrations for V2.1 schema
12. test(core): registry aggregator and Section model
13. test(veeduria): event payload primitives and section snapshot
```
