# 🔐 SRV Token Manager

Sistema profissional de gerenciamento de tokens OAuth2 para Gmail com cache Redis e refresh proativo.


## 📋 Renovar token
python3 keepguard-core/backend/srv/srv-email-google-sender/scripts/generate_token.py \
  --client-secrets keepguard-core/backend/srv/srv-token-manager/secure/credentials-local.json \
  --token-file keepguard-core/backend/srv/srv-token-manager/secure/token.json


## 📋 Visão Geral

O **srv-token-manager** é um microserviço Python que gerencia tokens OAuth2 do Gmail de forma centralizada, oferecendo:

- ✅ **Refresh proativo** (5 minutos antes da expiração)
- ✅ **Cache distribuído** com Redis
- ✅ **API REST** para obtenção de tokens
- ✅ **Métricas Prometheus** e logs estruturados
- ✅ **Health checks** e monitoramento
- ✅ **Arquitetura Hexagonal** com DDD e SOLID

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                     Aplicações Clientes                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │ email-google-   │  │ Outros serviços │  │ Scripts     │  │
│  │ sender          │  │                 │  │             │  │
│  └─────────┬───────┘  └─────────┬───────┘  └─────┬───────┘  │
└────────────┼────────────────────┼─────────────────┼──────────┘
             │                    │                 │
             └────────────────────┼─────────────────┘
                                  │
┌─────────────────────────────────▼─────────────────────────────┐
│                SRV Token Manager (FastAPI)                     │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  API Layer (REST Endpoints)                            │  │
│  │  ├─ GET /api/v1/tokens/gmail/{email}                   │  │
│  │  ├─ POST /api/v1/tokens/gmail/{email}/refresh          │  │
│  │  ├─ GET /api/v1/tokens/gmail/{email}/status            │  │
│  │  ├─ GET /health                                         │  │
│  │  └─ GET /metrics                                        │  │
│  └─────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Application Layer (Use Cases)                         │  │
│  │  ├─ GetTokenUseCase                                    │  │
│  │  ├─ RefreshTokenUseCase                               │  │
│  │  ├─ GetTokenStatusUseCase                             │  │
│  │  └─ TokenHealthCheckUseCase                           │  │
│  └─────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Domain Layer (Entities & Value Objects)              │  │
│  │  ├─ Token (Aggregate Root)                            │  │
│  │  ├─ Email (Value Object)                              │  │
│  │  ├─ TokenExpiry (Value Object)                        │  │
│  │  └─ TokenExpiryCalculator (Domain Service)            │  │
│  └─────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Infrastructure Layer (Adapters)                      │  │
│  │  ├─ RedisCache                                         │  │
│  │  ├─ GoogleOAuth2Client                                │  │
│  │  ├─ TokenRepository                                   │  │
│  │  ├─ WebhookAlert                                      │  │
│  │  └─ TokenRefreshJob (Background Worker)              │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
┌─────────────────────────────────▼─────────────────────────────┐
│                    Redis Cache                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Key: local:gmail:token:keepguard.ia@gmail.com        │  │
│  │  Value: {                                              │  │
│  │    "access_token": "ya29.a0...",                      │  │
│  │    "refresh_token": "1//0h...",                       │  │
│  │    "expiry": "2025-10-24T20:42:52Z",                  │  │
│  │    "last_refresh": "2025-10-24T19:42:52Z",            │  │
│  │    "refresh_count": 5                                 │  │
│  │  }                                                     │  │
│  │  TTL: 3300s (55 minutos)                              │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Pré-requisitos

- Python 3.11+
- Redis
- Docker e Docker Compose (opcional)

### Instalação Local

1. **Clone e configure o projeto:**
```bash
cd keepguard-backend/backend/srv/srv-token-manager
```

2. **Instale as dependências:**
```bash
pip install poetry
poetry install
```

3. **Configure as credenciais:**
```bash
# Copie as credenciais do srv-email-google-sender
cp ../srv-email-google-sender/secure/credentials-local.json secure/
cp ../srv-email-google-sender/secure/token.json secure/
```

4. **Inicie o Redis:**
```bash
# Com Docker
docker run -d --name redis-token-manager -p 6379:6379 redis:7-alpine

# Ou com Docker Compose
docker-compose up -d redis
```

5. **Execute o serviço:**
```bash
poetry run python app/main.py
```

6. **Teste o serviço:**
```bash
poetry run python scripts/test_token_manager.py
```

### Docker Compose

```bash
# Iniciar todos os serviços
docker-compose up -d

# Ver logs
docker-compose logs -f srv-token-manager

# Parar serviços
docker-compose down
```

## 📚 API Endpoints

### Health Check
```bash
GET /health
```

### Obter Token
```bash
GET /api/v1/tokens/gmail/{email}
```

### Refresh Token
```bash
POST /api/v1/tokens/gmail/{email}/refresh
```

