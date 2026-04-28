"""
Tests del contrato público de veeduria: complaint_created.
"""
from unittest.mock import MagicMock

import pytest
from django.contrib.gis.geos import Point

from apps.veeduria.models import Complaint, SLAAlert
from apps.veeduria.signals import complaint_created


@pytest.mark.django_db
def test_complaint_created_emits_signal(sweeping_service):
    """Crear una Complaint dispara complaint_created con los kwargs esperados."""
    aspect = sweeping_service.aspects.first()
    received = MagicMock()
    complaint_created.connect(received, dispatch_uid='test.received')

    try:
        complaint = Complaint.objects.create(
            service_id=sweeping_service.id,
            service_slug=sweeping_service.slug,
            service_name=sweeping_service.name,
            aspect_id=aspect.id,
            aspect_slug=aspect.slug,
            aspect_description=aspect.description,
            location=Point(-76.60, 2.47, srid=4326),
            location_source='gps',
        )
    finally:
        complaint_created.disconnect(dispatch_uid='test.received')

    assert received.call_count == 1
    kwargs = received.call_args.kwargs
    assert kwargs['complaint_id']    == complaint.id
    assert kwargs['service_slug']    == 'sweeping-cleaning'
    assert kwargs['aspect_slug']     == aspect.slug
    assert kwargs['location_source'] == 'gps'
    assert kwargs['location'].x == pytest.approx(-76.60)


@pytest.mark.django_db
def test_handler_filters_by_slug_and_skips_unknown_service(sweeping_service):
    """Una denuncia con slug que no pertenece a ningún handler no genera alertas."""
    aspect = sweeping_service.aspects.first()

    Complaint.objects.create(
        service_id=sweeping_service.id,
        service_slug='unknown-service',  # ningún handler responde a este slug
        aspect_id=aspect.id,
        aspect_description=aspect.description,
        location=Point(-76.60, 2.47, srid=4326),
        location_source='gps',
    )

    assert SLAAlert.objects.count() == 0
