from django.urls import path
from rest_framework.routers import DefaultRouter

from .statistics import StatisticsView
from .views import (
    ComplaintViewSet, EvidenceViewSet,
    SLAAlertViewSet, MetricByCommuneViewSet,
)

router = DefaultRouter()
router.register(r'complaints', ComplaintViewSet,         basename='complaint')
router.register(r'evidence',   EvidenceViewSet,          basename='evidence')
router.register(r'alerts',     SLAAlertViewSet,          basename='alert')
router.register(r'metrics',    MetricByCommuneViewSet,   basename='metric')

urlpatterns = [
    *router.urls,
    path('statistics/', StatisticsView.as_view(), name='statistics'),
]
