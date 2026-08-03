"""Teacher-aligned experimental cloud API Proxy boundary."""

from .contracts import (
    ADAPTER_ID,
    CAPABILITY,
    PROXY_CONTRACT_VERSION,
    CloudProxyRequestEnvelope,
    PaperSearchV01Request,
    ProxyAuthorizationScope,
    ProxyCapabilityToken,
    ProxyOperation,
    ProxyOperationStatus,
    ProxyUsage,
    build_operation_id,
)
from .errors import ProxyError
from .fake_adapter import DeterministicFakePaperSearchAdapter
from .in_memory import InMemoryProxyDatabase, InMemoryProxyUnitOfWork
from .service import CloudAPIProxyService

__all__ = [
    "ADAPTER_ID",
    "CAPABILITY",
    "PROXY_CONTRACT_VERSION",
    "CloudAPIProxyService",
    "CloudProxyRequestEnvelope",
    "DeterministicFakePaperSearchAdapter",
    "InMemoryProxyDatabase",
    "InMemoryProxyUnitOfWork",
    "PaperSearchV01Request",
    "ProxyAuthorizationScope",
    "ProxyCapabilityToken",
    "ProxyError",
    "ProxyOperation",
    "ProxyOperationStatus",
    "ProxyUsage",
    "build_operation_id",
]
