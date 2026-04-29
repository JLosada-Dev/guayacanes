"""
Management command: seed_complaints
Genera denuncias de prueba para demos y desarrollo.

Crea ~15 denuncias cubriendo los casos clave:
- Barrido dentro de horario → alerta sin violation
- Barrido fuera de horario → alerta con violation
- Zonas verdes cerca de áreas registradas → alerta
- Sin GPS (fallback centroide de comuna) → confidence=low
- En zonas sin cobertura → sin alerta

Las denuncias disparan el signal post_save que ejecuta el pipeline SLA.

Uso:
    python manage.py seed_complaints
    python manage.py seed_complaints --clear
"""
from datetime import datetime, timedelta

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import Commune
from apps.veeduria.models import Complaint, SLAAlert, MetricByCommune
from apps.infra_servicios_publicos_urbaser.models import (
    Service,
    Aspect,
    CuttingSchedule,
    GreenZoneAssignment,
)


# Coordenadas reales tomadas de microrutas de barrido y zonas verdes
# cargadas en la BD (ver `shell` para verificar).
COMPLAINTS_FIXTURE = [
    # ── Barrido cerca de microrutas activas ───────────────────────────────
    {
        'service_slug': 'sweeping-cleaning',
        'aspect_slug':  'frequency',
        'lat': 2.467533, 'lng': -76.589649,
        'hour': 14,  # fuera de horario (macroruta 611: 05:00)
        'commune_number': 4,
        'description': 'No pasaron a barrer esta semana en la carrera principal.',
    },
    {
        'service_slug': 'sweeping-cleaning',
        'aspect_slug':  'cleanliness',
        'lat': 2.468310, 'lng': -76.557983,
        'hour': 6,  # dentro de horario (macroruta 611: 05:00+)
        'commune_number': 3,
        'description': 'Limpieza deficiente, quedaron residuos.',
    },
    {
        'service_slug': 'sweeping-cleaning',
        'aspect_slug':  'bins',
        'lat': 2.468395, 'lng': -76.558244,
        'hour': 20,  # fuera de horario
        'commune_number': 3,
        'description': 'Cestas de basura desbordadas.',
    },
    {
        'service_slug': 'sweeping-cleaning',
        'aspect_slug':  'sand-residue',
        'lat': 2.468465, 'lng': -76.558385,
        'hour': 10,  # fuera de horario
        'commune_number': 3,
        'description': 'Arenilla sin recoger después del barrido.',
    },

    # ── Zonas verdes con alerta ───────────────────────────────────────────
    {
        'service_slug': 'green-zones',
        'aspect_slug':  'cutting-not-done',
        'lat': 2.483932, 'lng': -76.568401,  # cerca de BELLO HORIZONTE
        'hour': 9,
        'commune_number': 2,
        'description': 'Césped sin cortar desde hace más de 2 semanas.',
    },
    {
        'service_slug': 'green-zones',
        'aspect_slug':  'frequency-missed',
        'lat': 2.446903, 'lng': -76.602745,  # cerca de BOLIVAR
        'hour': 11,
        'commune_number': 4,
        'description': 'La frecuencia de corte no se está cumpliendo.',
    },
    {
        'service_slug': 'green-zones',
        'aspect_slug':  'pruning-waste-left',
        'lat': 2.463392, 'lng': -76.579693,  # cerca de CAMPESTRE
        'hour': 15,
        'commune_number': 5,
        'description': 'Residuos de poda abandonados por 3 días.',
    },
    {
        'service_slug': 'green-zones',
        'aspect_slug':  'area-deteriorated',
        'lat': 2.440186, 'lng': -76.606602,  # cerca de CENTRO URBANO
        'hour': 17,
        'commune_number': 4,
        'description': 'Zona verde deteriorada, maleza alta.',
    },

    # ── Fallback centroide (sin GPS) ──────────────────────────────────────
    {
        'service_slug': 'sweeping-cleaning',
        'aspect_slug':  'quality',
        'lat': None, 'lng': None,
        'hour': 8,
        'commune_number': 1,
        'description': 'El barrido se hace muy rápido y de mala calidad.',
    },
    {
        'service_slug': 'green-zones',
        'aspect_slug':  'cutting-not-done',
        'lat': None, 'lng': None,
        'hour': 12,
        'commune_number': 6,
        'description': 'Parque sin mantenimiento desde inicio de mes.',
    },
    {
        'service_slug': 'sweeping-cleaning',
        'aspect_slug':  'frequency',
        'lat': None, 'lng': None,
        'hour': 16,
        'commune_number': 8,
        'description': 'Pasan una vez al mes en este sector.',
    },

    # ── Más casos de barrido ──────────────────────────────────────────────
    {
        'service_slug': 'sweeping-cleaning',
        'aspect_slug':  'weed-removal',
        'lat': 2.468595, 'lng': -76.558712,
        'hour': 18,
        'commune_number': 3,
        'description': 'Desmoñe pendiente desde hace semanas.',
    },
    {
        'service_slug': 'sweeping-cleaning',
        'aspect_slug':  'scope',
        'lat': 2.451114, 'lng': -76.598008,
        'hour': 7,
        'commune_number': 4,
        'description': 'El barrido no cubre toda la zona contratada.',
    },

    # ── Zonas verdes con programación vencida (para violation directa) ────
    {
        'service_slug': 'green-zones',
        'aspect_slug':  'cutting-not-done',
        'lat': 2.463392, 'lng': -76.579693,  # CAMPESTRE
        'hour': 10,
        'commune_number': 5,
        'description': 'Programado el mes pasado, nunca ejecutado.',
        'overdue_schedule': True,  # flag especial
    },
]


