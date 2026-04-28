"""
Receivers de auditoría SLA.
Escucha complaint_created y ejecuta el cruce PostGIS.

Flujo:
  complaint_created signal
    → determinar confianza por location_source
    → según service_slug ejecutar cruce correspondiente
    → crear SLAAlert(es)
    → recalcular CommuneMetric
"""
from django.utils import timezone
from django.contrib.gis.db.models.functions import Transform

from apps.geodata.models import PublicSpace

from .signals import complaint_created
from .models import (
    SweepingMicroRoute,
    GreenZoneAssignment,
    CuttingSchedule,
    SLAAlert,
    CommuneMetric,
)

CONFIDENCE_MAP = {
    'gps':      'high',
    'manual':   'medium',
    'centroid': 'low',
}


def _recalculate_commune_metric(commune_id, service_slug):
    """
    Recalcula CommuneMetric para el mes actual.
    Llamada síncronamente tras crear cada SLAAlert (Fase 1).
    """
    if not commune_id:
        return

    today  = timezone.now().date()
    period = today.replace(day=1)

    alerts = SLAAlert.objects.filter(
        service_slug=service_slug,
    )

    from .models import Complaint
    complaints_ids = list(
        Complaint.objects.filter(
            commune_id=commune_id,
            service_slug=service_slug,
            created_at__year=today.year,
            created_at__month=today.month,
        ).values_list('id', flat=True)
    )

    total_complaints  = len(complaints_ids)
    relevant_alerts   = alerts.filter(complaint_id__in=complaints_ids)
    total_alerts      = relevant_alerts.count()
    total_violations  = relevant_alerts.filter(violation=True).count()
    violation_rate    = (
        total_violations / total_alerts if total_alerts > 0 else 0.0
    )

    from apps.core.models import Commune
    try:
        commune_name = Commune.objects.get(id=commune_id).name
    except Commune.DoesNotExist:
        commune_name = f'Comuna {commune_id}'

    CommuneMetric.objects.update_or_create(
        commune_id=commune_id,
        service_slug=service_slug,
        period=period,
        defaults={
            'commune_name':       commune_name,
            'total_complaints':   total_complaints,
            'total_alerts':       total_alerts,
            'total_violations':   total_violations,
            'violation_rate':     violation_rate,
        },
    )


def _process_sweeping(complaint_id, location, created_at, confidence, commune_id):
    """
    Cruce SLA para barrido.
    Transforma a EPSG:3116 (Colombia Oeste metros) para medir en metros reales.
    """
    # Transformar punto a sistema métrico colombiano
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
                # Ventana normal (ej: 06:00-14:00)
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

        # Distancia en metros reales
        geom_m   = microroute.geom.transform(3116, clone=True)
        distance = location_transformed.distance(geom_m)

        SLAAlert.objects.create(
            complaint_id    = complaint_id,
            service_slug    = 'sweeping-cleaning',
            route_type      = 'sweeping_microroute',
            route_id        = microroute.id,
            macroroute_code = macro.code,
            violation       = violation,
            distance_meters = round(distance, 2),
            confidence      = confidence,
        )

    _recalculate_commune_metric(commune_id, 'sweeping-cleaning')


def _process_green_zones(complaint_id, location, confidence, commune_id):
    """
    Cruce SLA para zonas verdes.
    Transforma a EPSG:3116 para medir en metros reales.

    El cruce espacial es contra geodata.PublicSpace (la geometría),
    pero solo se evalúa SLA para los espacios que tienen una
    GreenZoneAssignment activa (responsabilidad operativa de Urbaser).
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

    space_ids = list(nearby_spaces.values_list('id', flat=True))
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
            # Sin intervención registrada — verificar programación vencida
            overdue = CuttingSchedule.objects.filter(
                assignment=assignment,
                scheduled_date__lt=today,
                executed=False,
            ).exists()
            violation = overdue
        else:
            violation = days_since > assignment.cycle_days

        SLAAlert.objects.create(
            complaint_id          = complaint_id,
            service_slug          = 'green-zones',
            route_type            = 'green_zone',
            route_id              = assignment.id,
            macroroute_code       = '',
            violation             = violation,
            days_since_intervention = days_since,
            confidence            = confidence,
        )

    _recalculate_commune_metric(commune_id, 'green-zones')


def handle_complaint_created(
    sender, complaint_id, service_slug,
    location, created_at, location_source,
    commune_id, **kwargs
):
    """
    Entry point principal del módulo de auditoría.
    Recibe la signal y delega al procesador correspondiente.
    """
    confidence = CONFIDENCE_MAP.get(location_source, 'low')

    if service_slug == 'sweeping-cleaning':
        _process_sweeping(
            complaint_id, location, created_at, confidence, commune_id
        )
    elif service_slug == 'green-zones':
        _process_green_zones(
            complaint_id, location, confidence, commune_id
        )


# Conectar el receiver a la signal
complaint_created.connect(handle_complaint_created)
