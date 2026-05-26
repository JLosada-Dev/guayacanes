"""
Registro global de proveedores de catálogos de servicios.

Cada app de sección (urbaser, vivienda, cultura, ...) implementa el
Protocol ServiceProvider y se registra desde su AppConfig.ready().
Los endpoints /core/services y /core/aspects iteran este registro
para construir la respuesta agregada.

Ver docs/refactor/SECTION-REGISTRY.md para el diseño completo.
"""
from dataclasses import asdict, dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ServiceInfo:
    section_slug: str
    section_name: str
    slug:         str
    name:         str
    description:  str
    active:       bool
    order:        int
    content:      dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AspectInfo:
    section_slug: str
    service_slug: str
    slug:         str
    description:  str
    active:       bool
    content:      dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@runtime_checkable
class ServiceProvider(Protocol):
    """
    Contrato que implementa cada app de sección.

    section_slug debe coincidir con un Section.slug existente en core.
    """
    section_slug: str

    def get_services(self) -> list[ServiceInfo]: ...
    def get_aspects(self, service_slug: str) -> list[AspectInfo]: ...


_providers: dict[str, ServiceProvider] = {}


def register(provider: ServiceProvider) -> None:
    """
    Registra un provider. Idempotente: registrarlo dos veces (por ej. en
    autoreload) no duplica.
    """
    if not isinstance(provider, ServiceProvider):
        raise TypeError(
            f'{provider!r} no implementa el Protocol ServiceProvider'
        )
    _providers[provider.section_slug] = provider


def unregister(section_slug: str) -> None:
    """Útil sobre todo en tests."""
    _providers.pop(section_slug, None)


def all_providers() -> list[ServiceProvider]:
    return list(_providers.values())


def get_provider(section_slug: str) -> ServiceProvider | None:
    return _providers.get(section_slug)
