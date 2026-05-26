from django.urls import path

from .views import StaffLoginView, StaffMeView, StaffRefreshView

urlpatterns = [
    path('login/', StaffLoginView.as_view(), name='staff-login'),
    path('refresh/', StaffRefreshView.as_view(), name='staff-refresh'),
    path('me/', StaffMeView.as_view(), name='staff-me'),
]
