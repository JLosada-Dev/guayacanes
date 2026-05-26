"""Aggregated statistics for the staff portal.

Single-call payload to keep the frontend simple. Heavy queries run on demand;
if usage scales, move to materialized views or a periodic ETL.
"""

from datetime import timedelta

from django.db.models import Avg, Count, F, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStaff

from .models import Complaint, ComplaintStatusEvent

FINAL_STATUSES = ('resolved', 'rejected')


def _distribution(qs, field):
    return list(
        qs.values(field)
        .annotate(count=Count('id'))
        .order_by('-count')
    )


def _avg_resolution_days() -> float | None:
    """Average days between created_at and the latest event with to_status='resolved'."""
    resolved_events = (
        ComplaintStatusEvent.objects
        .filter(to_status='resolved')
        .values('complaint_id')
        .annotate(
            delta=F('created_at') - F('complaint__created_at'),
        )
    )
    deltas = [e['delta'] for e in resolved_events if e['delta']]
    if not deltas:
        return None
    total_seconds = sum(d.total_seconds() for d in deltas)
    return round(total_seconds / len(deltas) / 86400, 2)


def _monthly_series(months_back: int = 6):
    cutoff = timezone.now() - timedelta(days=30 * months_back)
    rows = (
        Complaint.objects
        .filter(created_at__gte=cutoff)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    return [{'month': r['month'].strftime('%Y-%m'), 'count': r['count']} for r in rows]


class StatisticsView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request):
        base_qs = Complaint.objects.all()
        total = base_qs.count()
        active = base_qs.exclude(status__in=FINAL_STATUSES).count()
        resolved = base_qs.filter(status='resolved').count()
        rejected = base_qs.filter(status='rejected').count()

        # KPIs principales
        resolution_rate = round((resolved / total) * 100, 1) if total else 0.0
        rejection_rate = round((rejected / total) * 100, 1) if total else 0.0
        avg_days = _avg_resolution_days()

        # Distribuciones
        by_status = _distribution(base_qs, 'status')
        by_severity = _distribution(base_qs, 'severity')
        by_service = _distribution(base_qs, 'service_slug')
        by_section = _distribution(base_qs, 'section_slug')
        by_location_source = _distribution(base_qs, 'location_source')

        # Rankings
        top_communes = list(
            base_qs.exclude(commune_id__isnull=True)
            .values('commune_id', 'commune_name')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
        top_aspects = list(
            base_qs.exclude(aspect_slug='')
            .values('aspect_slug', 'aspect_description', 'service_slug')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )

        # Evolución temporal
        monthly = _monthly_series()

        # Backlog: cuántas denuncias siguen en cada estado activo
        active_backlog = list(
            base_qs.exclude(status__in=FINAL_STATUSES)
            .values('status')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # Engagement de evidencia
        with_evidence = base_qs.annotate(ev_count=Count('evidence')).filter(ev_count__gt=0).count()
        evidence_rate = round((with_evidence / total) * 100, 1) if total else 0.0
        avg_evidence_per_complaint = round(
            base_qs.annotate(ev_count=Count('evidence')).aggregate(a=Avg('ev_count'))['a'] or 0,
            2,
        )

        # Actividad de gestión
        total_events = ComplaintStatusEvent.objects.count()
        events_last_30d = ComplaintStatusEvent.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()

        return Response({
            'kpis': {
                'total': total,
                'active': active,
                'resolved': resolved,
                'rejected': rejected,
                'resolution_rate_pct': resolution_rate,
                'rejection_rate_pct': rejection_rate,
                'avg_resolution_days': avg_days,
                'with_evidence_pct': evidence_rate,
                'avg_evidence_per_complaint': avg_evidence_per_complaint,
                'total_events': total_events,
                'events_last_30d': events_last_30d,
            },
            'distributions': {
                'by_status': by_status,
                'by_severity': by_severity,
                'by_service': by_service,
                'by_section': by_section,
                'by_location_source': by_location_source,
                'active_backlog': active_backlog,
            },
            'rankings': {
                'top_communes': top_communes,
                'top_aspects': top_aspects,
            },
            'series': {
                'monthly': monthly,
            },
        })
