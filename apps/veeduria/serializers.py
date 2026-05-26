from django.contrib.gis.geos import Point
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from apps.accounts.roles import user_role
from apps.core.models import Commune, Neighborhood
from apps.core.providers import OTHER_ASPECT_SLUG
from apps.core.registry import all_providers
from .models import Complaint, ComplaintStatusEvent, Evidence, MetricByCommune, SLAAlert
from .transitions import can_transition


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


MAX_EVIDENCE_PER_COMPLAINT = 2
MAX_EVIDENCE_FILE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_EVIDENCE_CONTENT_TYPES = (
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/heic',
    'image/heif',
)


class EvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Evidence
        fields = ['id', 'complaint', 'image', 'uploaded_at']
        read_only_fields = ['uploaded_at']

    def validate_image(self, value):
        if value.size > MAX_EVIDENCE_FILE_BYTES:
            mb = MAX_EVIDENCE_FILE_BYTES // (1024 * 1024)
            raise serializers.ValidationError(
                f'El archivo supera el tamaño máximo permitido ({mb} MB).'
            )
        content_type = getattr(value, 'content_type', '') or ''
        if content_type and content_type.lower() not in ALLOWED_EVIDENCE_CONTENT_TYPES:
            raise serializers.ValidationError(
                'Formato no permitido. Usa JPG, PNG, WEBP o HEIC.'
            )
        return value

    def validate(self, data):
        complaint = data.get('complaint')
        if complaint:
            existing = complaint.evidence.count()
            if existing >= MAX_EVIDENCE_PER_COMPLAINT:
                raise serializers.ValidationError({
                    'complaint': (
                        f'La denuncia ya alcanzó el límite de '
                        f'{MAX_EVIDENCE_PER_COMPLAINT} fotografías.'
                    ),
                })
        return data


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
            'description', 'status', 'severity', 'created_at',
            'evidence',
        ]
        read_only_fields = ['created_at', 'status', 'severity']

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
            'commune_name', 'status', 'severity', 'created_at',
        ]


# ─────────────────────────────────────────────────────────────────────
#  STAFF SERIALIZERS — portal de alcaldía
# ─────────────────────────────────────────────────────────────────────


class ComplaintStatusEventSerializer(serializers.ModelSerializer):
    """Read-only entry of the complaint status timeline."""

    class Meta:
        model = ComplaintStatusEvent
        fields = [
            'id',
            'from_status', 'to_status',
            'actor_user', 'actor_username', 'actor_full_name', 'actor_role',
            'note', 'created_at',
        ]
        read_only_fields = fields


class ComplaintDetailSerializer(serializers.ModelSerializer):
    """Full complaint payload for the staff detail view."""
    evidence = EvidenceSerializer(many=True, read_only=True)
    status_events = ComplaintStatusEventSerializer(many=True, read_only=True)
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = Complaint
        fields = [
            'id',
            'section_slug', 'section_name',
            'service_slug', 'service_name',
            'aspect_slug', 'aspect_description', 'custom_aspect_description',
            'commune_id', 'commune_name',
            'neighborhood_id', 'neighborhood_name',
            'address',
            'is_rural', 'hamlet_name',
            'latitude', 'longitude', 'location_source',
            'description', 'status', 'severity',
            'internal_notes',
            'created_at',
            'evidence', 'status_events',
        ]
        read_only_fields = fields

    def get_latitude(self, obj) -> float | None:
        return obj.location.y if obj.location else None

    def get_longitude(self, obj) -> float | None:
        return obj.location.x if obj.location else None


