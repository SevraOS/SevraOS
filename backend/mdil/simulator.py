"""
HELIOS OS + SEVRA AI
Device Simulators

Generates realistic device frames for ECG, BP, and SpO2.
Each simulator drives a SimulatorTransport → Collector → MDIL pipeline
without any physical hardware.

Usage:
    sim = ECGSimulator(device_id="SIM-ECG-001", rate_hz=1.0)
    transport = SimulatorTransport(device_id="SIM-ECG-001")
    await transport.connect()
    asyncio.create_task(sim.run(transport))
"""

from __future__ import annotations

import asyncio
import math
import random
from datetime import datetime, timezone

import structlog

from mdil.transports.simulator_transport import SimulatorTransport

logger = structlog.get_logger(__name__)


class ECGSimulator:
    """
    Simulates an ECG monitor producing DAT| and WFM| ASCII frames.

    DAT frames: 1 Hz (one HR + lead amplitude reading per second)
    WFM frames: every 0.5s with 250 samples at 500 Hz
    STA frames: heartbeat every 10s
    """

    def __init__(
        self,
        device_id: str,
        rate_hz: float = 1.0,
        base_hr: float = 72.0,
        lead: str = "II",
    ) -> None:
        self.device_id = device_id
        self._rate_hz = rate_hz
        self._base_hr = base_hr
        self._lead = lead
        self._running = False
        self._tick = 0
        self._log = logger.bind(simulator="ECGSimulator", device_id=device_id)

    async def run(self, transport: SimulatorTransport) -> None:
        """Push ECG frames into the transport at configured rate."""
        self._running = True
        self._log.info("ecg_simulator_started", rate_hz=self._rate_hz)
        interval = 1.0 / self._rate_hz

        while self._running:
            self._tick += 1

            # DAT frame every tick
            hr = round(self._base_hr + random.uniform(-3, 3), 1)
            amplitude = round(0.84 + math.sin(self._tick * 0.1) * 0.1, 3)
            dat_frame = f"DAT|{hr}|{amplitude}|{self._lead}".encode()
            await transport.push_frame(dat_frame)

            # WFM frame every 5th tick
            if self._tick % 5 == 0:
                sample_rate = 500
                samples = [
                    round(amplitude * math.sin(i * 2 * math.pi / 50) + random.uniform(-0.01, 0.01), 3)
                    for i in range(50)
                ]
                sample_str = ",".join(str(s) for s in samples)
                wfm_frame = f"WFM|{self._lead}|{sample_rate}|{sample_str}".encode()
                await transport.push_frame(wfm_frame)

            # STA heartbeat every 10th tick
            if self._tick % 10 == 0:
                await transport.push_frame(b"STA|OK")

            await asyncio.sleep(interval)

    async def stop(self) -> None:
        self._running = False
        self._log.info("ecg_simulator_stopped")


class BPSimulator:
    """
    Simulates a blood pressure monitor.
    Produces SYS/DIA/MAP/PR ASCII frames.
    """

    def __init__(
        self,
        device_id: str,
        rate_hz: float = 0.5,
        base_sys: float = 120.0,
        base_dia: float = 80.0,
    ) -> None:
        self.device_id = device_id
        self._rate_hz = rate_hz
        self._base_sys = base_sys
        self._base_dia = base_dia
        self._running = False
        self._log = logger.bind(simulator="BPSimulator", device_id=device_id)

    async def run(self, transport: SimulatorTransport) -> None:
        """Push BP frames into the transport."""
        self._running = True
        self._log.info("bp_simulator_started", rate_hz=self._rate_hz)
        interval = 1.0 / self._rate_hz

        while self._running:
            sys_bp = round(self._base_sys + random.uniform(-5, 5))
            dia_bp = round(self._base_dia + random.uniform(-3, 3))
            map_bp = round((sys_bp + 2 * dia_bp) / 3)
            pr = round(72 + random.uniform(-4, 4))
            frame = f"SYS={sys_bp} DIA={dia_bp} MAP={map_bp} PR={pr}".encode()
            await transport.push_frame(frame)
            await asyncio.sleep(interval)

    async def stop(self) -> None:
        self._running = False
        self._log.info("bp_simulator_stopped")


class SpO2Simulator:
    """
    Simulates a pulse oximeter.
    Produces 4-byte BLE binary payloads (sensor_contact + SpO2 + HR).
    """

    def __init__(
        self,
        device_id: str,
        rate_hz: float = 1.0,
        base_spo2: int = 98,
        base_hr: int = 72,
    ) -> None:
        self.device_id = device_id
        self._rate_hz = rate_hz
        self._base_spo2 = base_spo2
        self._base_hr = base_hr
        self._running = False
        self._log = logger.bind(simulator="SpO2Simulator", device_id=device_id)

    async def run(self, transport: SimulatorTransport) -> None:
        """Push BLE SpO2 binary frames into the transport."""
        self._running = True
        self._log.info("spo2_simulator_started", rate_hz=self._rate_hz)
        interval = 1.0 / self._rate_hz

        while self._running:
            spo2 = max(85, min(100, self._base_spo2 + random.randint(-1, 1)))
            hr = max(40, min(180, self._base_hr + random.randint(-2, 2)))

            # BLE binary: [flags=0x03 (16-bit HR + sensor contact), spo2, hr_lo, hr_hi]
            flags = 0x03  # HR 16-bit + sensor contact
            frame = bytes([flags, spo2, hr & 0xFF, (hr >> 8) & 0xFF])
            await transport.push_frame(frame)
            await asyncio.sleep(interval)

    async def stop(self) -> None:
        self._running = False
        self._log.info("spo2_simulator_stopped")


async def run_ecg_demo(duration_seconds: float = 5.0) -> list:
    """
    Demo: ECG Simulator → SimulatorTransport → ECGAdapter.
    Returns list of RawReadings produced.

    Raw bytes → Transport → Collector → Adapter → RawReading
    """
    from collectors.ecg_collector.collector import ECGCollector
    from collectors.base.validation_interface import QueueValidationInterface

    validation = QueueValidationInterface()
    await validation.start()

    config = {
        "device_id": "SIM-ECG-001",
        "transport": "serial",  # Will be overridden by SimulatorTransport
        "port": "/dev/null",
        "baud_rate": 115200,
        "ward": "ICU",
        "bed": "BED-01",
        "facility_id": "FACILITY-001",
        "frame_buffer_size": 512,
        "reconnect_base_delay": 1.0,
        "reconnect_max_delay": 60.0,
        "reconnect_factor": 2.0,
        "max_reconnect_attempts": 1,
    }

    transport = SimulatorTransport(device_id="SIM-ECG-001")

    # Build collector but inject simulator transport
    collector = ECGCollector(config=config, validation_queue=validation._queue)

    # Patch build_transport
    collector.build_transport = lambda: transport  # type: ignore[method-assign]

    sim = ECGSimulator(device_id="SIM-ECG-001", rate_hz=2.0)

    # Start all concurrently
    collector_task = asyncio.create_task(collector.start())
    sim_task = asyncio.create_task(sim.run(transport))

    await asyncio.sleep(duration_seconds)

    await sim.stop()
    await transport.disconnect()
    await collector.stop()
    collector_task.cancel()
    sim_task.cancel()

    readings = await validation.drain()
    await validation.stop()
    return readings
