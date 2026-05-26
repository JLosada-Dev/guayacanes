from django.contrib.gis.db import models


class PublicSpace(models.Model):
    """
    Polígono de espacio público del POT Popayán.
    Activo geográfico genérico — no asume un servicio específico.

    Cualquier app de servicio puede referenciar un PublicSpace por
    soft FK y agregarle su propia lógica operativa. Por ejemplo,
    urbaser.GreenZoneAssignment usa esto para registrar zonas verdes
    bajo su contrato; mañana otro servicio podría usar los mismos
    polígonos con otra cadencia sin chocar.

    Fuentes (combinadas en load_public_spaces):
      U19_ESPACIO_PUBLICO1.shp  →  source_layer='U19_EP1'   (2)
      U19_ESPACIO_PUBLICO2.shp  →  source_layer='U19_EP2'   (11)
      U19_ESPACIO_PUBLICO3.shp  →  source_layer='U19_EP3'   (96)
      U19_ESPACIO_PUBLICO5.shp  →  source_layer='U19_EP5'   (72)
      SEPARADOR.shp             →  source_layer='SEPARADOR' (132)

    CRS original: PCS_CAUCA_POPAYAN  →  almacenado en EPSG:4326.
    """
    SPACE_TYPE_CHOICES = [
        ('park',         'Parque público'),
        ('road_divider', 'Separador vial'),
        ('corridor',     'Corredor verde'),
        ('node',         'Nodo de espacio público'),
        ('sports',       'Polideportivo'),
        ('other',        'Otro'),
    ]

    external_id       = models.IntegerField(
        unique=True,
        help_text='ID compuesto por capa fuente (10001+, 20001+, ...)',
    )
    name              = models.CharField(max_length=300)
    space_type        = models.CharField(
        max_length=20,
        choices=SPACE_TYPE_CHOICES,
        default='other',
    )
    area_sqm          = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        help_text='Área en m² calculada en EPSG:3116',
    )
    source_layer      = models.CharField(
        max_length=50, blank=True,
        help_text='Capa POT de origen. Ej: U19_EP3, SEPARADOR',
    )
    # Soft FK a core_neighborhood
    neighborhood_id   = models.IntegerField(null=True, blank=True)
    neighborhood_name = models.CharField(max_length=150, blank=True)
    active            = models.BooleanField(default=True)
    geom              = models.MultiPolygonField(srid=4326)

    class Meta:
        db_table            = 'geodata_public_space'
        ordering            = ['name']
        verbose_name        = 'Espacio público'
        verbose_name_plural = 'Espacios públicos'

    def __str__(self):
        return f'{self.name} (ID {self.external_id})'
