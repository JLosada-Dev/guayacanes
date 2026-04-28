from django.contrib.gis import admin
from .models import (
    Complaint, Evidence,
    SweepingMacroRoute, SweepingMicroRoute,
    GreenZoneAssignment, CuttingSchedule, Intervention,
    SLAAlert, CommuneMetric,
    ServiceContent, AspectContent,
)


class EvidenceInline(admin.TabularInline):
    model           = Evidence
    extra           = 0
    fields          = ['image', 'uploaded_at']
    readonly_fields = ['uploaded_at']


@admin.register(Complaint)
class ComplaintAdmin(admin.GISModelAdmin):
    list_display    = [
        'id', 'service_slug', 'aspect_description',
        'commune_name', 'status', 'location_source', 'created_at',
    ]
    list_filter     = ['status', 'service_slug', 'location_source', 'is_rural']
    search_fields   = ['aspect_description', 'commune_name', 'neighborhood_name']
    ordering        = ['-created_at']
    readonly_fields = ['created_at']
    inlines         = [EvidenceInline]
    fieldsets = [
        ('Qué', {
            'fields': [
                'service_id', 'service_slug', 'service_name',
                'aspect_id', 'aspect_slug', 'aspect_description',
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


class SweepingMicroRouteInline(admin.TabularInline):
    model           = SweepingMicroRoute
    extra           = 0
    fields          = ['layer', 'active']
    readonly_fields = ['layer']
    can_delete      = False
    max_num         = 0
    verbose_name_plural = 'Microrutas (solo lectura — cargadas desde shapefile)'


@admin.register(SweepingMacroRoute)
class SweepingMacroRouteAdmin(admin.GISModelAdmin):
    list_display  = ['code', 'name', 'zone_type', 'days_text', 'start_time', 'active']
    list_filter   = ['zone_type', 'active']
    search_fields = ['code', 'name']
    ordering      = ['code']
    readonly_fields = ['code']
    inlines       = [SweepingMicroRouteInline]


@admin.register(SweepingMicroRoute)
class SweepingMicroRouteAdmin(admin.GISModelAdmin):
    list_display  = ['id', 'macroroute', 'layer', 'active']
    list_filter   = ['macroroute', 'layer', 'active']
    ordering      = ['macroroute__code']
    readonly_fields = ['macroroute', 'layer', 'geom']


class CuttingScheduleInline(admin.TabularInline):
    model           = CuttingSchedule
    extra           = 0
    fields          = ['scheduled_date', 'month', 'year', 'executed']
    readonly_fields = ['scheduled_date', 'month', 'year']


class InterventionInline(admin.TabularInline):
    model  = Intervention
    extra  = 1
    fields = ['execution_date', 'intervention_type', 'recorded_by', 'notes']


@admin.register(GreenZoneAssignment)
class GreenZoneAssignmentAdmin(admin.ModelAdmin):
    list_display  = ['external_id', 'public_space_name', 'public_space_id', 'cycle_days', 'active']
    list_filter   = ['active']
    search_fields = ['public_space_name', 'external_id', 'public_space_id']
    ordering      = ['external_id']
    inlines       = [CuttingScheduleInline, InterventionInline]


@admin.register(CuttingSchedule)
class CuttingScheduleAdmin(admin.ModelAdmin):
    list_display  = ['assignment', 'scheduled_date', 'month', 'year', 'executed']
    list_filter   = ['executed', 'year', 'month']
    ordering      = ['scheduled_date']
    search_fields = ['assignment__public_space_name']


@admin.register(Intervention)
class InterventionAdmin(admin.ModelAdmin):
    list_display  = ['assignment', 'execution_date', 'intervention_type', 'recorded_by']
    list_filter   = ['intervention_type']
    ordering      = ['-execution_date']
    search_fields = ['assignment__public_space_name', 'recorded_by']


@admin.register(SLAAlert)
class SLAAlertAdmin(admin.ModelAdmin):
    list_display    = [
        'id', 'complaint_id', 'service_slug', 'route_type',
        'macroroute_code', 'violation', 'distance_meters', 'confidence', 'generated_at',
    ]
    list_filter     = ['violation', 'service_slug', 'route_type', 'confidence']
    ordering        = ['-generated_at']
    readonly_fields = [
        'complaint_id', 'service_slug', 'route_type', 'route_id',
        'macroroute_code', 'violation', 'distance_meters', 'days_since_intervention',
        'confidence', 'generated_at',
    ]
    search_fields   = ['complaint_id', 'macroroute_code']

    def has_add_permission(self, request):    return False
    def has_change_permission(self, request, obj=None): return False


@admin.register(ServiceContent)
class ServiceContentAdmin(admin.ModelAdmin):
    list_display  = ['service', 'icon', 'updated_at']
    search_fields = ['service__name', 'summary']
    autocomplete_fields = ['service']


@admin.register(AspectContent)
class AspectContentAdmin(admin.ModelAdmin):
    list_display  = ['aspect', 'icon', 'response_time', 'updated_at']
    search_fields = ['aspect__description']
    list_filter   = ['aspect__service']
    autocomplete_fields = ['aspect']


@admin.register(CommuneMetric)
class CommuneMetricAdmin(admin.ModelAdmin):
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
