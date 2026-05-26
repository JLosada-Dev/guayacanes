from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.contrib.gis.geos import Point

from apps.core.models import Commune, Neighborhood
from apps.core.providers import OTHER_ASPECT_SLUG
from apps.core.registry import all_providers
from .models import Complaint, Evidence, SLAAlert, MetricByCommune


def _resolve_service(service_slug: str):
    """
    Busca un service_slug en todos los providers registrados.
    Retorna el ServiceInfo del primer match o None.
    """
    for provider in all_providers():
        for service in provider.get_services():
            if service.slug == service_slug:
                return service
    return None


def _resolve_aspect(service_slug: str, aspect_slug: str):
    """
    Busca un aspect_slug dentro de un servicio específico.
    Itera providers — el primero que tenga el service_slug responde.
    """
    for provider in all_providers():
        services = provider.get_services()
        if not any(s.slug == service_slug for s in services):
            continue
        for aspect in provider.get_aspects(service_slug):
            if aspect.slug == aspect_slug:
                return aspect
    return None


class EvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Evidence
        fields = ['id', 'complaint', 'image', 'uploaded_at']
        read_only_fields = ['uploaded_at']


class ComplaintSerializer(serializers.ModelSerializer):
    """
    Serializer para crear y listar denuncias ciudadanas.

    Reglas críticas:
    - location NUNCA puede ser NULL — cascada: gps → manual → centroid
    - service_slug y aspect_slug se validan contra el ServiceProvider registry
    - Se guardan snapshots de texto (section, service, aspect) al guardar
    """
    evidence     = EvidenceSerializer(many=True, read_only=True)
    latitude     = serializers.FloatField(write_only=True, required=False)
    longitude    = serializers.FloatField(write_only=True, required=False)

    # Inputs requeridos
    service_slug = serializers.CharField(max_length=100)
    aspect_slug  = serializers.CharField(max_length=100)

    # Rellenados en validate(); read-only en la respuesta
    section_slug       = serializers.CharField(max_length=20,  read_only=True)
    section_name       = serializers.CharField(max_length=100, read_only=True)
    service_name       = serializers.CharField(max_length=100, read_only=True)
    aspect_description = serializers.CharField(max_length=200, read_only=True)
    neighborhood_name  = serializers.CharField(max_length=150, read_only=True)

    class Meta:
        model  = Complaint
        fields = [
            'id',
            'section_slug', 'section_name',
            'service_slug', 'service_name',
            'aspect_slug', 'aspect_description', 'custom_aspect_description',
            'commune_id', 'commune_name',
            'neighborhood_id', 'neighborhood_name',
            'address',
            'is_rural', 'hamlet_name',
            'latitude', 'longitude',
            'location_source',
            'description', 'status', 'created_at',
            'evidence',
        ]
        read_only_fields = ['created_at', 'status']

    def validate(self, data):
        service_slug = data.get('service_slug')
        aspect_slug  = data.get('aspect_slug')

        # ── Resolver servicio ─────────────────────────────────────
        service_info = _resolve_service(service_slug)
        if service_info is None or not service_info.active:
            raise serializers.ValidationError(
                {'service_slug': 'Servicio no encontrado o inactivo.'}
            )
        data['section_slug'] = service_info.section_slug
        data['section_name'] = service_info.section_name
        data['service_name'] = service_info.name

        # ── Resolver aspecto ──────────────────────────────────────
        # "other-issue" es transversal: válido para cualquier servicio sin
        # estar en el catálogo. El ciudadano describe el problema en
        # custom_aspect_description y eso pasa a ser el snapshot.
        custom_aspect = (data.get('custom_aspect_description') or '').strip()
        if aspect_slug == OTHER_ASPECT_SLUG:
            if not custom_aspect:
                raise serializers.ValidationError({
                    'custom_aspect_description':
                        'Requerido cuando aspect_slug="other-issue".',
                })
            data['custom_aspect_description'] = custom_aspect
            data['aspect_description']        = custom_aspect
        else:
            aspect_info = _resolve_aspect(service_slug, aspect_slug)
            if aspect_info is None or not aspect_info.active:
                raise serializers.ValidationError(
                    {'aspect_slug': 'Aspecto no encontrado o no pertenece al servicio.'}
                )
            data['aspect_description']        = aspect_info.description
            # Evita que un aspect normal arrastre un texto custom: el campo
            # solo tiene sentido para "other-issue".
            data['custom_aspect_description'] = ''

        # ── Resolver nombre de comuna ─────────────────────────────
        commune_id = data.get('commune_id')
        commune    = None
        if commune_id:
            try:
                commune = Commune.objects.get(id=commune_id)
                data['commune_name'] = commune.name
            except Commune.DoesNotExist:
                raise serializers.ValidationError(
                    {'commune_id': 'Comuna no encontrada.'}
                )

        # ── Validar barrio (si viene) y snapshot ──────────────────
        neighborhood_id = data.get('neighborhood_id')
        if neighborhood_id:
            if commune is None:
                raise serializers.ValidationError(
                    {'neighborhood_id': 'Requiere commune_id para validar pertenencia.'}
                )
            try:
                neighborhood = Neighborhood.objects.get(
                    id=neighborhood_id, commune_id=commune.id,
                )
            except Neighborhood.DoesNotExist:
                raise serializers.ValidationError(
                    {'neighborhood_id': 'No pertenece a la comuna indicada.'}
                )
            data['neighborhood_name'] = neighborhood.name

        # ── Cascada de coordenada ─────────────────────────────────
        lat = data.pop('latitude', None)
        lng = data.pop('longitude', None)

        if lat is not None and lng is not None:
            data['location'] = Point(lng, lat, srid=4326)
        elif commune is not None:
            data['location']        = commune.geom.centroid
            data['location_source'] = 'centroid'
        else:
            raise serializers.ValidationError(
                {'location': 'Se requiere coordenada GPS o selección de comuna.'}
            )

        return data


class SLAAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SLAAlert
        fields = [
            'id', 'complaint_id', 'service_slug',
            'route_type', 'route_id', 'route_label',
            'violation', 'distance_meters', 'extra_int', 'extra_data',
            'confidence', 'generated_at',
        ]
        read_only_fields = fields


class MetricByCommuneSerializer(serializers.ModelSerializer):
    class Meta:
        model  = MetricByCommune
        fields = [
            'id', 'commune_id', 'commune_name', 'service_slug',
            'total_complaints', 'total_alerts', 'total_violations',
            'violation_rate', 'period', 'updated_at',
        ]
        read_only_fields = fields


class ComplaintGeoSerializer(GeoFeatureModelSerializer):
    """Serializer GeoJSON para el mapa del dashboard."""
    class Meta:
        model        = Complaint
        geo_field    = 'location'
        fields = [
            'id', 'section_slug', 'service_slug', 'aspect_description',
            'commune_name', 'status', 'created_at',
        ]
