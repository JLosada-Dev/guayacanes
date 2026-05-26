"""Status transition matrix for Complaint.

Keep this file in sync with the frontend mirror at
``frontend-guayacanes/src/lib/transitions.ts``. When edited here, update there
and vice versa.

Rules (per role):

- veedor: progresses a complaint through the operational pipeline up to
  ``escalated``, and can reopen characterization from ``in_field``/``escalated``
  back to ``triaged``. Cannot close (resolved/rejected).
- coordinador: everything a veedor can do, plus closing the complaint
  (``resolved`` / ``rejected``) from any non-final state, and reopening from
  final states back to ``triaged``.
"""

from apps.accounts.roles import ROLE_COORDINADOR, ROLE_VEEDOR

ALL_STATUSES = (
    'received',
    'triaged',
    'in_field',
    'escalated',
    'resolved',
    'rejected',
)

ALLOWED_TRANSITIONS: dict[str, dict[str, set[str]]] = {
    ROLE_VEEDOR: {
        'received':  {'triaged'},
        'triaged':   {'in_field'},
        'in_field':  {'escalated', 'triaged'},
        'escalated': {'triaged'},
        'resolved':  set(),
        'rejected':  set(),
    },
    ROLE_COORDINADOR: {
        'received':  {'triaged', 'rejected'},
        'triaged':   {'in_field', 'resolved', 'rejected'},
        'in_field':  {'escalated', 'triaged', 'resolved', 'rejected'},
        'escalated': {'triaged', 'resolved', 'rejected'},
        'resolved':  {'triaged'},
        'rejected':  {'triaged'},
    },
}


def can_transition(from_status: str, to_status: str, role: str | None) -> bool:
    if not role:
        return False
    role_map = ALLOWED_TRANSITIONS.get(role, {})
    return to_status in role_map.get(from_status, set())


def allowed_next_states(from_status: str, role: str | None) -> list[str]:
    if not role:
        return []
    return sorted(ALLOWED_TRANSITIONS.get(role, {}).get(from_status, set()))
