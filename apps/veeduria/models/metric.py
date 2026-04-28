from django.db import models


class MetricByCommune(models.Model):
    """
    Caché estadístico precalculado por comuna y servicio.
    Alimenta el heatmap del dashboard sin queries costosas.

    Recalculada síncronamente tras cada nueva SLAAlert (Fase 1).
    En Fase 2 se mueve a tarea Celery asíncrona.

    Colores del heatmap:
      violation_rate > 0.70 → rojo   (crítico)
      violation_rate > 0.40 → naranja (atención)
      violation_rate ≤ 0.40 → verde  (conforme)
    """
    # Soft FK a core_commune
    commune_id              = models.IntegerField()
    commune_name            = models.CharField(max_length=50)
    service_slug            = models.CharField(max_length=100)

    # Contadores precalculados
    total_complaints        = models.IntegerField(default=0)
    total_alerts            = models.IntegerField(default=0)
    total_violations        = models.IntegerField(default=0)
    violation_rate          = models.FloatField(
        default=0.0,
        help_text='Fracción 0.0–1.0. violations / alerts',
    )
    period                  = models.DateField(
        help_text='Primer día del mes calculado',
    )
    updated_at              = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'vee_metric_by_commune'
        ordering            = ['-period', 'commune_id']
        verbose_name        = 'Métrica por comuna'
        verbose_name_plural = 'Métricas por comuna'
        unique_together     = [['commune_id', 'service_slug', 'period']]
        indexes = [
            models.Index(
                fields=['period', 'service_slug'],
                name='idx_vee_metric_period',
            ),
        ]

    def __str__(self):
        return f'C{self.commune_id} · {self.service_slug} · {self.period}'
