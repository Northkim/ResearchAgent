"""Thread-safe in-memory Proxy persistence used only by focused tests."""

from __future__ import annotations

from dataclasses import replace
from threading import RLock

from .contracts import ProxyCapabilityToken, ProxyOperation, ProxyOperationStatus


class InMemoryProxyDatabase:
    def __init__(self) -> None:
        self.tokens: dict[str, ProxyCapabilityToken] = {}
        self.digest_index: dict[str, str] = {}
        self.operations: dict[str, ProxyOperation] = {}
        self.idempotency_index: dict[tuple[str, str], str] = {}
        self.lock = RLock()


class InMemoryProxyRepository:
    def __init__(self, database: InMemoryProxyDatabase) -> None:
        self.database = database

    def add_token(self, token: ProxyCapabilityToken) -> None:
        if token.scope.token_id in self.database.tokens or token.token_digest_sha256 in self.database.digest_index:
            raise ValueError("duplicate Proxy token identity")
        self.database.tokens[token.scope.token_id] = token
        self.database.digest_index[token.token_digest_sha256] = token.scope.token_id

    def find_token_by_digest(self, digest: str) -> ProxyCapabilityToken | None:
        token_id = self.database.digest_index.get(digest)
        return self.database.tokens.get(token_id) if token_id else None

    def get_token(self, token_id: str, *, for_update: bool = False) -> ProxyCapabilityToken | None:
        del for_update
        return self.database.tokens.get(token_id)

    def save_token(self, token: ProxyCapabilityToken) -> None:
        if token.scope.token_id not in self.database.tokens:
            raise ValueError("Proxy token not found")
        self.database.tokens[token.scope.token_id] = token

    def get_operation(self, operation_id: str) -> ProxyOperation | None:
        return self.database.operations.get(operation_id)

    def find_by_idempotency(self, token_id: str, idempotency_key: str) -> ProxyOperation | None:
        operation_id = self.database.idempotency_index.get((token_id, idempotency_key))
        return self.database.operations.get(operation_id) if operation_id else None

    def add_operation(self, operation: ProxyOperation) -> None:
        key = (operation.token_id, operation.request.idempotency_key)
        if operation.operation_id in self.database.operations or key in self.database.idempotency_index:
            raise ValueError("duplicate Proxy operation identity")
        self.database.operations[operation.operation_id] = operation
        self.database.idempotency_index[key] = operation.operation_id

    def save_operation(self, operation: ProxyOperation) -> None:
        if operation.operation_id not in self.database.operations:
            raise ValueError("Proxy operation not found")
        self.database.operations[operation.operation_id] = operation

    def count_active(self, token_id: str) -> int:
        return sum(
            operation.token_id == token_id and operation.status in {
                ProxyOperationStatus.RECEIVED, ProxyOperationStatus.RUNNING,
            }
            for operation in self.database.operations.values()
        )

    def reconcile_running(self, evidence: str) -> int:
        count = 0
        for operation_id, operation in tuple(self.database.operations.items()):
            if operation.status is ProxyOperationStatus.RUNNING:
                self.database.operations[operation_id] = replace(
                    operation,
                    status=ProxyOperationStatus.RECONCILIATION_REQUIRED,
                    reconciliation_evidence=evidence,
                    error_code="INTERRUPTED_OPERATION",
                ).with_response_checksum()
                count += 1
        return count


class InMemoryProxyUnitOfWork:
    def __init__(self, database: InMemoryProxyDatabase) -> None:
        self.database = database
        self.proxy = InMemoryProxyRepository(database)

    def __enter__(self) -> InMemoryProxyUnitOfWork:
        self.database.lock.acquire()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.database.lock.release()

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None
