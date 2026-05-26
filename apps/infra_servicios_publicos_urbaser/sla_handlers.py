"""
SLA handlers de Urbaser.
Conectados a veeduria.signals.complaint_created desde apps.py: ready().
Filtran por service_slug y solo procesan los servicios bajo contrato Urbaser.

Lógica:
  sweeping-cleaning:
    ST_DWithin(complaint.location, urbaser_sweeping_microroute.geom, D(m=50))
    + hora denuncia fuera de ventana horaria de la macroruta
    → violation=True

  green-zones:
    ST_DWithin(complaint.location, geodata_public_space.geom, D(m=30))
    + assignment activa + days_since_last_intervention > cycle_days
    → violation=True
    + schedule.executed=False con fecha pasada → violation directa
"""
from datetime import datetime

from django.utils import timezone
from django.contrib.gis.db.models.functions import Transform
from django.contrib.gis.geos import Point

from apps.geodata.models import PublicSpace
from apps.veeduria.models import SLAAlert
from apps.veeduria.metrics import recalculate_for

from .models import (
    SweepingMicroRoute,
    GreenZoneAssignment,
    CuttingSchedule,
)


URBASER_SLUGS = {'sweeping-cleaning', 'green-zones'}

CONFIDENCE_MAP = {
    'gps':      'high',
    'manual':   'medium',
    'centroid': 'low',
}


def handle_complaint(sender, service_slug, **kwargs):
    """
    Entry point conectado a veeduria.complaint_created.
    Filtra por slug y delega al procesador correspondiente.

    El payload del evento es solo primitivos (lat, lng, ISO timestamp).
    Aquí reconstruimos los objetos GeoDjango para hacer las queries.
    """
    if service_slug not in URBASER_SLUGS:
        return

    confidence = CONFIDENCE_MAP.get(kwargs.get('location_source'), 'low')
    commune_id = kwargs.get('commune_id')

    location = Point(
        kwargs['location_lng'],
        kwargs['location_lat'],
        srid=4326,
    )

    if service_slug == 'sweeping-cleaning':
        created_at = datetime.fromisoformat(kwargs['created_at'])
        _process_sweeping(
            complaint_id = kwargs['complaint_id'],
            location     = location,
            created_at   = created_at,
            confidence   = confidence,
        )
    elif service_slug == 'green-zones':
        _process_green_zones(
            complaint_id = kwargs['complaint_id'],
            location     = location,
            confidence   = confidence,
        )

    recalculate_for(commune_id, service_slug)


def _process_sweeping(complaint_id, location, created_at, confidence):
    """
    Cruce SLA para barrido.
    Transforma a EPSG:3116 (Colombia Oeste metros) para medir en metros reales.
    """
    location_transformed = location.transform(3116, clone=True)

    nearby = SweepingMicroRoute.objects.filter(
        active=True,
        geom__isnull=False,
    ).annotate(
        geom_m=Transform('geom', 3116)
    ).filter(
        geom_m__dwithin=(location_transformed, 50)
    ).select_related('macroroute')

    if not nearby.exists():
        return

    complaint_hour = created_at.hour

    for microroute in nearby:
        macro     = microroute.macroroute
        violation = False

        if macro.start_time and macro.end_time:
            start_hour = macro.start_time.hour
            end_hour   = macro.end_time.hour

            if start_hour <= end_hour:
                in_window = start_hour <= complaint_hour <= end_hour
            else:
                # Ventana que cruza medianoche (ej: 19:00-03:00)
                in_window = complaint_hour >= start_hour or complaint_hour <= end_hour

            violation = not in_window
        elif macro.start_time:
            # Sin end_time definido — fallback conservador: ventana de 8h
            start_hour = macro.start_time.hour
            end_hour   = (start_hour + 8) % 24
            if start_hour <= end_hour:
                in_window = start_hour <= complaint_hour <= end_hour
            else:
                in_window = complaint_hour >= start_hour or complaint_hour <= end_hour
            violation = not in_window

        geom_m   = microroute.geom.transform(3116, clone=True)
        distance = location_transformed.distance(geom_m)

        SLAAlert.objects.create(
            complaint_id    = complaint_id,
            service_slug    = 'sweeping-cleaning',
            route_type      = 'urbaser.sweeping_microroute',
            route_id        = microroute.id,
            route_label     = macro.code,
            violation       = violation,
            distance_meters = round(distance, 2),
            confidence      = confidence,
            extra_data      = {'urbaser_macroroute_code': macro.code},
        )


def _process_green_zones(complaint_id, location, confidence):
    """
    Cruce SLA para zonas verdes.
    Cruce espacial contra geodata.PublicSpace; solo se evalúa SLA para
    los espacios con una GreenZoneAssignment activa (responsabilidad
    operativa de Urbaser).
    """
    location_transformed = location.transform(3116, clone=True)

    nearby_spaces = PublicSpace.objects.filter(
        active=True,
        geom__isnull=False,
    ).annotate(
        geom_m=Transform('geom', 3116)
    ).filter(
        geom_m__dwithin=(location_transformed, 30)
    )

    if not nearby_spaces.exists():
        return

    today = timezone.now().date()

    space_ids   = list(nearby_spaces.values_list('id', flat=True))
    assignments = {
        a.public_space_id: a
        for a in GreenZoneAssignment.objects.filter(
            public_space_id__in=space_ids,
            active=True,
        )
    }

    for space in nearby_spaces:
        assignment = assignments.get(space.id)
        if assignment is None:
            continue  # espacio sin responsabilidad Urbaser, ignorar

        days_since = assignment.days_since_last_intervention()
        violation  = False

        if days_since is None:
            overdue = CuttingSchedule.objects.filter(
                assignment=assignment,
                scheduled_date__lt=today,
                executed=False,
            ).exists()
            violation = overdue
        else:
            violation = days_since > assignment.cycle_days

        SLAAlert.objects.create(
            complaint_id    = complaint_id,
            service_slug    = 'green-zones',
            route_type      = 'urbaser.green_zone',
            route_id        = assignment.id,
            route_label     = '',
            violation       = violation,
            extra_int       = days_since,
            confidence      = confidence,
            extra_data      = {
                'urbaser_assignment_external_id': assignment.external_id,
                'urbaser_public_space_id':        assignment.public_space_id,
            },
        )
