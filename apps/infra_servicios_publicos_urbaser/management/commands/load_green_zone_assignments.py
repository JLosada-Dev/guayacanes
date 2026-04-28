"""
Management command: load_green_zone_assignments
Crea una GreenZoneAssignment por cada PublicSpace cargado, modelando
la responsabilidad operativa de Urbaser sobre cada polígono del POT.

Asume que load_public_spaces ya corrió. Si no encuentra espacios,
falla con un mensaje claro.

external_id (ID Urbaser) inicialmente reutiliza el external_id del
PublicSpace. Cuando se cruce con el cronograma PDF de Urbaser se
podrá reemplazar por el ID real del cronograma.

cycle_days = 11 por defecto (PPS 2024).

Uso:
    python manage.py load_green_zone_assignments
    python manage.py load_green_zone_assignments --clear
"""
from django.core.management.base import BaseCommand

from apps.geodata.models import PublicSpace
from apps.infra_servicios_publicos_urbaser.models import GreenZoneAssignment


class Command(BaseCommand):
    help = 'Crea una GreenZoneAssignment por cada PublicSpace cargado.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Elimina todas las assignments antes de cargar',
        )

    def handle(self, *args, **options):
        if options['clear']:
            count = GreenZoneAssignment.objects.count()
            GreenZoneAssignment.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                f'Eliminadas {count} assignments existentes.'
            ))

        spaces = PublicSpace.objects.filter(active=True).order_by('external_id')
        if not spaces.exists():
            self.stderr.write(self.style.ERROR(
                'No hay PublicSpace cargados. Ejecuta primero: '
                'python manage.py load_public_spaces'
            ))
            return

        created = 0
        updated = 0

        for space in spaces:
            _, is_new = GreenZoneAssignment.objects.update_or_create(
                external_id=space.external_id,
                defaults={
                    'public_space_id':   space.id,
                    'public_space_name': space.name[:300],
                    'cycle_days':        11,
                    'active':            True,
                },
            )
            if is_new:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nListo. {created} assignments creadas, {updated} actualizadas.'
        ))
        self.stdout.write(
            f'Assignments en BD: {GreenZoneAssignment.objects.count()}'
        )
