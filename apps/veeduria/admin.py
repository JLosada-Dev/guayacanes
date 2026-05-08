from django.contrib.gis import admin
from .models import Complaint, Evidence, SLAAlert, MetricByCommune


class EvidenceInline(admin.TabularInline):
    model           = Evidence
    extra           = 0
    fields          = ['image', 'uploaded_at']
    readonly_fields = ['uploaded_at']


@admin.register(Complaint)
class ComplaintAdmin(admin.GISModelAdmin):
    list_display    = [
        'id', 'section_slug', 'service_slug', 'aspect_description',
        'commune_name', 'status', 'location_source', 'created_at',
    ]
    list_filter     = ['status', 'section_slug', 'service_slug', 'location_source', 'is_rural']
    search_fields   = ['aspect_description', 'commune_name', 'neighborhood_name']
    ordering        = ['-created_at']
    readonly_fields = ['created_at']
    inlines         = [EvidenceInline]
    fieldsets = [
        ('Qué', {
            'fields': [
                'section_slug', 'section_name',
                'service_slug', 'service_name',
                'aspect_slug', 'aspect_description',
            ]
        }),
        ('Dónde', {
            'fields': [
                'commune_id', 'commune_name',
                'neighborhood_id', 'neighborhood_name',
                'is_rural', 'hamlet_name',
                'location', 'location_source',
            ]
        }),
        ('Contexto', {
            'fields': ['description', 'status', 'created_at']
        }),
    ]


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display    = ['id', 'complaint', 'uploaded_at']
    ordering        = ['-uploaded_at']
    readonly_fields = ['uploaded_at']


@admin.register(SLAAlert)
class SLAAlertAdmin(admin.ModelAdmin):
    list_display    = [
        'id', 'complaint_id', 'service_slug', 'route_type',
        'route_label', 'violation', 'distance_meters', 'confidence', 'generated_at',
    ]
    list_filter     = ['violation', 'service_slug', 'route_type', 'confidence']
    ordering        = ['-generated_at']
    readonly_fields = [
        'complaint_id', 'service_slug', 'route_type', 'route_id',
        'route_label', 'violation', 'distance_meters', 'extra_int',
        'extra_data', 'confidence', 'generated_at',
    ]
    search_fields   = ['complaint_id', 'route_label']

    def has_add_permission(self, request):    return False
    def has_change_permission(self, request, obj=None): return False


@admin.register(MetricByCommune)
class MetricByCommuneAdmin(admin.ModelAdmin):
    list_display    = [
        'commune_name', 'service_slug', 'total_complaints',
        'total_violations', 'violation_rate', 'period', 'updated_at',
    ]
    list_filter     = ['service_slug', 'period']
    ordering        = ['-period', 'commune_id']
    readonly_fields = [
        'commune_id', 'commune_name', 'service_slug', 'total_complaints',
        'total_alerts', 'total_violations', 'violation_rate', 'period', 'updated_at',
    ]

    def has_add_permission(self, request):    return False
    def has_change_permission(self, request, obj=None): return False
