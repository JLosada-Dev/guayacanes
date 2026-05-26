from django.conf import settings
from django.db import models

from .complaint import Complaint


class ComplaintStatusEvent(models.Model):
    """Audit log entry: one row per status transition on a Complaint.

    ``actor_role`` is snapshotted at creation time so the event remains
    truthful even if the user later changes groups (or is deleted).
    """

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='status_events',
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='complaint_status_events',
    )
    actor_username = models.CharField(max_length=150, blank=True)
    actor_full_name = models.CharField(max_length=200, blank=True)
    actor_role = models.CharField(max_length=20, blank=True)
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vee_complaint_status_event'
        ordering = ['-created_at']
        verbose_name = 'Evento de cambio de estado'
        verbose_name_plural = 'Eventos de cambio de estado'
        indexes = [
            models.Index(fields=['complaint'], name='idx_vee_evt_complaint'),
            models.Index(fields=['created_at'], name='idx_vee_evt_created'),
        ]

    def __str__(self):
        return (
            f'#{self.complaint_id} {self.from_status}→{self.to_status} '
            f'por {self.actor_username or "?"}'
        )
