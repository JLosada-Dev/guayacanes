"""Role constants for the alcaldía staff portal.

Single source of truth for role/group names. Used by permissions, seeders,
serializers and the transition matrix.
"""

ROLE_VEEDOR = 'veedor'
ROLE_COORDINADOR = 'coordinador'

ALL_ROLES = (ROLE_VEEDOR, ROLE_COORDINADOR)


def user_role(user) -> str | None:
    """Return the first staff role the user belongs to, or None."""
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return ROLE_COORDINADOR
    group_names = set(user.groups.values_list('name', flat=True))
    for role in ALL_ROLES:
        if role in group_names:
            return role
    return None
