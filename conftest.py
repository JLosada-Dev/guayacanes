"""
Fixtures compartidos para todas las apps.
Provee el catálogo mínimo (Service, Aspect, Commune) y las rutas
operativas básicas que los tests de signals y handlers necesitan.
"""
from datetime import time

import pytest
from django.contrib.gis.geos import LineString, MultiPolygon, Point, Polygon


@pytest.fixture(autouse=True)
def _section(db):
    """
    Section 'urbaser' siempre disponible: el provider la consulta para
    enriquecer ServiceInfo.section_name.
    """
    from apps.core.models import Section
    Section.objects.update_or_create(
        slug='urbaser',
        defaults={
            'code': 'urbaser',
            'name': 'Urbaser S.A. E.S.P.',
            'active': True,
            'order': 1,
        },
    )


@pytest.fixture
def sweeping_service(db):
    from apps.infra_servicios_publicos_urbaser.models import Service, Aspect

    service = Service.objects.create(
        name='Barrido y Limpieza',
        slug='sweeping-cleaning',
        active=True,
        order=1,
    )
    Aspect.objects.create(
        service=service, slug='scope',
        description='Cobertura', active=True,
    )
    return service


@pytest.fixture
def green_zones_service(db):
    from apps.infra_servicios_publicos_urbaser.models import Service, Aspect

    service = Service.objects.create(
        name='Zonas Verdes',
        slug='green-zones',
        active=True,
        order=2,
    )
    Aspect.objects.create(
        service=service, slug='cutting-not-done',
        description='Sin corte', active=True,
    )
    return service


@pytest.fixture
def commune(db):
    from apps.core.models import Commune

    # Polígono pequeño alrededor de un punto en Popayán
    poly = Polygon((
        (-76.61, 2.46),
        (-76.59, 2.46),
        (-76.59, 2.48),
        (-76.61, 2.48),
        (-76.61, 2.46),
    ), srid=4326)
    return Commune.objects.create(
        number=1, name='Comuna 1',
        area_hectares=100, geom=poly,
    )


@pytest.fixture
def sweeping_macroroute(db):
    from apps.infra_servicios_publicos_urbaser.models import SweepingMacroRoute

    return SweepingMacroRoute.objects.create(
        code='B211', name='Test macroruta',
        zone_type='residential',
        days_text='Lu-Ju',
        start_time=time(6, 0),
        end_time=time(14, 0),
        active=True,
    )


@pytest.fixture
def sweeping_microroute(sweeping_macroroute):
    from apps.infra_servicios_publicos_urbaser.models import SweepingMicroRoute

    # LineString con dos puntos en Popayán, cerca de (-76.60, 2.47)
    line = LineString(
        (-76.6005, 2.4700),
        (-76.5995, 2.4700),
        srid=4326,
    )
    return SweepingMicroRoute.objects.create(
        macroroute=sweeping_macroroute,
        layer='VARIANT', active=True, geom=line,
    )


@pytest.fixture
def public_space_with_assignment(db):
    """
    PublicSpace + GreenZoneAssignment activa en un polígono cerca de
    (-76.60, 2.47). Sin intervenciones registradas.
    """
    from apps.geodata.models import PublicSpace
    from apps.infra_servicios_publicos_urbaser.models import GreenZoneAssignment

    poly = Polygon((
        (-76.6005, 2.4695),
        (-76.5995, 2.4695),
        (-76.5995, 2.4705),
        (-76.6005, 2.4705),
        (-76.6005, 2.4695),
    ), srid=4326)
    space = PublicSpace.objects.create(
        external_id=10001, name='Parque test',
        space_type='park', source_layer='U19_EP1',
        active=True, geom=MultiPolygon(poly, srid=4326),
    )
    assignment = GreenZoneAssignment.objects.create(
        public_space_id=space.id,
        public_space_name=space.name,
        external_id=10001,
        cycle_days=11,
        active=True,
    )
    return space, assignment


@pytest.fixture
def point_inside_route():
    """Punto a metros de la microruta y dentro del polígono del PublicSpace."""
    return Point(-76.6000, 2.4700, srid=4326)
