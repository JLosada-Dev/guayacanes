"""
Señales públicas de veeduría.

complaint_created es el contrato por el cual cada app de servicio
público se entera de que se creó una denuncia y decide si le aplica
ejecutar su lógica SLA. Veeduría no conoce ningún servicio en
particular — solo emite el evento con todos los datos relevantes.

Ver docs/refactor/REGISTRY-PATTERN.md para el patrón completo de
registro de handlers en cada app de servicio.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal

from .models import Complaint


complaint_created = Signal()


@receiver(post_save, sender=Complaint)
def on_complaint_saved(sender, instance, created, **kwargs):
    """
    Emite complaint_created solo en creación, no en updates.
    Cada app de servicio decide si esta denuncia le corresponde
    filtrando por service_slug en su receiver.
    """
    if not created:
        return

    complaint_created.send(
        sender           = Complaint,
        complaint_id     = instance.id,
        service_slug     = instance.service_slug,
        aspect_slug      = instance.aspect_slug,
        location         = instance.location,
        created_at       = instance.created_at,
        location_source  = instance.location_source,
        commune_id       = instance.commune_id,
    )
