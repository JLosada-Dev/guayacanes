from rest_framework import viewsets, mixins
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Complaint, Evidence, SLAAlert, MetricByCommune
from .serializers import (
    ComplaintSerializer,
    ComplaintGeoSerializer,
    EvidenceSerializer,
    SLAAlertSerializer,
    MetricByCommuneSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary='Listar denuncias ciudadanas',
        description=(
            'Lista todas las denuncias recibidas. Soporta filtros por estado, servicio, '
            'comuna y zona rural. También permite búsqueda de texto y ordenamiento.'
        ),
        parameters=[
            OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY,
                             description='Filtrar por estado (`received`, `under_review`, `closed`).'),
            OpenApiParameter('service_slug', OpenApiTypes.STR, OpenApiParameter.QUERY,
                             description='Filtrar por servicio (ej: `sweeping-cleaning`, `green-zones`).'),
            OpenApiParameter('commune_id', OpenApiTypes.INT, OpenApiParameter.QUERY,
                             description='Filtrar por ID de comuna.'),
            OpenApiParameter('is_rural', OpenApiTypes.BOOL, OpenApiParameter.QUERY,
                             description='Filtrar denuncias rurales (`true`) o urbanas (`false`).'),
            OpenApiParameter('search', OpenApiTypes.STR, OpenApiParameter.QUERY,
                             description='Búsqueda de texto en descripción del aspecto, nombre de comuna o barrio.'),
            OpenApiParameter('ordering', OpenApiTypes.STR, OpenApiParameter.QUERY,
                             description='Ordenar por campo. Prefijo `-` para descendente. Ej: `-created_at`.'),
        ],
        responses=ComplaintSerializer(many=True),
        tags=['Veeduría / Denuncias'],
    ),
    retrieve=extend_schema(
        summary='Detalle de una denuncia',
        responses=ComplaintSerializer,
        tags=['Veeduría / Denuncias'],
    ),
    create=extend_schema(
        summary='Crear denuncia ciudadana',
        description=(
            'Crea una nueva denuncia ciudadana. La ubicación sigue una cascada automática:\n\n'
            '1. **GPS**: si se envían `latitude` y `longitude`.\n'
            '2. **Manual**: si se envía solo un punto desde el mapa.\n'
            '3. **Centroide**: si no hay coordenadas, usa el centroide de la comuna seleccionada.\n\n'
            'Al crear la denuncia se emite la signal `complaint_created`; cada app de servicio '
            'público registrada decide si le aplica generar alertas SLA.'
        ),
        request=ComplaintSerializer,
        responses={201: ComplaintSerializer},
        tags=['Veeduría / Denuncias'],
    ),
)
class ComplaintViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Denuncias ciudadanas — transversal a todos los servicios públicos."""
    permission_classes     = [AllowAny]
    authentication_classes = []
    queryset               = Complaint.objects.all().order_by('-created_at')
    serializer_class       = ComplaintSerializer
    filter_backends        = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields       = ['status', 'service_slug', 'commune_id', 'is_rural']
    search_fields          = ['aspect_description', 'commune_name', 'neighborhood_name']
    ordering_fields        = ['created_at', 'status', 'service_slug']

    def get_serializer_class(self):
        if self.action == 'geojson':
            return ComplaintGeoSerializer
        return ComplaintSerializer

    @extend_schema(
        summary='Denuncias en formato GeoJSON',
        responses=ComplaintGeoSerializer(many=True),
        tags=['Veeduría / Denuncias'],
    )
    @action(detail=False, methods=['get'], url_path='geojson')
    def geojson(self, request):
        queryset   = self.filter_queryset(self.get_queryset())
        serializer = ComplaintGeoSerializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema_view(
    create=extend_schema(
        summary='Subir foto de evidencia',
        request=EvidenceSerializer,
        responses={201: EvidenceSerializer},
        tags=['Veeduría / Denuncias'],
    ),
)
class EvidenceViewSet(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Evidencias fotográficas adjuntas a denuncias ciudadanas."""
    queryset         = Evidence.objects.all()
    serializer_class = EvidenceSerializer
    parser_classes   = [MultiPartParser, FormParser, JSONParser]


@extend_schema_view(
    list=extend_schema(
        summary='Listar alertas SLA',
        description=(
            'Lista las alertas SLA generadas automáticamente por los handlers de servicio '
            'al recibir cada denuncia.'
        ),
        parameters=[
            OpenApiParameter('violation', OpenApiTypes.BOOL, OpenApiParameter.QUERY),
            OpenApiParameter('service_slug', OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter('route_type', OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter('confidence', OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter('complaint_id', OpenApiTypes.INT, OpenApiParameter.QUERY),
        ],
        responses=SLAAlertSerializer(many=True),
        tags=['Veeduría / SLA'],
    ),
    retrieve=extend_schema(
        summary='Detalle de alerta SLA',
        responses=SLAAlertSerializer,
        tags=['Veeduría / SLA'],
    ),
)
class SLAAlertViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Alertas SLA generadas por handlers de servicio."""
    queryset         = SLAAlert.objects.all()
    serializer_class = SLAAlertSerializer
    filter_backends  = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['violation', 'service_slug', 'route_type', 'confidence', 'complaint_id']
    ordering_fields  = ['generated_at', 'violation', 'service_slug']


@extend_schema_view(
    list=extend_schema(
        summary='Listar métricas por comuna',
        parameters=[
            OpenApiParameter('service_slug', OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter('period', OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter('commune_id', OpenApiTypes.INT, OpenApiParameter.QUERY),
        ],
        responses=MetricByCommuneSerializer(many=True),
        tags=['Veeduría / Métricas'],
    ),
    retrieve=extend_schema(
        summary='Detalle de métrica por comuna',
        responses=MetricByCommuneSerializer,
        tags=['Veeduría / Métricas'],
    ),
)
class MetricByCommuneViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Métricas pre-calculadas por comuna para el heatmap del dashboard."""
    queryset         = MetricByCommune.objects.all()
    serializer_class = MetricByCommuneSerializer
    pagination_class = None
    filter_backends  = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['service_slug', 'period', 'commune_id']
    ordering_fields  = ['period', 'violation_rate', 'commune_id']
