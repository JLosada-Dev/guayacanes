"""
Tests del ComplaintSerializer — validaciones de:
- neighborhood_id debe pertenecer a commune_id.
- address opcional aceptado tal cual.
- Snapshot de neighborhood_name y commune_name.
"""
import pytest

from apps.core.models import Neighborhood
from apps.veeduria.serializers import ComplaintSerializer


@pytest.fixture
def neighborhoods_for_commune(commune, db):
    return Neighborhood.objects.bulk_create([
        Neighborhood(name='Centro',  commune=commune),
        Neighborhood(name='Pomona',  commune=commune),
    ])


@pytest.mark.django_db
def test_neighborhood_must_belong_to_commune(
    commune, sweeping_service, neighborhoods_for_commune,
):
    """Mandar un neighborhood_id que no pertenece a la comuna → 400."""
    from apps.core.models import Commune
    from django.contrib.gis.geos import Polygon

    poly = Polygon((
        (-76.61, 2.46), (-76.59, 2.46), (-76.59, 2.48),
        (-76.61, 2.48), (-76.61, 2.46),
    ), srid=4326)
    other_commune = Commune.objects.create(
        number=99, name='Comuna 99', area_hectares=1, geom=poly,
    )
    foreign_nb = Neighborhood.objects.create(
        name='Ajeno', commune=other_commune,
    )
    aspect = sweeping_service.aspects.first()

    payload = {
        'service_slug':    sweeping_service.slug,
        'aspect_slug':     aspect.slug,
        'commune_id':      commune.id,
        'neighborhood_id': foreign_nb.id,
        'latitude':        2.47,
        'longitude':       -76.60,
        'location_source': 'gps',
    }
    s = ComplaintSerializer(data=payload)
    assert s.is_valid() is False
    assert 'neighborhood_id' in s.errors


@pytest.mark.django_db
def test_neighborhood_snapshot_filled_when_valid(
    commune, sweeping_service, neighborhoods_for_commune,
):
    """Al pasar barrio válido, neighborhood_name se completa desde BD."""
    centro = next(n for n in neighborhoods_for_commune if n.name == 'Centro')
    aspect = sweeping_service.aspects.first()
    payload = {
        'service_slug':    sweeping_service.slug,
        'aspect_slug':     aspect.slug,
        'commune_id':      commune.id,
        'neighborhood_id': centro.id,
        'address':         'Cra 4 #2-15',
        'latitude':        2.47,
        'longitude':       -76.60,
        'location_source': 'gps',
    }
    s = ComplaintSerializer(data=payload)
    assert s.is_valid(), s.errors
    assert s.validated_data['neighborhood_name'] == 'Centro'
    assert s.validated_data['commune_name']     == commune.name
    assert s.validated_data['address']          == 'Cra 4 #2-15'


@pytest.mark.django_db
def test_neighborhood_id_without_commune_is_rejected(sweeping_service):
    """neighborhood_id sin commune_id no puede validarse → 400."""
    aspect = sweeping_service.aspects.first()
    payload = {
        'service_slug':    sweeping_service.slug,
        'aspect_slug':     aspect.slug,
        'neighborhood_id': 12345,
        'latitude':        2.47,
        'longitude':       -76.60,
        'location_source': 'gps',
    }
    s = ComplaintSerializer(data=payload)
    assert s.is_valid() is False
    assert 'neighborhood_id' in s.errors


@pytest.mark.django_db
def test_other_aspect_requires_custom_description(commune, sweeping_service):
    """aspect_slug='other-issue' sin texto custom → 400."""
    payload = {
        'service_slug':    sweeping_service.slug,
        'aspect_slug':     'other-issue',
        'commune_id':      commune.id,
        'latitude':        2.47,
        'longitude':       -76.60,
        'location_source': 'gps',
    }
    s = ComplaintSerializer(data=payload)
    assert s.is_valid() is False
    assert 'custom_aspect_description' in s.errors


@pytest.mark.django_db
def test_other_aspect_happy_path_uses_custom_as_snapshot(commune, sweeping_service):
    """aspect_slug='other-issue' + texto → válido; aspect_description = ese texto."""
    payload = {
        'service_slug':              sweeping_service.slug,
        'aspect_slug':               'other-issue',
        'custom_aspect_description': 'Pasaron a barrer pero dejaron arena en la cuneta',
        'commune_id':                commune.id,
        'address':                   'Calle 5 #12-34',
        'latitude':                  2.47,
        'longitude':                 -76.60,
        'location_source':           'gps',
    }
    s = ComplaintSerializer(data=payload)
    assert s.is_valid(), s.errors
    assert s.validated_data['custom_aspect_description'] == \
        'Pasaron a barrer pero dejaron arena en la cuneta'
    assert s.validated_data['aspect_description'] == \
        'Pasaron a barrer pero dejaron arena en la cuneta'
    assert s.validated_data['address'] == 'Calle 5 #12-34'


@pytest.mark.django_db
def test_other_aspect_works_for_any_existing_service(
    commune, sweeping_service, green_zones_service,
):
    """Otros es transversal: válido también para servicios distintos."""
    for service in (sweeping_service, green_zones_service):
        payload = {
            'service_slug':              service.slug,
            'aspect_slug':               'other-issue',
            'custom_aspect_description': 'Problema no listado',
            'commune_id':                commune.id,
            'latitude':                  2.47,
            'longitude':                 -76.60,
            'location_source':           'gps',
        }
        s = ComplaintSerializer(data=payload)
        assert s.is_valid(), (service.slug, s.errors)


@pytest.mark.django_db
def test_normal_aspect_ignores_custom_description(commune, sweeping_service):
    """Si llega custom_aspect_description con un aspect normal, se fuerza a ''."""
    aspect = sweeping_service.aspects.first()
    payload = {
        'service_slug':              sweeping_service.slug,
        'aspect_slug':               aspect.slug,
        'custom_aspect_description': 'esto no debería persistir',
        'commune_id':                commune.id,
        'latitude':                  2.47,
        'longitude':                 -76.60,
        'location_source':           'gps',
    }
    s = ComplaintSerializer(data=payload)
    assert s.is_valid(), s.errors
    assert s.validated_data['custom_aspect_description'] == ''
    # aspect_description sigue siendo el del catálogo, no el texto custom.
    assert s.validated_data['aspect_description'] == aspect.description


@pytest.mark.django_db
def test_unknown_aspect_for_existing_service_still_rejected(
    commune, sweeping_service,
):
    """Un aspect_slug que no es 'other-issue' y no está en el catálogo → 400."""
    payload = {
        'service_slug':    sweeping_service.slug,
        'aspect_slug':     'made-up-slug',
        'commune_id':      commune.id,
        'latitude':        2.47,
        'longitude':       -76.60,
        'location_source': 'gps',
    }
    s = ComplaintSerializer(data=payload)
    assert s.is_valid() is False
    assert 'aspect_slug' in s.errors
