from django.apps import AppConfig


class InfraServiciosPublicosUrbaserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name               = 'apps.infra_servicios_publicos_urbaser'
    verbose_name       = 'Infraestructura Servicios Públicos — Urbaser'

    def ready(self):
        # 1) Registrar el ServiceProvider del catálogo (Section registry).
        from apps.core.registry import register
        from .registry import UrbaserServiceProvider
        register(UrbaserServiceProvider())

        # 2) Conectar el handler SLA a la señal pública de veeduría.
        # Patrón documentado en docs/refactor/REGISTRY-PATTERN.md.
        from apps.veeduria.signals import complaint_created
        from . import sla_handlers
        complaint_created.connect(
            sla_handlers.handle_complaint,
            dispatch_uid='urbaser.handle_complaint',
        )
