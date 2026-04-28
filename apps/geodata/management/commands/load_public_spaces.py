"""
Management command: load_public_spaces
Carga espacios públicos del POT Popayán a geodata.PublicSpace.

Fuentes (5 shapefiles, ~313 polígonos totales):
  U19_ESPACIO_PUBLICO1.shp  (2 polígonos)
  U19_ESPACIO_PUBLICO2.shp  (11 polígonos — parques urbanos)
  U19_ESPACIO_PUBLICO3.shp  (96 polígonos con NOMBRE real)
  U19_ESPACIO_PUBLICO5.shp  (72 polígonos — rondas de ríos, corredores)
  SEPARADOR.shp             (132 polígonos — separadores viales)

CRS original: PCS_CAUCA_POPAYAN
CRS destino:  EPSG:4326 (WGS84)
Áreas calculadas en EPSG:3116 (Colombia Oeste — metros reales)

external_id se genera por rango según la fuente:
  EP1: 10001+   EP2: 20001+   EP3: 30001+
  EP5: 50001+   SEP: 90001+

Uso:
    python manage.py load_public_spaces
    python manage.py load_public_spaces --clear
"""
from pathlib import Path
from decimal import Decimal

from django.contrib.gis.geos import GEOSGeometry
from django.core.management.base import BaseCommand

from apps.geodata.models import PublicSpace

BASE_SHAPEFILES = (
    Path(__file__).resolve().parents[4]
    / 'guayacanes_docs'
    / 'SHAPESPOT'
    / 'SHAPES POT'
)

# (relative_path, id_offset, space_type, name_base, source_layer)
SOURCES = [
    ('U-19 ESPACIO PUBLICO/U19_ESPACIO_PUBLICO1.shp', 10000, 'other',        'Espacio público',  'U19_EP1'),
    ('U-19 ESPACIO PUBLICO/U19_ESPACIO_PUBLICO2.shp', 20000, 'park',         'Parque',           'U19_EP2'),
    ('U-19 ESPACIO PUBLICO/U19_ESPACIO_PUBLICO3.shp', 30000, 'node',         'Nodo',             'U19_EP3'),
    ('U-19 ESPACIO PUBLICO/U19_ESPACIO_PUBLICO5.shp', 50000, 'corridor',     'Corredor verde',   'U19_EP5'),
    ('U1_POPAYAN BASE/SEPARADOR.shp',                 90000, 'road_divider', 'Separador',        'SEPARADOR'),
]


class Command(BaseCommand):
    help = 'Carga espacios públicos combinando 5 shapefiles del POT Popayán.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Elimina todos los espacios públicos antes de cargar',
        )

    def handle(self, *args, **options):
        try:
            import geopandas as gpd
        except ImportError:
            self.stderr.write(self.style.ERROR(
                'geopandas no está instalado. Ejecuta: uv add geopandas'
            ))
            return

        if options['clear']:
            count = PublicSpace.objects.count()
            PublicSpace.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                f'Eliminados {count} espacios públicos existentes.'
            ))

        total_created = 0
        total_updated = 0
        total_skipped = 0

        for relative_path, id_offset, space_type, name_base, source_layer in SOURCES:
            shapefile = BASE_SHAPEFILES / relative_path
            if not shapefile.exists():
                self.stderr.write(self.style.WARNING(
                    f'Shapefile no encontrado, saltando: {shapefile}'
                ))
                continue

            self.stdout.write(f'\nLeyendo: {relative_path}')
            gdf = gpd.read_file(shapefile)
            self.stdout.write(f'  Features: {len(gdf)} — CRS: {gdf.crs.name if gdf.crs else "?"}')

            gdf_4326 = gdf.to_crs(epsg=4326)
            gdf_3116 = gdf.to_crs(epsg=3116)

            created = 0
            updated = 0
            skipped = 0

            for i, (idx, row) in enumerate(gdf_4326.iterrows(), start=1):
                geom_wgs = row.geometry
                if geom_wgs is None or geom_wgs.is_empty:
                    skipped += 1
                    continue

                if geom_wgs.geom_type == 'Polygon':
                    from shapely.geometry import MultiPolygon as ShapelyMP
                    geom_wgs = ShapelyMP([geom_wgs])
                elif geom_wgs.geom_type != 'MultiPolygon':
                    skipped += 1
                    continue

                geom = GEOSGeometry(geom_wgs.wkt, srid=4326)

                try:
                    area = Decimal(str(round(gdf_3116.iloc[i - 1].geometry.area, 2)))
                except Exception:
                    area = None

                name = None
                for candidate in ('NOMBRE', 'CATEGORIA'):
                    if candidate in row and row[candidate]:
                        name = str(row[candidate]).strip()
                        break
                if not name:
                    name = f'{name_base} {i:03d}'

                external_id = id_offset + i

                _, is_new = PublicSpace.objects.update_or_create(
                    external_id=external_id,
                    defaults={
                        'name':         name[:300],
                        'space_type':   space_type,
                        'area_sqm':     area,
                        'source_layer': source_layer,
                        'geom':         geom,
                        'active':       True,
                    },
                )
                if is_new:
                    created += 1
                else:
                    updated += 1

            self.stdout.write(
                f'  → {created} creados, {updated} actualizados, {skipped} saltados'
            )
            total_created += created
            total_updated += updated
            total_skipped += skipped

        self.stdout.write(self.style.SUCCESS(
            f'\nListo. Total: {total_created} creados, '
            f'{total_updated} actualizados, {total_skipped} saltados.'
        ))
        self.stdout.write(
            f'Espacios públicos en BD: {PublicSpace.objects.count()}'
        )
