from django.contrib.gis import admin
from .models import (
    Service, Aspect,
    SweepingMacroRoute, SweepingMicroRoute,
    GreenZoneAssignment, CuttingSchedule, Intervention,
    ServiceContent, AspectContent,
)


class ServiceContentInline(admin.StackedInline):
    model       = ServiceContent
    extra       = 1
    fields      = ['icon', 'summary', 'full_description', 'frequency', 'citizen_rights']


class AspectContentInline(admin.StackedInline):
    model       = AspectContent
    extra       = 1
    fields      = ['icon', 'what_is', 'how_to_evidence', 'response_time']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display  = ['name', 'slug', 'active', 'order']
    ordering      = ['order']
    search_fields = ['name', 'slug']
    list_filter   = ['active']
    inlines       = [ServiceContentInline]


@admin.register(Aspect)
class AspectAdmin(admin.ModelAdmin):
    list_display  = ['description', 'service', 'slug', 'active']
    ordering      = ['service__order', 'description']
    search_fields = ['description', 'slug']
    list_filter   = ['service', 'active']
    inlines       = [AspectContentInline]


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
