"""Settings Configuration Loader."""

import os
import yaml
from typing import Any, Dict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ServerConfig:
    """Server configuration."""
    host: str = "0.0.0.0"
    port: int = 8700
    read_timeout: int = 30
    write_timeout: int = 30


@dataclass
class TokenManagerConfig:
    """Token manager configuration."""
    refresh_strategy: str = "proactive"
    access_token_ttl_seconds: int = 3600
    refresh_before_expiry_minutes: int = 5
    cache_ttl_seconds: int = 3300
    max_inactivity_days: int = 180
    health_check_interval_days: int = 30
    max_tokens_per_account: int = 100
    retry_max_attempts: int = 3
    backoff_multiplier: int = 2
    initial_delay_seconds: int = 1


@dataclass
class GmailConfig:
    """Gmail configuration."""
    sender_email: str
    client_secrets_file: str
    token_file: str
    scopes: list[str]
    auth_mode: str = "token-only"


@dataclass
class RedisConfig:
    """Redis configuration."""
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0
    key_prefix: str = ""
    max_connections: int = 50
    socket_timeout: int = 5
    retry_on_timeout: bool = True


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    check_interval_seconds: int = 60
    alert_before_expiry_minutes: int = 10
    metrics_enabled: bool = True
    alerts_enabled: bool = False
    alert_webhook_url: str = ""


@dataclass
class LogConfig:
    """Log configuration."""
    level: str = "info"
    format: str = "json"


@dataclass
class Settings:
    """Application settings."""
    app_name: str
    app_version: str
    server: ServerConfig
    token_manager: TokenManagerConfig
    gmail: GmailConfig
    redis: RedisConfig
    monitoring: MonitoringConfig
    log: LogConfig
    env: str


def load_settings() -> Settings:
    """Load settings from configuration files."""
    
    # Get environment
    env = os.getenv("APP_ENV", "local").lower()
    
    # Get project root
    project_root = Path(__file__).parent.parent.parent.parent
    config_dir = project_root / "config"
    
    # Load base configuration
    base_config = _load_yaml(config_dir / "application.yaml")
    
    # Load environment-specific configuration
    env_config = _load_yaml(config_dir / f"application-{env}.yaml")
    
    # Merge configurations
    config = _deep_merge(base_config, env_config)
    
    # Override with environment variables
    config = _override_with_env(config)
    
    # Normalize paths
    config = _normalize_paths(config, project_root)
    
    # Create settings object
    return Settings(
        app_name=config["app"]["name"],
        app_version=config["app"]["version"],
        server=ServerConfig(
            host=config["server"]["host"],
            port=config["server"]["port"],
            read_timeout=config["server"]["read_timeout"],
            write_timeout=config["server"]["write_timeout"]
        ),
        token_manager=TokenManagerConfig(
            refresh_strategy=config["token_manager"]["refresh_strategy"],
            access_token_ttl_seconds=config["token_manager"]["access_token"]["ttl_seconds"],
            refresh_before_expiry_minutes=config["token_manager"]["access_token"]["refresh_before_expiry_minutes"],
            cache_ttl_seconds=config["token_manager"]["access_token"]["cache_ttl_seconds"],
            max_inactivity_days=config["token_manager"]["refresh_token"]["max_inactivity_days"],
            health_check_interval_days=config["token_manager"]["refresh_token"]["health_check_interval_days"],
            max_tokens_per_account=config["token_manager"]["refresh_token"]["max_tokens_per_account"],
            retry_max_attempts=config["token_manager"]["retry"]["max_attempts"],
            backoff_multiplier=config["token_manager"]["retry"]["backoff_multiplier"],
            initial_delay_seconds=config["token_manager"]["retry"]["initial_delay_seconds"]
        ),
        gmail=GmailConfig(
            sender_email=config["gmail"]["sender_email"],
            client_secrets_file=config["gmail"]["client_secrets_file"],
            token_file=config["gmail"]["token_file"],
            scopes=config["gmail"]["scopes"],
            auth_mode=config["gmail"].get("auth_mode", "token-only")
        ),
        redis=RedisConfig(
            host=config["redis"]["host"],
            port=config["redis"]["port"],
            password=config["redis"]["password"],
            db=config["redis"]["db"],
            key_prefix=config["redis"]["key_prefix"],
            max_connections=config["redis"]["max_connections"],
            socket_timeout=config["redis"]["socket_timeout"],
            retry_on_timeout=config["redis"]["retry_on_timeout"]
        ),
        monitoring=MonitoringConfig(
            check_interval_seconds=config["monitoring"]["check_interval_seconds"],
            alert_before_expiry_minutes=config["monitoring"]["alert_before_expiry_minutes"],
            metrics_enabled=config["monitoring"]["metrics_enabled"],
            alerts_enabled=config["monitoring"]["alerts_enabled"],
            alert_webhook_url=config["monitoring"].get("alert_webhook_url", "")
        ),
        log=LogConfig(
            level=config["log"]["level"],
            format=config["log"]["format"]
        ),
        env=config["env"]
    )


def _load_yaml(file_path: Path) -> Dict[str, Any]:
    """Load YAML file."""
    if not file_path.exists():
        return {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def _deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries."""
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _override_with_env(config: Dict[str, Any]) -> Dict[str, Any]:
    """Override configuration with environment variables."""
    def _override(target: Dict[str, Any], prefix: str = "") -> None:
        for k, v in list(target.items()):
            key = (prefix + k).upper().replace(".", "_")
            if isinstance(v, dict):
                _override(v, prefix=key + "_")
            else:
                env_v = os.getenv(key)
                if env_v is not None:
                    if isinstance(v, bool):
                        target[k] = env_v.lower() in ("1", "true", "yes")
                    else:
                        target[k] = env_v
    
    _override(config)
    return config


def _normalize_paths(config: Dict[str, Any], project_root: Path) -> Dict[str, Any]:
    """Normalize file paths."""
    def _abspath(p: str) -> str:
        if not p:
            return p
        if not os.path.isabs(p):
            return str(project_root / p)
        return p
    
    # Normalize Gmail paths
    gmail = config.get("gmail", {})
    if "client_secrets_file" in gmail:
        gmail["client_secrets_file"] = _abspath(gmail["client_secrets_file"])
    if "token_file" in gmail:
        gmail["token_file"] = _abspath(gmail["token_file"])
    
    return config