class Command(BaseCommand):
    help = 'Crea denuncias de prueba para demo y desarrollo.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Elimina denuncias, alertas y métricas existentes.',
        )

    def handle(self, *args, **options):
        if options['clear']:
            c = Complaint.objects.count()
            a = SLAAlert.objects.count()
            m = MetricByCommune.objects.count()
            Complaint.objects.all().delete()
            SLAAlert.objects.all().delete()
            MetricByCommune.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                f'Eliminadas: {c} denuncias, {a} alertas, {m} métricas.'
            ))

        # Cachear servicios y aspectos por slug
        services = {s.slug: s for s in Service.objects.all()}
        aspects  = {(a.service.slug, a.slug): a for a in Aspect.objects.select_related('service')}
        communes = {c.number: c for c in Commune.objects.all()}

        # Crear un CuttingSchedule vencido para generar violation directa
        self._create_overdue_schedule()

        created     = 0
        with_alerts = 0

        for i, fx in enumerate(COMPLAINTS_FIXTURE, start=1):
            service = services.get(fx['service_slug'])
            aspect  = aspects.get((fx['service_slug'], fx['aspect_slug']))
            commune = communes.get(fx['commune_number'])

            if not (service and aspect and commune):
                self.stderr.write(
                    f'  [{i}] SKIP — catálogo incompleto para {fx}'
                )
                continue

            # Determinar location y source
            if fx['lat'] is not None:
                location = Point(fx['lng'], fx['lat'], srid=4326)
                location_source = 'gps'
            else:
                location = commune.geom.centroid
                location_source = 'centroid'

            # Timestamp con hora específica para triggerar violations en barrido
            now = timezone.now()
            created_at = now.replace(
                hour=fx['hour'], minute=0, second=0, microsecond=0
            ) - timedelta(days=i % 5)

            complaint = Complaint(
                section_slug       = 'urbaser',
                section_name       = 'Urbaser S.A. E.S.P.',
                service_slug       = service.slug,
                service_name       = service.name,
                aspect_slug        = aspect.slug,
                aspect_description = aspect.description,
                commune_id         = commune.id,
                commune_name       = commune.name,
                is_rural           = False,
                location           = location,
                location_source   = location_source,
                description        = fx['description'],
                status             = 'received',
            )
            complaint.save()
            complaint.created_at = created_at
            Complaint.objects.filter(pk=complaint.pk).update(created_at=created_at)

            alert_count = SLAAlert.objects.filter(complaint_id=complaint.id).count()
            if alert_count:
                with_alerts += 1

            self.stdout.write(
                f'  [{i:2d}] {service.slug:20} '
                f'({location.y:.4f}, {location.x:.4f}) '
                f'source={location_source:8} '
                f'alerts={alert_count}'
            )
            created += 1

        # Resumen final
        total_complaints = Complaint.objects.count()
        total_alerts     = SLAAlert.objects.count()
        total_violations = SLAAlert.objects.filter(violation=True).count()
        total_metrics    = MetricByCommune.objects.count()

        self.stdout.write(self.style.SUCCESS(
            f'\n{created} denuncias creadas ({with_alerts} con alertas generadas).'
        ))
        self.stdout.write(
            f'Totales en BD: {total_complaints} denuncias · '
            f'{total_alerts} alertas ({total_violations} violations) · '
            f'{total_metrics} métricas'
        )

    def _create_overdue_schedule(self):
        """Crea una CuttingSchedule vencida en zona CAMPESTRE para triggerar violation directa."""
        try:
            assignment = GreenZoneAssignment.objects.filter(
                public_space_name__icontains='CAMPESTRE'
            ).first()
            if not assignment:
                return
            past = timezone.now().date() - timedelta(days=20)
            CuttingSchedule.objects.get_or_create(
                assignment=assignment,
                scheduled_date=past,
                defaults={
                    'month':    past.month,
                    'year':     past.year,
                    'executed': False,
                },
            )
            self.stdout.write(
                f'  [schedule] Vencido creado para zona {assignment.public_space_name}'
            )
        except Exception as e:
            self.stderr.write(f'  [schedule] error: {e}')
