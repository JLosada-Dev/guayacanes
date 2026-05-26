from django.urls import path
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Commune, Neighborhood, Section
from .registry import all_providers, get_provider


# ── Serializers ──────────────────────────────────────────────────────


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Section
        fields = ['id', 'code', 'name', 'slug', 'description', 'active', 'order']


class CommuneSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Commune
        fields = ['id', 'number', 'name', 'area_hectares']


class CommuneGeoSerializer(GeoFeatureModelSerializer):
    class Meta:
        model     = Commune
        geo_field = 'geom'
        fields    = ['id', 'number', 'name', 'area_hectares']


class NeighborhoodSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Neighborhood
        fields = ['id', 'name', 'commune_id']


# ── Endpoints ─────────────────────────────────────────────────────────


@extend_schema(
    summary='Listar secciones (proveedores de servicios)',
    description=(
        'Retorna las secciones de la Alcaldía que prestan servicios públicos: '
        'Urbaser (aseo), Vivienda, Cultura, etc. Cada sección tiene su propio '
        'catálogo de servicios y aspectos accesibles vía /core/services/.'
    ),
    responses=SectionSerializer(many=True),
    tags=['Core / Catálogo'],
)
@api_view(['GET'])
def sections_list(request):
    sections = Section.objects.filter(active=True).order_by('order', 'name')
    return Response(SectionSerializer(sections, many=True).data)


@extend_schema(
    summary='Listar servicios públicos disponibles',
    description=(
        'Retorna los servicios activos agregando los catálogos de todas las '
        'secciones registradas. Cada servicio incluye `section_slug` y '
        '`section_name` para que el frontend pueda agrupar por proveedor. '
        'Filtrar por `?section=<slug>` para una sola sección.'
    ),
    parameters=[
        OpenApiParameter(
            name='section',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Slug de la sección. Ej: `urbaser`.',
            required=False,
        ),
    ],
    tags=['Core / Catálogo'],
)
@api_view(['GET'])
def services_list(request):
    section_slug = request.query_params.get('section')
    if section_slug:
        provider = get_provider(section_slug)
        providers = [provider] if provider is not None else []
    else:
        providers = all_providers()

    services = [s for p in providers for s in p.get_services()]
    services.sort(key=lambda s: (s.order, s.section_slug, s.slug))
    return Response([s.to_dict() for s in services])


@extend_schema(
    summary='Listar aspectos de un servicio',
    description=(
        'Retorna los aspectos (subcategorías de queja) del servicio indicado, '
        'tomados del catálogo de la sección a la que pertenece.'
    ),
    parameters=[
        OpenApiParameter(
            name='service',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Slug del servicio. Ej: `sweeping-cleaning`.',
            required=True,
        ),
        OpenApiParameter(
            name='section',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Slug de la sección dueña del servicio (opcional, ayuda a desambiguar).',
            required=False,
        ),
    ],
    tags=['Core / Catálogo'],
)
@api_view(['GET'])
def aspects_list(request):
    service_slug = request.query_params.get('service')
    if not service_slug:
        return Response([])

    section_slug = request.query_params.get('section')
    if section_slug:
        provider = get_provider(section_slug)
        providers = [provider] if provider is not None else []
    else:
        providers = all_providers()

    aspects = [a for p in providers for a in p.get_aspects(service_slug)]
    return Response([a.to_dict() for a in aspects])


@extend_schema(
    summary='Listar comunas de Popayán',
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


@extend_schema(
    summary='Listar barrios de una comuna',
    description=(
        'Retorna los barrios pertenecientes a la comuna indicada por '
        '`commune_id`. Pensado para alimentar un selector con búsqueda '
        'aproximada (fuzzy) en el cliente; la respuesta es plana, sin '
        'geometría y sin paginar (≤60 barrios por comuna).'
    ),
    parameters=[
        OpenApiParameter(
            name='commune_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='ID de la comuna (Commune.id, no Commune.number).',
            required=True,
        ),
    ],
    responses=NeighborhoodSerializer(many=True),
    tags=['Core / Catálogo'],
)
@api_view(['GET'])
def neighborhoods_list(request):
    commune_id = request.query_params.get('commune_id')
    if not commune_id:
        return Response(
            {'commune_id': 'Parámetro requerido.'},
            status=400,
        )
    try:
        commune_id_int = int(commune_id)
    except (TypeError, ValueError):
        return Response(
            {'commune_id': 'Debe ser un entero.'},
            status=400,
        )
    neighborhoods = (
        Neighborhood.objects
        .filter(commune_id=commune_id_int)
        .order_by('name')
    )
    return Response(NeighborhoodSerializer(neighborhoods, many=True).data)


urlpatterns = [
    path('sections/',         sections_list,      name='sections-list'),
    path('services/',         services_list,      name='services-list'),
    path('aspects/',          aspects_list,       name='aspects-list'),
    path('communes/',         communes_list,      name='communes-list'),
    path('communes/geojson/', communes_geojson,   name='communes-geojson'),
    path('neighborhoods/',    neighborhoods_list, name='neighborhoods-list'),
]
