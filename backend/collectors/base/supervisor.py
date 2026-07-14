"""
HELIOS OS + SEVRA AI
Collector Supervisor

Manages the lifecycle of all device collectors:
  - Start collectors as asyncio Tasks
  - Monitor health and restart failed collectors
  - Expose aggregated health state
  - Graceful shutdown of all collectors

Design:
  - One Supervisor per process (singleton).
  - Each collector runs as an independent asyncio.Task.
  - If a collector Task ends unexpectedly, Supervisor restarts it.
  - Graceful shutdown cancels all tasks with a configurable timeout.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from collectors.base.collector_base import BaseCollector
from collectors.base.health import CollectorHealth, DeviceStatus

logger = structlog.get_logger(__name__)


class CollectorSupervisor:
    """
    Supervises all device collectors.

    Usage:
        supervisor = CollectorSupervisor()
        supervisor.register(ecg_collector)
        supervisor.register(bp_collector)
        await supervisor.start_all()
        # ... runs until shutdown
        await supervisor.shutdown()
    """

    def __init__(self, shutdown_timeout: float = 10.0) -> None:
        self._collectors: dict[str, BaseCollector] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._running: bool = False
        self._shutdown_timeout = shutdown_timeout
        self._log = logger.bind(component="CollectorSupervisor")

    def register(self, collector: BaseCollector) -> None:
        """
        Register a collector with the supervisor.
        Must be called before start_all().
        Raises ValueError if a collector with the same device_id is already registered.
        """
        device_id = collector.device_id
        if device_id in self._collectors:
            raise ValueError(
                f"Collector for device_id='{device_id}' is already registered."
            )
        self._collectors[device_id] = collector
        self._log.info("supervisor_collector_registered", device_id=device_id)

    def unregister(self, device_id: str) -> None:
        """Remove a collector from the supervisor (must be stopped first)."""
        self._collectors.pop(device_id, None)
        self._log.info("supervisor_collector_unregistered", device_id=device_id)

    async def start_all(self) -> None:
        """
        Start all registered collectors as asyncio Tasks.
        Sets up a monitoring loop that restarts crashed collectors.
        """
        self._running = True
        self._log.info("supervisor_starting", collector_count=len(self._collectors))

        for device_id, collector in self._collectors.items():
            self._launch_task(device_id, collector)

        # Monitor loop
        await self._monitor_loop()

    async def _monitor_loop(self) -> None:
        """
        Continuously monitor collector Tasks.
        Restarts any Task that has ended unexpectedly (not DeviceStatus.STOPPED/FAILED).
        """
        while self._running:
            await asyncio.sleep(5.0)  # Health-check interval

            for device_id, task in list(self._tasks.items()):
                collector = self._collectors.get(device_id)
                if collector is None:
                    continue

                if task.done():
                    exc = task.exception() if not task.cancelled() else None
                    health_status = collector.health.status

                    if health_status in (DeviceStatus.STOPPED, DeviceStatus.FAILED):
                        # Intentional stop — do not restart
                        self._log.info(
                            "supervisor_collector_terminal",
                            device_id=device_id,
                            status=health_status,
                        )
                        continue

                    # Unexpected exit — restart
                    self._log.warning(
                        "supervisor_collector_unexpected_exit",
                        device_id=device_id,
                        error=str(exc) if exc else "unknown",
                    )
                    self._launch_task(device_id, collector)

    def _launch_task(self, device_id: str, collector: BaseCollector) -> None:
        """Create and register an asyncio Task for the collector."""
        task = asyncio.create_task(
            collector.start(),
            name=f"collector_{device_id}",
        )
        self._tasks[device_id] = task
        self._log.info("supervisor_collector_launched", device_id=device_id)

    async def shutdown(self) -> None:
        """
        Gracefully stop all collectors and cancel their tasks.
        Waits up to shutdown_timeout seconds for each.
        """
        self._running = False
        self._log.info("supervisor_shutdown_initiated")

        # Signal all collectors to stop
        stop_coros = [c.stop() for c in self._collectors.values()]
        await asyncio.gather(*stop_coros, return_exceptions=True)

        # Cancel and await all tasks
        tasks = list(self._tasks.values())
        for task in tasks:
            if not task.done():
                task.cancel()

        if tasks:
            await asyncio.wait(tasks, timeout=self._shutdown_timeout)

        self._log.info("supervisor_shutdown_complete")

    def health_report(self) -> dict[str, Any]:
        """
        Return aggregated health for all collectors.
        Safe to call at any time.
        """
        reports = {}
        for device_id, collector in self._collectors.items():
            reports[device_id] = collector.health.to_dict()

        statuses = [c.health.status for c in self._collectors.values()]
        all_connected = all(s == DeviceStatus.CONNECTED for s in statuses)
        any_failed = any(s == DeviceStatus.FAILED for s in statuses)

        return {
            "overall_status": (
                "healthy" if all_connected else
                "degraded" if not any_failed else
                "critical"
            ),
            "collector_count": len(self._collectors),
            "collectors": reports,
        }

    def get_health(self, device_id: str) -> CollectorHealth | None:
        """Get health for a specific device collector."""
        collector = self._collectors.get(device_id)
        return collector.health if collector else None

    @property
    def is_running(self) -> bool:
        return self._running

    def __repr__(self) -> str:
        return (
            f"CollectorSupervisor("
            f"collectors={list(self._collectors.keys())}, "
            f"running={self._running})"
        )
