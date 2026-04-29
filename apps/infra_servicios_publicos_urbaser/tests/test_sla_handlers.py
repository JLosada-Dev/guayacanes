"""
Tests del handler SLA de Urbaser conectado a veeduria.complaint_created.
"""
import pytest

from apps.veeduria.models import Complaint, SLAAlert, MetricByCommune


@pytest.mark.django_db
def test_sweeping_handler_creates_alert(
    sweeping_service, sweeping_microroute, commune, point_inside_route,
):
    """Una denuncia de barrido cerca de una microruta crea una SLAAlert."""
    aspect = sweeping_service.aspects.first()

    Complaint.objects.create(
        section_slug='urbaser',
        service_slug='sweeping-cleaning',
        aspect_slug=aspect.slug,
        aspect_description=aspect.description,
        commune_id=commune.id,
        location=point_inside_route,
        location_source='gps',
    )

    alerts = SLAAlert.objects.filter(service_slug='sweeping-cleaning')
    assert alerts.count() == 1
    alert = alerts.first()
    assert alert.route_type  == 'urbaser.sweeping_microroute'
    assert alert.route_id    == sweeping_microroute.id
    assert alert.route_label == 'B211'
    assert alert.distance_meters is not None
    assert alert.extra_data.get('urbaser_macroroute_code') == 'B211'


@pytest.mark.django_db
def test_green_zones_handler_creates_alert(
    green_zones_service, public_space_with_assignment, commune, point_inside_route,
):
    """Una denuncia de zonas verdes dentro de un PublicSpace con assignment crea SLAAlert."""
    space, assignment = public_space_with_assignment
    aspect = green_zones_service.aspects.first()

    Complaint.objects.create(
        section_slug='urbaser',
        service_slug='green-zones',
        aspect_slug=aspect.slug,
        aspect_description=aspect.description,
        commune_id=commune.id,
        location=point_inside_route,
        location_source='gps',
    )

    alerts = SLAAlert.objects.filter(service_slug='green-zones')
    assert alerts.count() == 1
    alert = alerts.first()
    assert alert.route_type == 'urbaser.green_zone'
    assert alert.route_id   == assignment.id
    assert alert.extra_data.get('urbaser_assignment_external_id') == assignment.external_id
    assert alert.extra_data.get('urbaser_public_space_id')        == space.id


@pytest.mark.django_db
def test_metric_recalculated_after_alert(
    sweeping_service, sweeping_microroute, commune, point_inside_route,
):
    """Tras una denuncia con alerta, MetricByCommune queda actualizada."""
    aspect = sweeping_service.aspects.first()

    assert MetricByCommune.objects.count() == 0

    Complaint.objects.create(
        section_slug='urbaser',
        service_slug='sweeping-cleaning',
        aspect_slug=aspect.slug,
        aspect_description=aspect.description,
        commune_id=commune.id,
        location=point_inside_route,
        location_source='gps',
    )

    metric = MetricByCommune.objects.get(
        commune_id=commune.id,
        service_slug='sweeping-cleaning',
    )
    assert metric.total_complaints == 1
    assert metric.total_alerts     >= 1
