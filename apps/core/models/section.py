from django.db import models


class Section(models.Model):
    """
    Sección/empresa/secretaría que presta servicios públicos en la Alcaldía.
    Catálogo administrativo. Cada sección es dueña de su propio modelo de
    Service y Aspect dentro de su app Django.

    Ejemplos: Urbaser (aseo), Vivienda, Cultura, Acueducto.
    """
    code        = models.CharField(
        max_length=20, unique=True,
        help_text='Identificador estable. Ej: urbaser, vivienda, cultura',
    )
    name        = models.CharField(
        max_length=100,
        help_text='Nombre legal o público. Ej: Urbaser S.A. E.S.P.',
    )
    slug        = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    app_label   = models.CharField(
        max_length=100, blank=True,
        help_text='Django app label que registra el ServiceProvider de esta sección',
    )
    active      = models.BooleanField(default=True)
    order       = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table            = 'core_section'
        ordering            = ['order', 'name']
        verbose_name        = 'Sección'
        verbose_name_plural = 'Secciones'

    def __str__(self):
        return self.name
