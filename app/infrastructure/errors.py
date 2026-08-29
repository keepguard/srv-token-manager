"""RFC 7807 Problem Details for HTTP APIs."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from fastapi.responses import JSONResponse


@dataclass
class ProblemDetail:
    """RFC 7807 Problem Detail."""
    type: str
    title: str
    status: int
    detail: str
    instance: Optional[str] = None
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
        }
        
        if self.instance:
            result["instance"] = self.instance
        cid = self.correlation_id or self.trace_id
        if cid:
            result["correlationId"] = cid
        if self.context:
            result["context"] = self.context
            
        return result

    def to_response(self) -> JSONResponse:
        """Convert to FastAPI JSONResponse."""
        return JSONResponse(
            status_code=self.status,
            content=self.to_dict(),
            headers={"Content-Type": "application/problem+json"}
        )


# Erros pré-definidos
def create_validation_error(detail: str, instance: str = None, trace_id: str = None, context: Dict[str, Any] = None) -> ProblemDetail:
    """Create validation error."""
    return ProblemDetail(
        type="https://keepguard.com/problems/validation-error",
        title="Erro de validação",
        status=400,
        detail=detail,
        instance=instance,
        trace_id=trace_id,
        context=context or {}
    )


def create_not_found_error(detail: str, instance: str = None, trace_id: str = None) -> ProblemDetail:
    """Create not found error."""
    return ProblemDetail(
        type="https://keepguard.com/problems/not-found",
        title="Recurso não encontrado",
        status=404,
        detail=detail,
        instance=instance,
        trace_id=trace_id
    )


def create_internal_server_error(detail: str, instance: str = None, trace_id: str = None) -> ProblemDetail:
    """Create internal server error."""
    return ProblemDetail(
        type="https://keepguard.com/problems/internal-error",
        title="Erro interno do servidor",
        status=500,
        detail=detail,
        instance=instance,
        trace_id=trace_id
    )


def create_service_unavailable_error(detail: str, instance: str = None, trace_id: str = None) -> ProblemDetail:
    """Create service unavailable error."""
    return ProblemDetail(
        type="https://keepguard.com/problems/service-unavailable",
        title="Serviço indisponível",
        status=503,
        detail=detail,
        instance=instance,
        trace_id=trace_id
    )


def create_token_refresh_error(detail: str, email: str, instance: str = None, trace_id: str = None) -> ProblemDetail:
    """Create token refresh error."""
    return ProblemDetail(
        type="https://keepguard.com/problems/token-refresh-error",
        title="Erro ao atualizar token",
        status=500,
        detail=detail,
        instance=instance,
        trace_id=trace_id,
        context={"email": email}
    )


def create_unauthorized_error(detail: str, instance: str = None, trace_id: str = None) -> ProblemDetail:
    """Create unauthorized error."""
    return ProblemDetail(
        type="https://keepguard.com/problems/unauthorized",
        title="Não autorizado",
        status=401,
        detail=detail,
        instance=instance,
        trace_id=trace_id
    )


def create_redis_error(detail: str, operation: str, instance: str = None, trace_id: str = None) -> ProblemDetail:
    """Create Redis error."""
    return ProblemDetail(
        type="https://keepguard.com/problems/redis-error",
        title="Erro no Redis",
        status=500,
        detail=detail,
        instance=instance,
        trace_id=trace_id,
        context={"operation": operation}
    )

