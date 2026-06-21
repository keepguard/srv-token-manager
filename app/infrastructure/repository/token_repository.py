"""Token Repository Implementation."""

import json
import structlog
from typing import Dict, Any, Optional, List
import os
from datetime import datetime

from app.domain.value_objects.email import Email
from app.domain.entities.token import Token
from app.domain.errors.token_errors import TokenNotFoundError
from app.application.ports.outbound.token_repository_port import TokenRepositoryPort

logger = structlog.get_logger()


class TokenRepository(TokenRepositoryPort):
    """File-based implementation of TokenRepositoryPort."""
    
    def __init__(self, token_file: str):
        self.token_file = token_file
    
    async def get(self, email: Email) -> Optional[Token]:
        """Get token by email."""
        logger.info("repository_get_started", email=str(email))
        
        try:
            if not os.path.exists(self.token_file):
                logger.warning("repository_token_file_not_found", file=self.token_file)
                return None
            
            # Read token file
            with open(self.token_file, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            
            # Create token from data
            token = Token.from_dict(email, token_data)
            
            logger.info("repository_get_success", email=str(email))
            return token
            
        except Exception as e:
            logger.error("repository_get_failed", email=str(email), error=str(e))
            return None
    
    async def save(self, token: Token) -> None:
        """Save token."""
        logger.info("repository_save_started", email=str(token.email))
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            
            # Convert token to dict
            token_data = token.to_dict()
            
            # Write to file
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, indent=2, ensure_ascii=False)
            
            logger.info("repository_save_success", email=str(token.email))
            
        except Exception as e:
            logger.error("repository_save_failed", email=str(token.email), error=str(e))
            raise
    
    async def delete(self, email: Email) -> bool:
        """Delete token by email."""
        logger.info("repository_delete_started", email=str(email))
        
        try:
            if not os.path.exists(self.token_file):
                logger.warning("repository_token_file_not_found", file=self.token_file)
                return False
            
            # Remove file
            os.remove(self.token_file)
            
            logger.info("repository_delete_success", email=str(email))
            return True
            
        except Exception as e:
            logger.error("repository_delete_failed", email=str(email), error=str(e))
            return False
    
    async def exists(self, email: Email) -> bool:
        """Check if token exists."""
        logger.info("repository_exists_started", email=str(email))
        
        try:
            exists = os.path.exists(self.token_file)
            logger.info("repository_exists_result", email=str(email), exists=exists)
            return exists
            
        except Exception as e:
            logger.error("repository_exists_failed", email=str(email), error=str(e))
            return False
    
    async def get_all(self) -> List[Token]:
        """Get all tokens."""
        logger.info("repository_get_all_started")
        
        try:
            tokens = []
            
            if not os.path.exists(self.token_file):
                logger.warning("repository_token_file_not_found", file=self.token_file)
                return tokens
            
            # Read token file
            with open(self.token_file, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            
            # Extract email from token data (assuming it's stored somewhere)
            # For now, we'll use a default email since the file-based approach
            # doesn't store multiple tokens
            email = Email("keepguard.ia@gmail.com")  # Default email
            
            # Create token from data
            token = Token.from_dict(email, token_data)
            tokens.append(token)
            
            logger.info("repository_get_all_success", count=len(tokens))
            return tokens
            
        except Exception as e:
            logger.error("repository_get_all_failed", error=str(e))
            return []
