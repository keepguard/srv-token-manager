#!/usr/bin/env python3
"""Script de teste para srv-token-manager."""

import asyncio
import httpx
import json
from datetime import datetime


async def test_token_manager():
    """Testa o srv-token-manager localmente."""
    
    base_url = "http://localhost:8700"
    
    print("🧪 Testando srv-token-manager...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Test 1: Health check
            print("\n1. Testando health check...")
            response = await client.get(f"{base_url}/health/")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
            
            # Test 2: Token status
            print("\n2. Testando status do token...")
            email = "keepguard.ia@gmail.com"
            response = await client.get(f"{base_url}/api/v1/tokens/gmail/{email}/status")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                status = response.json()
                print(f"   Token válido: {status.get('is_valid')}")
                print(f"   Expira em: {status.get('expires_in_minutes')} minutos")
                print(f"   Precisa refresh: {status.get('needs_refresh')}")
            else:
                print(f"   Erro: {response.text}")
            
            # Test 3: Get token
            print("\n3. Testando obtenção do token...")
            response = await client.get(f"{base_url}/api/v1/tokens/gmail/{email}")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                token_data = response.json()
                print(f"   Token obtido com sucesso")
                print(f"   Email: {token_data.get('email')}")
                print(f"   Status: {token_data.get('status')}")
            else:
                print(f"   Erro: {response.text}")
            
            # Test 4: Refresh token (se necessário)
            print("\n4. Testando refresh do token...")
            response = await client.post(f"{base_url}/api/v1/tokens/gmail/{email}/refresh")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                refresh_data = response.json()
                print(f"   Token refreshado com sucesso")
                print(f"   Status: {refresh_data.get('status')}")
            else:
                print(f"   Erro: {response.text}")
            
            # Test 5: Metrics
            print("\n5. Testando métricas...")
            response = await client.get(f"{base_url}/metrics")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                metrics_text = response.text
                lines = metrics_text.split('\n')
                token_metrics = [line for line in lines if 'token_manager' in line]
                print(f"   Métricas encontradas: {len(token_metrics)}")
                for metric in token_metrics[:5]:  # Mostrar apenas as primeiras 5
                    print(f"   {metric}")
            
            print("\n✅ Testes concluídos!")
            
        except httpx.ConnectError:
            print("❌ Erro: Não foi possível conectar ao srv-token-manager")
            print("   Certifique-se de que o serviço está rodando em http://localhost:8700")
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")


if __name__ == "__main__":
    asyncio.run(test_token_manager())
