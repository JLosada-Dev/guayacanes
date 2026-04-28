from rest_framework import viewsets, mixins
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema_view, extend_schema

from .models import SweepingMacroRoute, SweepingMicroRoute, GreenZoneAssignment
from .serializers import (
    SweepingMacroRouteSerializer,
    SweepingMicroRouteSerializer,
    GreenZoneAssignmentSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=['Urbaser / Operaciones']),
    retrieve=extend_schema(tags=['Urbaser / Operaciones']),
)
class SweepingMacroRouteViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """8 macrorutas del PPS 2024."""
    permission_classes = [AllowAny]
    queryset           = SweepingMacroRoute.objects.all().order_by('code')
    serializer_class   = SweepingMacroRouteSerializer
    filter_backends    = [DjangoFilterBackend, OrderingFilter]
    filterset_fields   = ['zone_type', 'active']
    ordering_fields    = ['code', 'name']


@extend_schema_view(
    list=extend_schema(tags=['Urbaser / Operaciones']),
    retrieve=extend_schema(tags=['Urbaser / Operaciones']),
)
class SweepingMicroRouteViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Trayectos LineString de barrido cargados desde U18_VIAL.shp."""
    permission_classes = [AllowAny]
    queryset           = SweepingMicroRoute.objects.all()
    serializer_class   = SweepingMicroRouteSerializer
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['macroroute', 'layer', 'active']


@extend_schema_view(
    list=extend_schema(tags=['Urbaser / Operaciones']),
    retrieve=extend_schema(tags=['Urbaser / Operaciones']),
)
class GreenZoneAssignmentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Responsabilidad operativa de Urbaser sobre cada PublicSpace."""
    permission_classes = [AllowAny]
    queryset           = GreenZoneAssignment.objects.all()
    serializer_class   = GreenZoneAssignmentSerializer
    filter_backends    = [DjangoFilterBackend, SearchFilter]
    filterset_fields   = ['active', 'cycle_days']
    search_fields      = ['public_space_name', 'external_id']
