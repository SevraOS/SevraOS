"""
HELIOS OS + SEVRA AI
Failure Recovery and Offline First Strategy
SECTIONS 19 & 20
"""

import asyncio
import structlog
from typing import Callable

from database.health.health_server import DatabaseHealthService
from database.sync.engine import SyncEngine
from database.metrics.prometheus import metrics

logger = structlog.get_logger(__name__)

class Orchestrator:
    """
    Manages the overall Database Service lifecycle, failure detection, 
    and offline-first transitions.
    """
    
    def __init__(
        self, 
        health_service: DatabaseHealthService, 
        sync_engine: SyncEngine,
        consumers: list
    ):
        self.health_service = health_service
        self.sync_engine = sync_engine
        self.consumers = consumers
        self._running = False
        self._monitor_task = None
        self._is_offline_mode = False

    async def start(self):
        """Boot up the service."""
        self._running = True
        
        # 1. Start consumers (they write to SQLite, which is local)
        for consumer in self.consumers:
            await consumer.start()
            
        # 2. Check initial network state
        is_pg_up = await self.health_service.check_postgresql()
        
        # 3. Start Sync Engine if online
        if is_pg_up:
            logger.info("orchestrator_pg_online_starting_sync")
            await self.sync_engine.start()
            self._is_offline_mode = False
        else:
            logger.warning("orchestrator_pg_offline_starting_in_offline_mode")
            self._is_offline_mode = True
            
        # 4. Start continuous monitor
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """Graceful shutdown."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            
        for consumer in self.consumers:
            await consumer.stop()
            
        await self.sync_engine.stop()

    async def _monitor_loop(self):
        """
        Continuously monitors health.
        Triggers Section 19 (Offline-First) & 20 (Failure Recovery).
        """
        while self._running:
            try:
                is_pg_up = await self.health_service.check_postgresql()
                
                # State Transition: Offline -> Online
                if not self._is_offline_mode and not is_pg_up:
                    logger.warning("network_partition_detected_entering_offline_mode")
                    self._is_offline_mode = True
                    await self.sync_engine.stop() # Pause sync, prevent error logs spam
                    metrics.inc_failure("network", "partition")
                    
                # State Transition: Online -> Offline (Recovery)
                elif self._is_offline_mode and is_pg_up:
                    logger.info("network_restored_resuming_sync_engine")
                    self._is_offline_mode = False
                    await self.sync_engine.start()
                    
                # Check SQLite (Critical Failure)
                is_sqlite_up = await self.health_service.check_sqlite()
                if not is_sqlite_up:
                    logger.critical("sqlite_corrupted_or_unavailable")
                    # If local storage dies, we must stop consumers from Acking messages
                    # This leaves messages in Redis PEL for recovery later
                    for consumer in self.consumers:
                        await consumer.stop()
                    metrics.inc_failure("sqlite", "corruption")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("orchestrator_monitor_error", error=str(e))
                
            await asyncio.sleep(15) # Check every 15s
