from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.contrib.gis.geos import Point

from apps.core.models import Commune
# TODO: temporary cross-app import — Service/Aspect will be resolved via
# the ServiceProvider registry once the serializer is rewritten in a
# later commit (snapshot section_slug + use registry).
from apps.infra_servicios_publicos_urbaser.models import Service, Aspect
from .models import Complaint, Evidence, SLAAlert, MetricByCommune


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
    - service_id y aspect_id se validan contra core
    - Se guardan snapshots de texto al momento del guardado
    """
    evidence           = EvidenceSerializer(many=True, read_only=True)
    latitude           = serializers.FloatField(write_only=True, required=False)
    longitude          = serializers.FloatField(write_only=True, required=False)
    # Rellenados en validate() desde el catálogo — no requeridos en el input
    service_slug       = serializers.CharField(max_length=100, required=False)
    service_name       = serializers.CharField(max_length=100, required=False)
    aspect_slug        = serializers.CharField(max_length=100, required=False)
    aspect_description = serializers.CharField(max_length=200, required=False)

    class Meta:
        model  = Complaint
        fields = [
            'id',
            'service_id', 'service_slug', 'service_name',
            'aspect_id', 'aspect_slug', 'aspect_description',
            'commune_id', 'commune_name',
            'neighborhood_id', 'neighborhood_name',
            'is_rural', 'hamlet_name',
            'latitude', 'longitude',
            'location_source',
            'description', 'status', 'created_at',
            'evidence',
        ]
        read_only_fields = ['created_at', 'status']

    def validate(self, data):
        # ── Validar servicio ──────────────────────────────────────
        service_id = data.get('service_id')
        try:
            service = Service.objects.get(id=service_id, active=True)
            data['service_slug'] = service.slug
            data['service_name'] = service.name
        except Service.DoesNotExist:
            raise serializers.ValidationError(
                {'service_id': 'Servicio no encontrado o inactivo.'}
            )

        # ── Validar aspecto ───────────────────────────────────────
        aspect_id = data.get('aspect_id')
        try:
            aspect = service.aspects.get(id=aspect_id, active=True)
            data['aspect_slug']        = aspect.slug
            data['aspect_description'] = aspect.description
        except Exception:
            raise serializers.ValidationError(
                {'aspect_id': 'Aspecto no encontrado o no pertenece al servicio.'}
            )

        # ── Resolver nombre de comuna ─────────────────────────────
        commune_id = data.get('commune_id')
        if commune_id:
            try:
                commune = Commune.objects.get(id=commune_id)
                data['commune_name'] = commune.name
            except Commune.DoesNotExist:
                raise serializers.ValidationError(
                    {'commune_id': 'Comuna no encontrada.'}
                )

        # ── Cascada de coordenada ─────────────────────────────────
        lat = data.pop('latitude', None)
        lng = data.pop('longitude', None)

        if lat is not None and lng is not None:
            data['location'] = Point(lng, lat, srid=4326)
        elif commune_id:
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
            'id', 'service_slug', 'aspect_description',
            'commune_name', 'status', 'created_at',
        ]
