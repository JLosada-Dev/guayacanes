from django.db import models


class Service(models.Model):
    """
    Catálogo de servicios públicos prestados por Urbaser.
    Cargado con apps/infra_servicios_publicos_urbaser/fixtures/services.json
    Fase 1 activos: sweeping-cleaning, green-zones
    Fase 2 inactivos: waste-collection, street-washing, tree-pruning

    section_slug es soft FK a core.Section. Snapshot 'urbaser' constante
    aquí — cada app de sección tiene su propio Service con su section_slug.
    """
    name        = models.CharField(max_length=100, unique=True)
    slug        = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    active      = models.BooleanField(default=True)
    order       = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table            = 'urbaser_service'
        ordering            = ['order', 'name']
        verbose_name        = 'Servicio Urbaser'
        verbose_name_plural = 'Servicios Urbaser'

    def __str__(self):
        return self.name


class Aspect(models.Model):
    """
    Subcategorías de queja por servicio Urbaser.
    Cargado con apps/infra_servicios_publicos_urbaser/fixtures/aspects.json

    Sweeping (7): scope, frequency, cleanliness, sand-residue,
                  weed-removal, bins, quality
    Green zones (4): cutting-not-done, frequency-missed,
                     pruning-waste-left, area-deteriorated
    """
    service     = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name='aspects',
    )
    slug        = models.SlugField()
    description = models.CharField(max_length=200)
    active      = models.BooleanField(default=True)

    class Meta:
        db_table            = 'urbaser_aspect'
        ordering            = ['service', 'description']
        verbose_name        = 'Aspecto Urbaser'
        verbose_name_plural = 'Aspectos Urbaser'
        unique_together     = [['service', 'slug']]

    def __str__(self):
        return f'{self.service.name} — {self.description}'
