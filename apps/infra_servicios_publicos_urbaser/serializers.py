from rest_framework import serializers

from .models import (
    SweepingMacroRoute,
    SweepingMicroRoute,
    GreenZoneAssignment,
)


class SweepingMacroRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SweepingMacroRoute
        fields = [
            'id', 'code', 'name', 'zone_type',
            'communes_text', 'days_text', 'schedule_text',
            'start_time', 'end_time', 'active',
        ]


class SweepingMicroRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SweepingMicroRoute
        fields = [
            'id', 'macroroute', 'layer',
            'neighborhood_id', 'neighborhood_name', 'active',
        ]


class GreenZoneAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = GreenZoneAssignment
        fields = [
            'id', 'public_space_id', 'public_space_name',
            'external_id', 'cycle_days', 'active',
        ]
