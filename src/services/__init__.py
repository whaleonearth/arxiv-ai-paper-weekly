"""Services package for coordinating paper discovery."""

from .paper_discovery import (
    PaperDiscoveryService,
    DiscoveryConfig,
    DiscoveryResult,
    create_discovery_service
)

__all__ = [
    "PaperDiscoveryService",
    "DiscoveryConfig", 
    "DiscoveryResult",
    "create_discovery_service"
] 