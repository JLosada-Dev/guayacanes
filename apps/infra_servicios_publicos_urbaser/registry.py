"""
ServiceProvider de Urbaser.
Implementa el contrato apps.core.registry.ServiceProvider y se registra
desde apps.py: ready().
"""
from apps.core.models import Section
from apps.core.registry import ServiceProvider, ServiceInfo, AspectInfo

from .models import Service, Aspect


class UrbaserServiceProvider:
    section_slug = 'urbaser'

    def _section_name(self) -> str:
        # Resuelto perezosamente porque Section puede no estar cargada
        # cuando el provider se construye en ready(); cacheamos el primer hit.
        if not hasattr(self, '_cached_section_name'):
            try:
                section = Section.objects.get(slug=self.section_slug)
                self._cached_section_name = section.name
            except Section.DoesNotExist:
                self._cached_section_name = 'Urbaser'
        return self._cached_section_name

    def get_services(self) -> list[ServiceInfo]:
        section_name = self._section_name()
        services = (
            Service.objects.filter(active=True)
            .select_related('content')
            .order_by('order', 'name')
        )
        return [
            ServiceInfo(
                section_slug = self.section_slug,
                section_name = section_name,
                slug         = s.slug,
                name         = s.name,
                description  = s.description,
                active       = s.active,
                order        = s.order,
                content      = self._service_content(s),
            )
            for s in services
        ]

    def get_aspects(self, service_slug: str) -> list[AspectInfo]:
        aspects = (
            Aspect.objects
            .filter(active=True, service__slug=service_slug)
            .select_related('content', 'service')
        )
        return [
            AspectInfo(
                section_slug = self.section_slug,
                service_slug = service_slug,
                slug         = a.slug,
                description  = a.description,
                active       = a.active,
                content      = self._aspect_content(a),
            )
            for a in aspects
        ]

    @staticmethod
    def _service_content(service) -> dict | None:
        c = getattr(service, 'content', None)
        if c is None:
            return None
        return {
            'icon':             c.icon,
            'summary':          c.summary,
            'full_description': c.full_description,
            'frequency':        c.frequency,
            'citizen_rights':   c.citizen_rights,
        }

    @staticmethod
    def _aspect_content(aspect) -> dict | None:
        c = getattr(aspect, 'content', None)
        if c is None:
            return None
        return {
            'icon':            c.icon,
            'what_is':         c.what_is,
            'how_to_evidence': c.how_to_evidence,
            'response_time':   c.response_time,
        }
