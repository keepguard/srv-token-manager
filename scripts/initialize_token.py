#!/usr/bin/env python3
"""Script para inicializar token no Redis."""

import asyncio
import json
import redis.asyncio as redis
from datetime import datetime, timedelta
import os


async def initialize_token():
    """Inicializa token no Redis usando token.json existente."""
    
    # Configuração Redis
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_password = os.getenv("REDIS_PASSWORD", "")
    
    # Conectar ao Redis
    redis_client = redis.Redis(
        host=redis_host,
        port=redis_port,
        password=redis_password if redis_password else None,
        decode_responses=True
    )
    
    try:
        # Ler token.json
        token_file = "/Users/rafaelnogueirasoares/Projetos/keepguard/keepguard-backend/backend/srv/srv-token-manager/secure/token.json"
        
        if not os.path.exists(token_file):
            print(f"❌ Arquivo token.json não encontrado: {token_file}")
            return
        
        with open(token_file, 'r') as f:
            token_data = json.load(f)
        
        print(f"📄 Token carregado de: {token_file}")
        
        # Preparar dados para Redis
        email = "keepguard.ia@gmail.com"
        redis_key = f"token:{email}"  # Chave sem prefixo (prefixo será adicionado pelo RedisCache)
        redis_prefix = os.getenv("REDIS_KEY_PREFIX", "local:gmail:token:")
        
        # Calcular TTL (55 minutos)
        ttl_seconds = 3300
        
        # Armazenar no Redis
        await redis_client.setex(
            f"{redis_prefix}{redis_key}",
            ttl_seconds,
            json.dumps(token_data)
        )
        
        print(f"✅ Token armazenado no Redis:")
        print(f"   Key: {redis_prefix}{redis_key}")
        print(f"   TTL: {ttl_seconds} segundos ({ttl_seconds/60:.1f} minutos)")
        print(f"   Email: {email}")
        
        # Verificar se foi armazenado
        stored_data = await redis_client.get(f"{redis_prefix}{redis_key}")
        if stored_data:
            print(f"✅ Verificação: Token encontrado no Redis")
            parsed_data = json.loads(stored_data)
            print(f"   Access Token: {parsed_data.get('access_token', 'N/A')[:20]}...")
            print(f"   Refresh Token: {parsed_data.get('refresh_token', 'N/A')[:20]}...")
            print(f"   Expiry: {parsed_data.get('expiry', 'N/A')}")
        else:
            print(f"❌ Erro: Token não encontrado após armazenamento")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        
    finally:
        await redis_client.close()


if __name__ == "__main__":
    asyncio.run(initialize_token())
