from rest_framework.permissions import BasePermission

from .roles import ROLE_COORDINADOR, ROLE_VEEDOR, user_role


class IsStaff(BasePermission):
    """Authenticated user belonging to any of the alcaldía staff groups."""

    message = 'Se requiere autenticación como personal de la alcaldía.'

    def has_permission(self, request, view):
        return user_role(request.user) is not None


class IsCoordinator(BasePermission):
    """Only coordinador role (superusers also map to coordinador)."""

    message = 'Solo coordinadores pueden ejecutar esta acción.'

    def has_permission(self, request, view):
        return user_role(request.user) == ROLE_COORDINADOR


class IsVeedor(BasePermission):
    """Only veedor role."""

    message = 'Solo veedores pueden ejecutar esta acción.'

    def has_permission(self, request, view):
        return user_role(request.user) == ROLE_VEEDOR
