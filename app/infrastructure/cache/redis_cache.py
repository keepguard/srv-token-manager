"""Redis Cache Implementation."""

import json
import structlog
from typing import Dict, Any, Optional, List
import redis.asyncio as redis
from redis.exceptions import RedisError
from redis.cluster import RedisCluster

from app.application.ports.outbound.cache_port import CachePort

logger = structlog.get_logger()


class RedisCache(CachePort):
    """Redis implementation of CachePort."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        key_prefix: str = "",
        max_connections: int = 50,
        socket_timeout: int = 5,
        retry_on_timeout: bool = True,
        mode: str = "standalone",
        cluster_nodes: Optional[List[str]] = None
    ):
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.key_prefix = key_prefix
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.retry_on_timeout = retry_on_timeout
        self.mode = mode
        self.cluster_nodes = cluster_nodes or []
        self._redis: Optional[redis.Redis] = None
        self._cluster: Optional[RedisCluster] = None
    
    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            if self.mode == "cluster" and self.cluster_nodes:
                # Cluster mode
                startup_nodes = []
                for node in self.cluster_nodes:
                    host, port = node.split(":")
                    startup_nodes.append({"host": host, "port": int(port)})
                
                self._cluster = RedisCluster(
                    startup_nodes=startup_nodes,
                    password=self.password,
                    decode_responses=True,
                    skip_full_coverage_check=True,
                    socket_timeout=self.socket_timeout,
                    retry_on_timeout=self.retry_on_timeout
                )
                
                # Test connection
                await self._cluster.ping()
                logger.info("redis_cluster_connected", nodes=self.cluster_nodes)
                
            else:
                # Standalone mode
                self._redis = redis.Redis(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    db=self.db,
                    max_connections=self.max_connections,
                    socket_timeout=self.socket_timeout,
                    retry_on_timeout=self.retry_on_timeout,
                    decode_responses=True
                )
                
                # Test connection
                await self._redis.ping()
                logger.info("redis_connected", host=self.host, port=self.port, db=self.db)
            
        except RedisError as e:
            logger.error("redis_connection_failed", error=str(e))
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            logger.info("redis_disconnected")
        if self._cluster:
            await self._cluster.close()
            logger.info("redis_cluster_disconnected")
    
    def _get_key(self, key: str) -> str:
        """Get full key with prefix."""
        return f"{self.key_prefix}{key}" if self.key_prefix else key
    
    def _get_client(self):
        """Get the appropriate Redis client."""
        return self._cluster if self.mode == "cluster" else self._redis
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from cache."""
        client = self._get_client()
        if not client:
            await self.connect()
            client = self._get_client()
        
        try:
            full_key = self._get_key(key)
            value = await client.get(full_key)
            
            if value is None:
                logger.debug("cache_miss", key=key)
                return None
            
            # Parse JSON
            data = json.loads(value)
            logger.debug("cache_hit", key=key)
            return data
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.error("cache_get_failed", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: Dict[str, Any], ttl: int) -> bool:
        """Set value in cache with TTL."""
        client = self._get_client()
        if not client:
            await self.connect()
            client = self._get_client()
        
        try:
            full_key = self._get_key(key)
            json_value = json.dumps(value)
            
            await client.setex(full_key, ttl, json_value)
            logger.debug("cache_set", key=key, ttl=ttl)
            return True
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.error("cache_set_failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        client = self._get_client()
        if not client:
            await self.connect()
            client = self._get_client()
        
        try:
            full_key = self._get_key(key)
            result = await client.delete(full_key)
            logger.debug("cache_delete", key=key, deleted=bool(result))
            return bool(result)
            
        except RedisError as e:
            logger.error("cache_delete_failed", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        client = self._get_client()
        if not client:
            await self.connect()
            client = self._get_client()
        
        try:
            full_key = self._get_key(key)
            result = await client.exists(full_key)
            return bool(result)
            
        except RedisError as e:
            logger.error("cache_exists_failed", key=key, error=str(e))
            return False
    
    async def get_all_keys(self, pattern: str = "*") -> list[str]:
        """Get all keys matching pattern."""
        client = self._get_client()
        if not client:
            await self.connect()
            client = self._get_client()
        
        try:
            full_pattern = self._get_key(pattern)
            keys = await client.keys(full_pattern)
            
            # Remove prefix from keys
            if self.key_prefix:
                keys = [key[len(self.key_prefix):] for key in keys]
            
            return keys
            
        except RedisError as e:
            logger.error("cache_get_all_keys_failed", pattern=pattern, error=str(e))
            return []
