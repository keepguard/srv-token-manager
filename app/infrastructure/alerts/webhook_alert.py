"""Webhook Alert Implementation."""

import httpx
import structlog
from typing import Dict, Any, Optional

from app.application.ports.outbound.alert_port import AlertPort

logger = structlog.get_logger()


class WebhookAlert(AlertPort):
    """Webhook implementation of AlertPort."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url
    
    async def send_alert(self, message: str, level: str = "warning", metadata: Dict[str, Any] = None) -> None:
        """Send alert via webhook."""
        if not self.webhook_url:
            logger.warning("webhook_alert_disabled", message=message, level=level)
            return
        
        logger.info("webhook_alert_started", message=message, level=level)
        
        try:
            # Build payload
            payload = {
                "text": f"[{level.upper()}] Token Manager Alert",
                "attachments": [
                    {
                        "color": self._get_color(level),
                        "fields": [
                            {
                                "title": "Message",
                                "value": message,
                                "short": False
                            }
                        ]
                    }
                ]
            }
            
            # Add metadata if provided
            if metadata:
                payload["attachments"][0]["fields"].append({
                    "title": "Metadata",
                    "value": json.dumps(metadata, indent=2),
                    "short": False
                })
            
            # Send webhook
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()
            
            logger.info("webhook_alert_success", message=message, level=level)
            
        except Exception as e:
            logger.error("webhook_alert_failed", message=message, level=level, error=str(e))
    
    async def send_critical_alert(self, message: str, metadata: Dict[str, Any] = None) -> None:
        """Send critical alert via webhook."""
        await self.send_alert(message, level="critical", metadata=metadata)
    
    def _get_color(self, level: str) -> str:
        """Get color for alert level."""
        colors = {
            "info": "good",
            "warning": "warning",
            "error": "danger",
            "critical": "danger"
        }
        return colors.get(level.lower(), "warning")
