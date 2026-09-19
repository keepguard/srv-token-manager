# srv-token-manager - System Design

## 1. Propósito e Domínio
- **Responsabilidade Principal:** Gerenciar de forma centralizada o ciclo de vida de tokens OAuth2 do Gmail (obtenção, cache Redis, refresh proativo e health), expondo API REST para consumidores como o `srv-email-sender` usarem o access token sem lidar com OAuth2 diretamente.
- **Domínio/Subdomínio:** Comunicação / Credenciais OAuth2 (Gmail) — infraestrutura de plataforma KeepGuard (envio de e-mail).

## 2. Tech Stack Local
- **Linguagem & Framework:** Python 3.11 / FastAPI ^0.115 + Uvicorn; Poetry (`srv-token-manager` 1.0.0, app version em config `1.0.14`); Pydantic 2 / pydantic-settings; PyYAML; structlog; APScheduler (dependência); Prometheus client; httpx; bibliotecas Google (`google-auth`, `google-auth-oauthlib`, `google-api-python-client`).
- **Persistência e Cache:** Sem banco SQL. Persistência primária em arquivo JSON (`secure/token.json`); cache Redis (standalone em local/dev; cluster 6 nós declarado em `application-prod.yaml`) com prefixos `local|dev|prod:gmail:token:` e TTL de cache do access token ~3300s (55 min). Credenciais OAuth em `secure/credentials*.json` / `service-account.json` (prod).
- **Mensageria:** RabbitMQ (AMQP via `pika`) — **publica** eventos de auditoria fire-and-forget (`AuditEventPublisher`) no exchange topic configurável (`AUDIT_EXCHANGE`, default `srv-audit-exchange-local` / Helm `srv-audit-exchange-prod`), routing-key `audit.event`, `sourceService: srv-token-manager`. Não consome filas neste serviço.

## 3. Arquitetura Interna
- **Padrão Utilizado:** Hexagonal (Ports & Adapters) + DDD leve + Use Cases — camadas `api` → `application` (ports in/out + usecases) → `domain` (entity/VOs/errors/services) → `infrastructure` (adapters); DI manual via `Container` no lifespan FastAPI.
- **Módulos Principais:**
  - **Agregado de domínio:** `Token` (access/refresh, expiry, scopes, `client_id`/`client_secret`, `refresh_count`, `last_refresh`).
  - **Value Objects:** `Email`, `TokenExpiry`, enum `RefreshStrategy` (`proactive` | `reactive`).
  - **Domain service:** `TokenExpiryCalculator` (janela de refresh e TTL de cache).
  - **Erros de domínio:** `TokenNotFoundError`, `TokenExpiredError`, `TokenRefreshError`, `TokenInvalidError`, erros de validação.
  - **Ports out:** `CachePort`, `TokenRepositoryPort`, `OAuth2ClientPort`, `AlertPort`; ports in (`token_service_port`, `health_check_port`) declarados.
  - **Use cases:** `GetTokenUseCase`, `RefreshTokenUseCase`, `GetTokenStatusUseCase`, `TokenHealthCheckUseCase`.
  - **Adapters in REST:** `token_router`, `health_router`, `metrics_router` + root `/`.
  - **Adapters out:** `RedisCache`, `TokenRepository` (filesystem), `GoogleOAuth2Client`, `WebhookAlert`, `AuditEventPublisher`, `TokenRefreshJob` (asyncio loop); `LeaderElector` (K8s Lease) presente mas **não** wired no `Container`; `TokenManagerClient` como referência de cliente HTTP para consumidores.

## 4. Superfície de Contato (I/O)
- **Endpoints Expostos Principais:**
  - `GET /api/v1/tokens/gmail/{email}` — retorna token válido (cache-first; 404 / 410 se ausente/expirado).
  - `POST /api/v1/tokens/gmail/{email}/refresh` — refresh manual via Google OAuth2.
  - `GET /api/v1/tokens/gmail/{email}/status` — validade, expiry, `needs_refresh`, `refresh_count`.
  - `GET /health`, `/health/token`, `/health/ready`, `/health/live` — liveness/readiness/health de tokens.
  - `GET /metrics` — Prometheus; `GET /` — info do serviço.
  - Portas: **8700** (base/dev/prod), **8701** (local overlay).
- **Dependências Externas:** Google OAuth2 / Gmail API (`gmail.send`); Redis; RabbitMQ (`srv-audit`); webhook HTTP de alertas (Slack-like, opcional); consumidor principal documentado: `srv-email-sender` (HTTP). Kubernetes API apenas no módulo de leader election (não ativo no container atual).

## 5. Invariantes Locais e Observações
- **Refresh proativo:** estratégia default `proactive`; access token Google TTL 3600s; refresh quando faltam ≤5 min; job em background a cada `check_interval_seconds` (60s local/prod, 30s dev).
- **Cache-first:** chave lógica `token:{email}` com prefixo Redis por ambiente; TTL fixo 3300s nos use cases; hit de cache no GET evita I/O de arquivo.
- **Repositório single-tenant de arquivo:** um `token.json` por instância; `get_all()` hardcoda e-mail `keepguard.ia@gmail.com`; não há multi-conta real no filesystem apesar de `max_tokens_per_account: 100` na config.
- **FS read-only em K8s:** `TokenRepository.save` engole `PermissionError` e deixa o token renovado só no Redis (secrets montadas read-only).
- **Escopo OAuth:** apenas `https://www.googleapis.com/auth/gmail.send`; conta `keepguard.ia@gmail.com`.
- **Prod `auth_mode: service-account`:** declarado em YAML, mas o client ativo usa `Credentials.from_authorized_user_info` (fluxo user/token); service account não está implementado no adapter OAuth atual.
- **Auditoria:** publica `TOKEN_REFRESH_FAILURE` em falha de refresh (e-mail mascarado); falha de publish não quebra o fluxo (warning). `AUDIT_ENABLED` / credenciais RabbitMQ via env.
- **Alertas:** `WebhookAlert` só envia se `alert_webhook_url` preenchido; falha de refresh dispara alerta crítico.
- **Leader election:** código K8s Lease existe, mas comentário no `Container` indica remoção do wiring — risco de refresh duplicado se houver múltiplos pods.
- **Config:** merge `application.yaml` + `application-{APP_ENV}.yaml` + override por env; `RedisConfig` em Settings **não** carrega `mode`/`cluster_nodes` do YAML — cluster prod pode não ser aplicado via loader atual (container usa `getattr(..., 'standalone')`).
- **Observabilidade:** CorrelationId middleware; logs JSON estruturados; métricas (`token_manager_refresh_total`, expiry, cache hits, HTTP); CORS aberto `*`.
- **Deploy:** Docker/Helm (GHCR `ghcr.io/keepguard/srv-token-manager`), recursos ~128–256Mi; scripts `script-deploy-github-*.sh` / `script-deploy-k8s-prod.sh`.
