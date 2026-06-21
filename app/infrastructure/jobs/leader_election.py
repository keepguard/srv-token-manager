"""Kubernetes Leader Election Implementation."""

import asyncio
import structlog
from typing import Optional
from datetime import datetime, timedelta
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = structlog.get_logger()


class LeaderElector:
    """Leader election for Kubernetes pods."""
    
    def __init__(
        self,
        namespace: str = "keepguard",
        lock_name: str = "srv-token-manager-leader",
        lock_duration: int = 15,
        renew_deadline: int = 10,
        retry_period: int = 2
    ):
        self.namespace = namespace
        self.lock_name = lock_name
        self.lock_duration = lock_duration
        self.renew_deadline = renew_deadline
        self.retry_period = retry_period
        self.is_leader = False
        self._task = None
        self._v1 = None
        self._identity = None
    
    async def start(self) -> None:
        """Start leader election."""
        try:
            # Load Kubernetes config
            config.load_incluster_config()
            self._v1 = client.CoreV1Api()
            
            # Generate identity
            import socket
            self._identity = f"{socket.gethostname()}-{datetime.utcnow().isoformat()}"
            
            # Start election task
            self._task = asyncio.create_task(self._run_election())
            logger.info("leader_election_started", identity=self._identity)
            
        except Exception as e:
            logger.error("leader_election_start_failed", error=str(e))
            raise
    
    async def stop(self) -> None:
        """Stop leader election."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("leader_election_stopped")
    
    async def _run_election(self) -> None:
        """Main election loop."""
        while True:
            try:
                if await self._try_acquire_lock():
                    self.is_leader = True
                    logger.info("leader_elected", identity=self._identity)
                    
                    # Renew lock periodically
                    await self._renew_lock()
                else:
                    self.is_leader = False
                    logger.debug("not_leader", identity=self._identity)
                
                await asyncio.sleep(self.retry_period)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("leader_election_error", error=str(e))
                self.is_leader = False
                await asyncio.sleep(self.retry_period)
    
    async def _try_acquire_lock(self) -> bool:
        """Try to acquire leadership lock."""
        try:
            # Check if lock exists
            try:
                lease = self._v1.read_namespaced_lease(
                    name=self.lock_name,
                    namespace=self.namespace
                )
                
                # Check if lease is expired
                if lease.spec.lease_duration_seconds and lease.spec.lease_duration_seconds > 0:
                    lease_time = datetime.fromisoformat(lease.metadata.creation_timestamp.replace('Z', '+00:00'))
                    expiry_time = lease_time + timedelta(seconds=lease.spec.lease_duration_seconds)
                    
                    if datetime.utcnow() < expiry_time:
                        logger.debug("lease_active", holder=lease.spec.holder_identity)
                        return False
                
            except ApiException as e:
                if e.status == 404:
                    # Lease doesn't exist, create it
                    await self._create_lease()
                    return True
                else:
                    raise
            
            # Try to update lease
            try:
                lease.spec.holder_identity = self._identity
                lease.spec.lease_duration_seconds = self.lock_duration
                lease.spec.renew_time = datetime.utcnow().isoformat() + 'Z'
                
                self._v1.replace_namespaced_lease(
                    name=self.lock_name,
                    namespace=self.namespace,
                    body=lease
                )
                
                return True
                
            except ApiException as e:
                if e.status == 409:
                    # Conflict - someone else got the lock
                    return False
                else:
                    raise
            
        except Exception as e:
            logger.error("acquire_lock_failed", error=str(e))
            return False
    
    async def _create_lease(self) -> None:
        """Create new lease."""
        try:
            lease = client.V1Lease(
                metadata=client.V1ObjectMeta(
                    name=self.lock_name,
                    namespace=self.namespace
                ),
                spec=client.V1LeaseSpec(
                    holder_identity=self._identity,
                    lease_duration_seconds=self.lock_duration,
                    renew_time=datetime.utcnow().isoformat() + 'Z'
                )
            )
            
            self._v1.create_namespaced_lease(
                namespace=self.namespace,
                body=lease
            )
            
            logger.info("lease_created", identity=self._identity)
            
        except Exception as e:
            logger.error("create_lease_failed", error=str(e))
            raise
    
    async def _renew_lock(self) -> None:
        """Renew leadership lock."""
        try:
            while self.is_leader:
                # Renew lease
                lease = self._v1.read_namespaced_lease(
                    name=self.lock_name,
                    namespace=self.namespace
                )
                
                lease.spec.renew_time = datetime.utcnow().isoformat() + 'Z'
                
                self._v1.replace_namespaced_lease(
                    name=self.lock_name,
                    namespace=self.namespace,
                    body=lease
                )
                
                logger.debug("lease_renewed", identity=self._identity)
                
                # Wait before next renewal
                await asyncio.sleep(self.renew_deadline)
                
        except ApiException as e:
            if e.status == 404:
                logger.warning("lease_not_found_during_renewal")
            else:
                logger.error("renew_lock_failed", error=str(e))
            self.is_leader = False
        except Exception as e:
            logger.error("renew_lock_error", error=str(e))
            self.is_leader = False
