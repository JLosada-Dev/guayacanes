from django.db import models


class SLAAlert(models.Model):
    """
    Resultado del cruce espacial generado por un handler de servicio.
    Modelo transversal: cada app de servicio crea sus alertas aquí
    desde su propio handler conectado a complaint_created.

    NUNCA se crea manualmente.

    El campo route_type es libre (CharField) en lugar de choices para
    que cada servicio aporte sus propios tipos sin obligar a una
    migración en veeduría. Convención: prefijar con el dominio
    (`urbaser.sweeping_microroute`, `urbaser.green_zone`,
    `vivienda.illegal_construction`, etc.).

    extra_int y extra_data permiten campos específicos por servicio
    sin forzar el esquema base. Convención: claves prefijadas por
    dominio para evitar choques.
    """
    CONFIDENCE_CHOICES = [
        ('high',   'Alta — coordenada GPS'),
        ('medium', 'Media — pin manual'),
        ('low',    'Baja — centroide barrio'),
    ]

    # Soft FK a vee_complaint
    complaint_id              = models.IntegerField(db_index=True)
    service_slug              = models.CharField(max_length=100)

    # Qué ruta o zona fue afectada
    route_type                = models.CharField(
        max_length=50,
        help_text='Tipo libre por servicio. Ej: urbaser.sweeping_microroute',
    )
    route_id                  = models.IntegerField()
    route_label               = models.CharField(
        max_length=50, blank=True,
        help_text='Etiqueta legible para reportes. Ej: código PPS B211',
    )

    # Resultado del análisis
    violation                 = models.BooleanField()
    distance_meters           = models.FloatField(
        null=True, blank=True,
        help_text='Distancia en metros entre la denuncia y la ruta',
    )
    extra_int                 = models.IntegerField(
        null=True, blank=True,
        help_text='Campo entero genérico por servicio. Ej: días desde último corte',
    )
    extra_data                = models.JSONField(
        default=dict, blank=True,
        help_text='Metadatos adicionales por servicio. Claves prefijadas por dominio',
    )
    confidence                = models.CharField(
        max_length=6,
        choices=CONFIDENCE_CHOICES,
        default='high',
    )
    generated_at              = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'vee_sla_alert'
        ordering            = ['-generated_at']
        verbose_name        = 'Alerta SLA'
        verbose_name_plural = 'Alertas SLA'
        indexes = [
            models.Index(fields=['complaint_id'],  name='idx_vee_alert_complaint'),
            models.Index(fields=['violation'],     name='idx_vee_alert_violation'),
            models.Index(fields=['service_slug'],  name='idx_vee_alert_service'),
            models.Index(fields=['generated_at'],  name='idx_vee_alert_date'),
            models.Index(fields=['route_type', 'route_id'], name='idx_vee_alert_route'),
        ]

    def __str__(self):
        estado = 'INCUMPLIMIENTO' if self.violation else 'Conforme'
        return f'Alerta #{self.id} — {estado} ({self.route_type})'
