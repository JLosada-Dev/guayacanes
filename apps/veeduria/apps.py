from django.apps import AppConfig


class VeeduriaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name               = 'apps.veeduria'
    verbose_name       = 'Veeduría ciudadana'

    def ready(self):
        # Registrar el receiver post_save de Complaint que emite complaint_created
        import apps.veeduria.signals  # noqa
