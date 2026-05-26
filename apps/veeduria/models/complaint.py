from django.contrib.gis.db import models


class Complaint(models.Model):
    """
    Denuncia ciudadana anónima — modelo transversal a todos los
    servicios públicos de la Alcaldía.

    REGLA CRÍTICA: location NUNCA puede ser NULL.
    El serializer implementa la cascada:
      1. GPS automático del dispositivo  → location_source='gps'
      2. Pin manual en React-Leaflet     → location_source='manual'
      3. Centroide del barrio            → location_source='centroid'
    Si ninguno está disponible → error 400, rechazar el POST.

    Soft FKs a core (Service, Aspect, Commune, Neighborhood) — validadas
    en serializer, sin FK dura en BD. Se guardan snapshots de texto
    para que el registro sea autocontenido aunque el catálogo cambie.
    """

    LOCATION_SOURCE_CHOICES = [
        ('gps',      'GPS automático'),
        ('manual',   'Pin manual en mapa'),
        ('centroid', 'Centroide del barrio'),
    ]

    STATUS_CHOICES = [
        ('received',     'Recibida'),
        ('under_review', 'En revisión'),
        ('closed',       'Cerrada'),
    ]

    # ── Qué ──────────────────────────────────────────────────────
    section_slug        = models.CharField(max_length=20, blank=True)
    section_name        = models.CharField(max_length=100, blank=True)
    service_slug        = models.CharField(max_length=100)
    service_name        = models.CharField(max_length=100, blank=True)
    aspect_slug         = models.CharField(max_length=100, blank=True)
    aspect_description  = models.CharField(max_length=200)

    # ── Dónde ────────────────────────────────────────────────────
    commune_id          = models.IntegerField(null=True, blank=True)
    commune_name        = models.CharField(max_length=50, blank=True)
    neighborhood_id     = models.IntegerField(null=True, blank=True)
    neighborhood_name   = models.CharField(max_length=150, blank=True)
    address             = models.CharField(
        max_length=300, blank=True,
        help_text='Dirección textual opcional para refinar la ubicación (calle, número, referencia).',
    )
    is_rural            = models.BooleanField(default=False)
    hamlet_name         = models.CharField(
        max_length=150, blank=True,
        help_text='Nombre de la vereda si is_rural=True'
    )

    # ── Coordenada — NUNCA NULL ───────────────────────────────────
    location            = models.PointField(srid=4326)
    location_source     = models.CharField(
        max_length=10,
        choices=LOCATION_SOURCE_CHOICES,
        default='gps',
    )

    # ── Contexto ─────────────────────────────────────────────────
    custom_aspect_description = models.CharField(
        max_length=200, blank=True,
        help_text='Descripción del problema cuando aspect_slug="other-issue".',
    )
    description         = models.TextField(blank=True)
    status              = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='received',
    )
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'vee_complaint'
        ordering            = ['-created_at']
        verbose_name        = 'Denuncia ciudadana'
        verbose_name_plural = 'Denuncias ciudadanas'
        indexes = [
            models.Index(fields=['section_slug'], name='idx_vee_complaint_section'),
            models.Index(fields=['service_slug'], name='idx_vee_complaint_service'),
            models.Index(fields=['status'],       name='idx_vee_complaint_status'),
            models.Index(fields=['created_at'],   name='idx_vee_complaint_date'),
            models.Index(fields=['commune_id'],   name='idx_vee_complaint_commune'),
        ]

    def __str__(self):
        return f'Denuncia #{self.id} — {self.service_slug} ({self.status})'


class Evidence(models.Model):
    """
    Fotografía adjunta a una denuncia.
    Guardada en media_local/complaints/YYYY/MM/
    """
    complaint   = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='evidence',
    )
    image       = models.ImageField(upload_to='complaints/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'vee_evidence'
        verbose_name        = 'Evidencia fotográfica'
        verbose_name_plural = 'Evidencias fotográficas'

    def __str__(self):
        return f'Foto denuncia #{self.complaint_id}'
