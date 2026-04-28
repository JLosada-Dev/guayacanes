from django.contrib.gis import admin
from .models import PublicSpace


@admin.register(PublicSpace)
class PublicSpaceAdmin(admin.GISModelAdmin):
    list_display  = ['external_id', 'name', 'space_type', 'source_layer', 'area_sqm', 'active']
    list_filter   = ['space_type', 'source_layer', 'active']
    search_fields = ['name', 'external_id']
    ordering      = ['name']
