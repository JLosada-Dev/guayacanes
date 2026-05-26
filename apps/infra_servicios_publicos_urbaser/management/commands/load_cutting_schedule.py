"""
Management command: load_cutting_schedule
Carga el cronograma de cortes de césped desde los PDFs mensuales de Urbaser.

Fuente:
    guayacanes_docs/urbaser-servicios-pdf/zonas-verdes/
        cronograma-de-cesped-febrero-2026.pdf  (feb actual)
        ENERO-2026.pdf ... DICIEMBRE-2026.pdf  (inventario arbóreo, estructura diferente)

Estructura del PDF (febrero 2026):
    Columnas: ID | POLIGONO | AREA M² | FECHA
    Fecha formato: DD-MM-YYYY
    ~290 filas, 9 páginas

El matching GreenZoneAssignment ↔ PDF es por nombre (fuzzy match con
SequenceMatcher) usando el snapshot public_space_name de la assignment,
ya que external_id de la BD no corresponde al ID del PDF.

Uso:
    python manage.py load_cutting_schedule
    python manage.py load_cutting_schedule --clear
    python manage.py load_cutting_schedule --pdf /ruta/otro-cronograma.pdf
"""
import re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from unicodedata import normalize

from django.core.management.base import BaseCommand

from apps.infra_servicios_publicos_urbaser.models import (
    GreenZoneAssignment,
    CuttingSchedule,
)

DEFAULT_PDF = (
    Path(__file__).resolve().parents[4]
    / 'guayacanes_docs'
    / 'urbaser-servicios-pdf'
    / 'zonas-verdes'
    / 'cronograma-de-cesped-febrero-2026.pdf'
)

MATCH_THRESHOLD = 0.70  # similaridad mínima para aceptar el match
# Nota: con threshold más estricto (0.8+) solo matchea 11 zonas.
# A 0.70 se alcanzan ~37 matches con muy pocos falsos positivos.
# El límite estructural es que el PDF usa nombres de barrio y los shapefiles
# usan nombres de landmarks (parques, coliseos, centros). Sin shapefile de
# barrios no se puede mejorar más sin un crosswalk manual.


def _normalize(s: str) -> str:
    """Normaliza texto para fuzzy match: sin acentos, minúsculas, sin puntuación."""
    s = normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _best_match(pdf_name: str, zones_normalized: dict):
    """Encuentra la zona con mayor similaridad al nombre del PDF."""
    target = _normalize(pdf_name)
    if not target:
        return None, 0.0

    best_id    = None
    best_score = 0.0

    for zone_id, norm_name in zones_normalized.items():
        score = SequenceMatcher(None, target, norm_name).ratio()
        if score > best_score:
            best_score = score
            best_id    = zone_id

    return best_id, best_score


class Command(BaseCommand):
    help = 'Carga el cronograma de cortes de césped desde un PDF de Urbaser.'

    def add_arguments(self, parser):
        parser.add_argument('--pdf', default=str(DEFAULT_PDF))
        parser.add_argument('--clear', action='store_true')
        parser.add_argument('--verbose-match', action='store_true',
                            help='Muestra matches con bajo score')

    def handle(self, *args, **options):
        try:
            import pdfplumber
        except ImportError:
            self.stderr.write(self.style.ERROR(
                'pdfplumber no está instalado. Ejecuta: uv add pdfplumber'
            ))
            return

        pdf_path = Path(options['pdf'])
        if not pdf_path.exists():
            self.stderr.write(self.style.ERROR(f'PDF no encontrado: {pdf_path}'))
            return

        if options['clear']:
            count = CuttingSchedule.objects.count()
            CuttingSchedule.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                f'Eliminados {count} schedules existentes.'
            ))

        # Cachear assignments normalizadas para fuzzy match
        assignments = list(
            GreenZoneAssignment.objects.all().values('id', 'public_space_name')
        )
        zones_normalized = {
            a['id']: _normalize(a['public_space_name']) for a in assignments
        }
        self.stdout.write(f'Assignments en BD: {len(assignments)}')

        # Extraer filas del PDF
        self.stdout.write(f'\nLeyendo PDF: {pdf_path.name}')
        rows = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row and row[0] and row[0].strip().isdigit():
                            rows.append(row)

        self.stdout.write(f'Filas extraídas del PDF: {len(rows)}')

        # Procesar cada fila
        created   = 0
        skipped   = 0
        low_match = 0

        for row in rows:
            try:
                pdf_id     = int(row[0].strip())
                pdf_name   = (row[1] or '').strip()
                date_str   = (row[3] or '').strip() if len(row) > 3 else ''
            except (ValueError, IndexError):
                skipped += 1
                continue

            if not pdf_name or not date_str:
                skipped += 1
                continue

            # Parsear fecha DD-MM-YYYY
            try:
                scheduled = datetime.strptime(date_str, '%d-%m-%Y').date()
            except ValueError:
                skipped += 1
                continue

            # Fuzzy match
            assignment_id, score = _best_match(pdf_name, zones_normalized)
            if score < MATCH_THRESHOLD:
                low_match += 1
                if options['verbose_match']:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  NO MATCH ({score:.2f}): "{pdf_name}"'
                        )
                    )
                continue

            _, is_new = CuttingSchedule.objects.get_or_create(
                assignment_id=assignment_id,
                scheduled_date=scheduled,
                defaults={
                    'month':    scheduled.month,
                    'year':     scheduled.year,
                    'executed': False,
                },
            )
            if is_new:
                created += 1

        total = CuttingSchedule.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'\n{created} schedules creados.'
        ))
        self.stdout.write(
            f'Filas sin match (<{MATCH_THRESHOLD:.2f}): {low_match}  ·  '
            f'Filas inválidas: {skipped}  ·  '
            f'Total schedules en BD: {total}'
        )
