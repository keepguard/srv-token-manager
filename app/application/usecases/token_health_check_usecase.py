"""Token Health Check Use Case."""

import structlog
from typing import Dict, Any, List

from app.domain.entities.token import Token
from app.application.ports.outbound.token_repository_port import TokenRepositoryPort

logger = structlog.get_logger()


class TokenHealthCheckUseCase:
    """Use case for token health check."""
    
    def __init__(self, repository_port: TokenRepositoryPort):
        self.repository_port = repository_port
    
    async def execute(self) -> Dict[str, Any]:
        """Execute token health check use case."""
        logger.info("token_health_check_started")
        
        try:
            # Get all tokens
            tokens = await self.repository_port.get_all()
            
            # Analyze tokens
            total_tokens = len(tokens)
            valid_tokens = sum(1 for token in tokens if token.is_valid())
            expired_tokens = sum(1 for token in tokens if token.is_expired())
            tokens_needing_refresh = sum(1 for token in tokens if token.needs_refresh())
            
            # Calculate health score
            health_score = self._calculate_health_score(valid_tokens, total_tokens)
            
            # Build health response
            health = {
                "status": "healthy" if health_score >= 0.8 else "degraded" if health_score >= 0.5 else "unhealthy",
                "health_score": health_score,
                "total_tokens": total_tokens,
                "valid_tokens": valid_tokens,
                "expired_tokens": expired_tokens,
                "tokens_needing_refresh": tokens_needing_refresh,
                "tokens": [
                    {
                        "email": str(token.email),
                        "is_valid": token.is_valid(),
                        "expires_in_minutes": token.minutes_until_expiry(),
                        "needs_refresh": token.needs_refresh(),
                        "refresh_count": token.refresh_count
                    }
                    for token in tokens
                ]
            }
            
            logger.info("token_health_check_success", health=health)
            return health
            
        except Exception as e:
            logger.error("token_health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "health_score": 0.0,
                "error": str(e)
            }
    
    def _calculate_health_score(self, valid_tokens: int, total_tokens: int) -> float:
        """Calculate health score based on valid tokens."""
        if total_tokens == 0:
            return 1.0
        
        return valid_tokens / total_tokens