### Status do Token
```bash
GET /api/v1/tokens/gmail/{email}/status
```

### Métricas Prometheus
```bash
GET /metrics
```

## ⚙️ Configuração

### Variáveis de Ambiente

```bash
# Ambiente
APP_ENV=local  # local, dev, prod

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Gmail
GMAIL_SENDER_EMAIL=keepguard.ia@gmail.com

# Monitoramento
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

### Arquivos de Configuração

- `config/application.yaml` - Configuração base
- `config/application-local.yaml` - Ambiente local
- `config/application-dev.yaml` - Ambiente desenvolvimento
- `config/application-prod.yaml` - Ambiente produção

## 🔄 Funcionamento

### Fluxo de Refresh Proativo

1. **Background Job** verifica tokens a cada 60 segundos
2. **Identifica tokens** que expiram em < 5 minutos
3. **Executa refresh** usando Google OAuth2 API
4. **Atualiza cache** Redis com novo token
5. **Registra métricas** e logs

### Fluxo de Consumo

1. **Cliente** solicita token via API
2. **Token Manager** busca no cache Redis
3. **Retorna token** válido para o cliente
4. **Cliente** usa token para enviar e-mail

## 📊 Monitoramento

### Métricas Prometheus

- `token_manager_refresh_total` - Total de refreshes
- `token_manager_expiry_seconds` - Segundos até expiração
- `token_manager_cache_hits_total` - Cache hits
- `token_manager_http_requests_total` - Requests HTTP

### Logs Estruturados

```json
{
  "timestamp": "2025-10-24T19:42:52Z",
  "level": "info",
  "event": "token_refresh_success",
  "email": "keepguard.ia@gmail.com",
  "old_expiry": "2025-10-24T19:42:52Z",
  "new_expiry": "2025-10-24T20:42:52Z",
  "refresh_duration_ms": 234
}
```

## 🧪 Testes

```bash
# Executar todos os testes
poetry run pytest

# Testes com coverage
poetry run pytest --cov=app --cov-report=html

# Testes específicos
poetry run pytest tests/unit/domain/test_token_entity.py
```

## 🔧 Desenvolvimento

### Estrutura do Projeto

```
srv-token-manager/
├── app/                    # Código da aplicação
│   ├── api/               # API REST (FastAPI)
│   ├── application/       # Use Cases e Ports
│   ├── domain/           # Entidades e Value Objects
│   ├── infrastructure/   # Adapters externos
│   └── main.py           # Entry point
├── config/               # Configurações
├── scripts/              # Scripts utilitários
├── tests/                # Testes
└── secure/               # Credenciais (gitignored)
```

### Princípios Arquiteturais

- **Hexagonal Architecture** (Ports & Adapters)
- **Domain-Driven Design** (DDD)
- **SOLID Principles**
- **Clean Code**

### Code Quality

```bash
# Formatação
poetry run black app/ tests/
poetry run isort app/ tests/

# Linting
poetry run flake8 app/ tests/
poetry run mypy app/

# Pre-commit hooks
poetry run pre-commit install
```

## 🚀 Deploy

### GitHub Container Registry

```bash
# Build e push
./script-deploy-github-srv-token-manager.sh v1.0.0

# Deploy local
docker-compose pull srv-token-manager
docker-compose up -d srv-token-manager
```

## 🔗 Integração com srv-email-google-sender

### TokenManagerClient

```python
from app.infrastructure.token_manager_client import TokenManagerClient

# Inicializar cliente
client = TokenManagerClient(
    token_manager_url="http://srv-token-manager:8700",
    email="keepguard.ia@gmail.com"
)

# Obter credenciais
creds = await client.get_credentials()
```

### Modificações Necessárias

1. **Adicionar TokenManagerClient** ao srv-email-google-sender
2. **Remover lógica de refresh local**
3. **Configurar URL do token manager**
4. **Manter apenas envio de e-mail**

## 📝 Logs e Troubleshooting

### Logs Importantes

```bash
# Ver logs do serviço
docker-compose logs -f srv-token-manager

# Filtrar logs de refresh
docker-compose logs srv-token-manager | grep "token_refresh"

# Logs de erro
docker-compose logs srv-token-manager | grep "ERROR"
```

### Problemas Comuns

1. **Token expirado**: Verificar se refresh está funcionando
2. **Redis desconectado**: Verificar conexão Redis
3. **Credenciais inválidas**: Regenerar token.json
4. **Porta ocupada**: Verificar se porta 8700 está livre

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto é parte do ecossistema KeepGuard e segue as mesmas políticas de licenciamento.

## 📞 Suporte

Para dúvidas ou problemas:

- **Issues**: Abra uma issue no repositório
- **Logs**: Verifique logs estruturados
- **Métricas**: Monitore via Prometheus
- **Health Check**: Use endpoint `/health`
