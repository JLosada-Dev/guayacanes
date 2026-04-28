from django.contrib.gis import admin
from .models import Commune, Neighborhood, Service, Aspect, Section


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display  = ['code', 'name', 'slug', 'active', 'order']
    list_filter   = ['active']
    search_fields = ['code', 'name', 'slug']
    ordering      = ['order', 'name']


@admin.register(Commune)
class CommuneAdmin(admin.GISModelAdmin):
    list_display  = ['number', 'name', 'area_hectares']
    ordering      = ['number']
    search_fields = ['name', 'number']


@admin.register(Neighborhood)
class NeighborhoodAdmin(admin.GISModelAdmin):
    list_display  = ['name', 'commune', 'dane_code', 'osm_id']
    ordering      = ['commune__number', 'name']
    search_fields = ['name']
    list_filter   = ['commune']
    autocomplete_fields = ['commune']
    exclude       = ['geom']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display  = ['name', 'slug', 'active', 'order']
    ordering      = ['order']
    search_fields = ['name', 'slug']
    list_filter   = ['active']


@admin.register(Aspect)
class AspectAdmin(admin.ModelAdmin):
    list_display  = ['description', 'service', 'slug', 'active']
    ordering      = ['service__order', 'description']
    search_fields = ['description', 'slug']
    list_filter   = ['service', 'active']
