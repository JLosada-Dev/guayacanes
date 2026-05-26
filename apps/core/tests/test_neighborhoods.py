"""
Tests del endpoint /core/neighborhoods/ y de la ausencia de "Otros" como
servicio (ahora es solo un aspect transversal).
"""
import pytest
from rest_framework.test import APIClient

from apps.core.models import Commune, Neighborhood


@pytest.fixture
def two_communes_with_neighborhoods(db):
    """
    Crea dos comunas con sus barrios. `commune` (autouse en otros tests) ya
    crea Comuna 1 — aquí trabajamos con números altos para no chocar.
    """
    from django.contrib.gis.geos import Polygon
    poly = Polygon((
        (-76.61, 2.46), (-76.59, 2.46), (-76.59, 2.48),
        (-76.61, 2.48), (-76.61, 2.46),
    ), srid=4326)
    c_a = Commune.objects.create(number=91, name='Comuna A', area_hectares=10, geom=poly)
    c_b = Commune.objects.create(number=92, name='Comuna B', area_hectares=10, geom=poly)
    Neighborhood.objects.bulk_create([
        Neighborhood(name='Berlín',   commune=c_a),
        Neighborhood(name='Acacias',  commune=c_a),
        Neighborhood(name='Centro',   commune=c_a),
        Neighborhood(name='Pomona',   commune=c_b),
    ])
    return c_a, c_b


@pytest.mark.django_db
def test_list_neighborhoods_by_commune_returns_only_matching(
    two_communes_with_neighborhoods,
):
    c_a, _ = two_communes_with_neighborhoods
    client = APIClient()

    resp = client.get('/api/v1/core/neighborhoods/', {'commune_id': c_a.id})

    assert resp.status_code == 200
    names = [n['name'] for n in resp.json()]
    assert names == ['Acacias', 'Berlín', 'Centro']  # ordenados alfabéticamente
    assert all(n['commune_id'] == c_a.id for n in resp.json())


@pytest.mark.django_db
def test_list_neighborhoods_requires_commune_id(db):
    client = APIClient()
    resp = client.get('/api/v1/core/neighborhoods/')

    assert resp.status_code == 400
    assert 'commune_id' in resp.json()


@pytest.mark.django_db
def test_list_neighborhoods_rejects_non_integer_commune_id(db):
    client = APIClient()
    resp = client.get('/api/v1/core/neighborhoods/', {'commune_id': 'abc'})

    assert resp.status_code == 400
    assert 'commune_id' in resp.json()


@pytest.mark.django_db
def test_list_neighborhoods_empty_when_unknown_commune(db):
    client = APIClient()
    resp = client.get('/api/v1/core/neighborhoods/', {'commune_id': 9999})

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.django_db
def test_services_listing_does_not_include_other():
    """
    "Otros" no es un servicio: vive como aspect transversal aplicable a
    cualquier servicio. El catálogo de /core/services/ no debe exponerlo.
    """
    client = APIClient()
    services = client.get('/api/v1/core/services/').json()
    slugs = [s['slug'] for s in services]
    assert 'other' not in slugs
