from rest_framework.routers import DefaultRouter

from .views import (
    SweepingMacroRouteViewSet,
    SweepingMicroRouteViewSet,
    GreenZoneAssignmentViewSet,
)

router = DefaultRouter()
router.register(r'sweeping-macroroutes',    SweepingMacroRouteViewSet,    basename='sweeping-macroroute')
router.register(r'sweeping-microroutes',    SweepingMicroRouteViewSet,    basename='sweeping-microroute')
router.register(r'green-zone-assignments',  GreenZoneAssignmentViewSet,   basename='green-zone-assignment')

urlpatterns = router.urls