class ComplaintCharacterizeSerializer(serializers.ModelSerializer):
    """PATCH payload for staff to characterize/reclassify a complaint.

    Lets the staff move section/service/aspect, adjust the map location,
    set severity and edit internal notes. Status is **not** mutable here —
    use the ``transition`` action instead.
    """
    latitude = serializers.FloatField(write_only=True, required=False)
    longitude = serializers.FloatField(write_only=True, required=False)

    class Meta:
        model = Complaint
        fields = [
            'service_slug', 'aspect_slug', 'custom_aspect_description',
            'commune_id', 'neighborhood_id', 'address',
            'severity', 'internal_notes',
            'latitude', 'longitude',
        ]

    def validate(self, data):
        instance: Complaint = self.instance  # type: ignore[assignment]

        # Re-resolve service/aspect against the registry whenever either changes.
        service_slug = data.get('service_slug', instance.service_slug)
        aspect_slug = data.get('aspect_slug', instance.aspect_slug)
        if 'service_slug' in data or 'aspect_slug' in data:
            service_info = _resolve_service(service_slug)
            if service_info is None or not service_info.active:
                raise serializers.ValidationError(
                    {'service_slug': 'Servicio no encontrado o inactivo.'}
                )
            data['section_slug'] = service_info.section_slug
            data['section_name'] = service_info.section_name
            data['service_name'] = service_info.name

            custom = (
                data.get('custom_aspect_description')
                or instance.custom_aspect_description
                or ''
            ).strip()
            if aspect_slug == OTHER_ASPECT_SLUG:
                if not custom:
                    raise serializers.ValidationError({
                        'custom_aspect_description':
                            'Requerido cuando aspect_slug="other-issue".',
                    })
                data['custom_aspect_description'] = custom
                data['aspect_description'] = custom
            else:
                aspect_info = _resolve_aspect(service_slug, aspect_slug)
                if aspect_info is None or not aspect_info.active:
                    raise serializers.ValidationError(
                        {'aspect_slug': 'Aspecto no encontrado o no pertenece al servicio.'}
                    )
                data['aspect_description'] = aspect_info.description
                data['custom_aspect_description'] = ''

        # Commune/neighborhood snapshots.
        commune_id = data.get('commune_id', instance.commune_id)
        commune = None
        if commune_id and 'commune_id' in data:
            try:
                commune = Commune.objects.get(id=commune_id)
                data['commune_name'] = commune.name
            except Commune.DoesNotExist:
                raise serializers.ValidationError(
                    {'commune_id': 'Comuna no encontrada.'}
                )

        neighborhood_id = data.get('neighborhood_id', instance.neighborhood_id)
        if neighborhood_id and 'neighborhood_id' in data:
            if commune is None and commune_id:
                commune = Commune.objects.filter(id=commune_id).first()
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

        # Optional location override (drag marker). Staff edits are always
        # treated as 'manual' once they move the pin.
        lat = data.pop('latitude', None)
        lng = data.pop('longitude', None)
        if lat is not None and lng is not None:
            data['location'] = Point(lng, lat, srid=4326)
            data['location_source'] = 'manual'

        return data


class ComplaintTransitionSerializer(serializers.Serializer):
    """POST body for state transitions. Validates against the role matrix."""
    to_status = serializers.ChoiceField(
        choices=[c[0] for c in Complaint.STATUS_CHOICES]
    )
    note = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, data):
        instance: Complaint = self.context['complaint']
        request = self.context['request']
        role = user_role(request.user)
        from_status = instance.status
        to_status = data['to_status']

        if from_status == to_status:
            raise serializers.ValidationError(
                {'to_status': 'La denuncia ya se encuentra en ese estado.'}
            )

        if not can_transition(from_status, to_status, role):
            raise serializers.ValidationError(
                {'to_status': f'Transición {from_status}→{to_status} no permitida para tu rol.'}
            )

        data['from_status'] = from_status
        data['role'] = role
        return data

    def save(self, **kwargs):
        complaint: Complaint = self.context['complaint']
        request = self.context['request']
        user = request.user
        from_status = self.validated_data['from_status']
        to_status = self.validated_data['to_status']
        note = self.validated_data.get('note', '')
        role = self.validated_data['role']

        complaint.status = to_status
        complaint.save(update_fields=['status'])

        event = ComplaintStatusEvent.objects.create(
            complaint=complaint,
            actor_user=user,
            actor_username=user.username,
            actor_full_name=user.get_full_name() or user.username,
            actor_role=role or '',
            from_status=from_status,
            to_status=to_status,
            note=note,
        )
        return event
