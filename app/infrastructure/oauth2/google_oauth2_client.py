"""Google OAuth2 Client Implementation."""

import json
import structlog
from typing import Dict, Any
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.application.ports.outbound.oauth2_client_port import OAuth2ClientPort
from app.domain.errors.token_errors import TokenRefreshError

logger = structlog.get_logger()


class GoogleOAuth2Client(OAuth2ClientPort):
    """Google OAuth2 implementation of OAuth2ClientPort."""
    
    def __init__(self, client_secrets_file: str):
        self.client_secrets_file = client_secrets_file
    
    async def refresh_token(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Refresh OAuth2 token."""
        logger.info("oauth2_refresh_started")
        
        try:
            # Create credentials from token data
            creds = Credentials.from_authorized_user_info(token_data)
            
            # Refresh token
            creds.refresh(Request())
            
            # Build new token data
            new_token_data = {
                "access_token": creds.token,
                "refresh_token": creds.refresh_token,
                "expiry": creds.expiry.replace(tzinfo=timezone.utc).isoformat() if creds.expiry else None,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes
            }
            
            logger.info("oauth2_refresh_success", new_expiry=new_token_data["expiry"])
            return new_token_data
            
        except Exception as e:
            logger.error("oauth2_refresh_failed", error=str(e))
            raise TokenRefreshError(f"Failed to refresh OAuth2 token: {str(e)}") from e
    
    async def validate_token(self, token_data: Dict[str, Any]) -> bool:
        """Validate OAuth2 token."""
        logger.info("oauth2_validate_started")
        
        try:
            # Create credentials from token data
            creds = Credentials.from_authorized_user_info(token_data)
            
            # Check if token is valid
            is_valid = creds.valid
            
            # If expired but has refresh token, try to refresh
            if not is_valid and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    is_valid = creds.valid
                except Exception:
                    is_valid = False
            
            logger.info("oauth2_validate_result", is_valid=is_valid)
            return is_valid
            
        except Exception as e:
            logger.error("oauth2_validate_failed", error=str(e))
            return False
    
    async def get_token_info(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get token information."""
        logger.info("oauth2_get_token_info_started")
        
        try:
            # Create credentials from token data
            creds = Credentials.from_authorized_user_info(token_data)
            
            # Build Gmail service
            service = build('gmail', 'v1', credentials=creds)
            
            # Get user profile
            profile = service.users().getProfile(userId='me').execute()
            
            # Build token info
            token_info = {
                "email": profile.get('emailAddress'),
                "messages_total": profile.get('messagesTotal', 0),
                "threads_total": profile.get('threadsTotal', 0),
                "history_id": profile.get('historyId'),
                "is_valid": creds.valid,
                "expires_in_seconds": int((creds.expiry - datetime.now(timezone.utc)).total_seconds()) if creds.expiry else None
            }
            
            logger.info("oauth2_get_token_info_success", email=token_info["email"])
            return token_info
            
        except Exception as e:
            logger.error("oauth2_get_token_info_failed", error=str(e))
            raise TokenRefreshError(f"Failed to get token info: {str(e)}") from e
