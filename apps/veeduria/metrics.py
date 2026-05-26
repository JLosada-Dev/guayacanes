"""
Recalculo de MetricByCommune.

Cada handler de servicio debe llamar `recalculate_for(commune_id, service_slug)`
después de crear sus alertas para mantener el heatmap del dashboard fresco.
"""
from django.utils import timezone

from .models import Complaint, SLAAlert, MetricByCommune


def recalculate_for(commune_id, service_slug):
    """
    Recalcula MetricByCommune para el mes actual de una comuna y un servicio.
    Llamada síncronamente tras crear cada SLAAlert (Fase 1).
    En Fase 2 se mueve a tarea Celery asíncrona.
    """
    if not commune_id:
        return

    today  = timezone.now().date()
    period = today.replace(day=1)

    complaint_ids = list(
        Complaint.objects.filter(
            commune_id=commune_id,
            service_slug=service_slug,
            created_at__year=today.year,
            created_at__month=today.month,
        ).values_list('id', flat=True)
    )

    relevant_alerts  = SLAAlert.objects.filter(
        service_slug=service_slug,
        complaint_id__in=complaint_ids,
    )

    total_complaints = len(complaint_ids)
    total_alerts     = relevant_alerts.count()
    total_violations = relevant_alerts.filter(violation=True).count()
    violation_rate   = (
        total_violations / total_alerts if total_alerts > 0 else 0.0
    )

    from apps.core.models import Commune
    try:
        commune_name = Commune.objects.get(id=commune_id).name
    except Commune.DoesNotExist:
        commune_name = f'Comuna {commune_id}'

    MetricByCommune.objects.update_or_create(
        commune_id=commune_id,
        service_slug=service_slug,
        period=period,
        defaults={
            'commune_name':     commune_name,
            'total_complaints': total_complaints,
            'total_alerts':     total_alerts,
            'total_violations': total_violations,
            'violation_rate':   violation_rate,
        },
    )
