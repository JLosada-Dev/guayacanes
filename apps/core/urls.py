from django.urls import path
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Commune
# TODO: temporary cross-app imports — these endpoints will be rewritten
# as registry aggregators in the next commit, removing this coupling.
from apps.infra_servicios_publicos_urbaser.models import (
    Service, Aspect, ServiceContent, AspectContent,
)


class AspectContentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AspectContent
        fields = ['icon', 'what_is', 'how_to_evidence', 'response_time']


class ServiceContentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ServiceContent
        fields = ['icon', 'summary', 'full_description', 'frequency', 'citizen_rights']


class AspectSerializer(serializers.ModelSerializer):
    content = AspectContentSerializer(read_only=True)

    class Meta:
        model  = Aspect
        fields = ['id', 'service_id', 'slug', 'description', 'content']


class ServiceSerializer(serializers.ModelSerializer):
    content = ServiceContentSerializer(read_only=True)

    class Meta:
        model  = Service
        fields = ['id', 'name', 'slug', 'description', 'order', 'content']


class CommuneSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Commune
        fields = ['id', 'number', 'name', 'area_hectares']


class CommuneGeoSerializer(GeoFeatureModelSerializer):
    class Meta:
        model     = Commune
        geo_field = 'geom'
        fields    = ['id', 'number', 'name', 'area_hectares']


@extend_schema(
    summary='Listar servicios activos',
    description=(
        'Retorna los servicios públicos activos con su contenido informativo. '
        'Usado por el formulario ciudadano para seleccionar el tipo de servicio a denunciar. '
        'Ordenados por el campo `order`.'
    ),
    responses=ServiceSerializer(many=True),
    tags=['Core / Catálogo'],
)
@api_view(['GET'])
def services_list(request):
    services = Service.objects.filter(
        active=True
    ).select_related('content').order_by('order')
    return Response(ServiceSerializer(services, many=True).data)


@extend_schema(
    summary='Listar aspectos activos',
    description=(
        'Retorna los aspectos (subcategorías) de los servicios con su contenido informativo. '
        'Cuando el ciudadano selecciona un aspecto en el formulario, ve la explicación de qué es '
        'y cómo evidenciarlo. Filtrar por `service` para obtener solo los aspectos de un servicio.'
    ),
    parameters=[
        OpenApiParameter(
            name='service',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Slug del servicio para filtrar aspectos (ej: `sweeping-cleaning`, `green-zones`).',
            required=False,
        ),
    ],
    responses=AspectSerializer(many=True),
    tags=['Core / Catálogo'],
)
@api_view(['GET'])
def aspects_list(request):
    service_slug = request.query_params.get('service')
    aspects = Aspect.objects.filter(
        active=True
    ).select_related('content', 'service')
    if service_slug:
        aspects = aspects.filter(service__slug=service_slug)
    return Response(AspectSerializer(aspects, many=True).data)


@extend_schema(
    summary='Listar comunas de Popayán',
    description='Retorna las 9 comunas de Popayán ordenadas por número. Usadas para geolocalizar denuncias.',
    responses=CommuneSerializer(many=True),
    tags=['Core / Catálogo'],
)
@api_view(['GET'])
def communes_list(request):
    communes = Commune.objects.all().order_by('number')
    return Response(CommuneSerializer(communes, many=True).data)


@extend_schema(
    summary='Comunas en formato GeoJSON',
    description=(
        'Retorna las 9 comunas de Popayán como GeoJSON FeatureCollection '
        'para renderizar polígonos en el mapa del dashboard.'
    ),
    responses=CommuneGeoSerializer(many=True),
    tags=['Core / Catálogo'],
)
@api_view(['GET'])
def communes_geojson(request):
    communes = Commune.objects.all().order_by('number')
    serializer = CommuneGeoSerializer(communes, many=True)
    return Response(serializer.data)


urlpatterns = [
    path('services/',        services_list,   name='services-list'),
    path('aspects/',         aspects_list,    name='aspects-list'),
    path('communes/',        communes_list,   name='communes-list'),
    path('communes/geojson/', communes_geojson, name='communes-geojson'),
]
