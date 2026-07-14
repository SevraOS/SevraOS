# HELIOS OS + SEVRA AI
# Section 11: MDIL & Collector Architecture

---

## 11.1 Why the MDIL Exists

Medical devices speak dozens of incompatible protocols:
- RS-232/485 serial ASCII streams
- Bluetooth Low Energy GATT notifications
- USB HID interrupt transfers
- TCP sockets carrying HL7 v2 / MLLP
- Proprietary binary frames

Without the MDIL, every downstream service would need protocol-specific logic.
The MDIL is a **protocol firewall**: protocol complexity lives only inside it.
Downstream services (Validation, Normalization, AI) only see `RawReading`.

---

## 11.2 MDIL Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MEDICAL DEVICE INTEGRATION LAYER (MDIL)                 │
│                                                                             │
│  ┌─────────────┐   ┌──────────────────┐   ┌──────────────────────────────┐ │
│  │  Transport  │──▶│  DeviceAdapter   │──▶│       RawReading             │ │
│  │  Layer      │   │  (parse only)    │   │  (canonical output type)     │ │
│  └─────────────┘   └──────────────────┘   └──────────────────────────────┘ │
│         │                  │                                                │
│  ┌──────┴──────┐   ┌───────┴───────┐                                       │
│  │ Serial      │   │ ECGAdapter    │  device_type  = DeviceType.ECG        │
│  │ USB         │   │ BPAdapter     │  device_id    = "ECG-BED-01-ICU"     │
│  │ BLE         │   │ SpO2Adapter   │  metric       = MetricType.HEART_RATE│
│  │ Socket      │   │ VentAdapter   │  value        = 72.0                  │
│  │ Simulator   │   │ InfusionAdapter│  unit        = Unit.BPM              │
│  └─────────────┘   │ GlucoAdapter  │  raw_payload  = "DAT|72|0.84|II"     │
│                    └───────────────┘                                       │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      AdapterRegistry                                │   │
│  │  DeviceType → AdapterClass  (auto-discovered from mdil/adapters/)   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 11.3 Device Abstraction Strategy

| Layer         | Responsibility                                   | Knows About         |
|---------------|--------------------------------------------------|---------------------|
| Transport     | Raw bytes in/out. Manages connection lifecycle.  | Wire protocol only  |
| Adapter       | Parse bytes → `RawReading`. Stateless.           | Frame format only   |
| Collector     | Drives transport + adapter. Owns reconnect.      | Both layers         |
| RawReading    | The single output contract of the entire MDIL.   | Nothing below       |

**Device Independence Contract:**
- Adapters **never** know which transport delivered the bytes.
- Transports **never** know which adapter will process the bytes.
- A serial ECG and a socket ECG both use `ECGAdapter` — transport is swapped at Collector level.

---

## 11.4 Data Flow Diagram

```
Physical Device / Simulator
        │
        │  Raw bytes  (serial, BLE, USB, TCP, in-memory)
        ▼
┌───────────────────┐
│   BaseTransport   │  connect() / read_frames() → AsyncIterator[bytes]
│  (async generator)│
└────────┬──────────┘
         │  bytes per frame
         ▼
┌───────────────────┐
│   BaseCollector   │  _producer_loop() → asyncio.Queue[bytes] (frame buffer)
│   (async loop)    │  _consumer_loop() → calls adapter.parse_safe(frame)
└────────┬──────────┘
         │  list[RawReading]
         ▼
┌───────────────────┐
│  DeviceAdapter    │  parse(raw_frame) → list[RawReading]
│  (stateless)      │  deterministic, no I/O, < 10ms
└────────┬──────────┘
         │  RawReading(s)
         ▼
┌───────────────────┐
│ValidationInterface│  forward(reading) → asyncio.Queue[RawReading]
│  (Prompt 4 impl.) │  Non-blocking, bounded queue
└───────────────────┘
         │
         ▼
   [Validation & Normalization — Prompt 4]
```

---

## 11.5 Sequence Diagram — Normal Frame Processing

```
Device          Transport       Collector           Adapter         ValidationQueue
  │                │                │                   │                 │
  │── bytes ──────▶│                │                   │                 │
  │                │── yield ──────▶│                   │                 │
  │                │   frame        │── parse_safe() ──▶│                 │
  │                │                │                   │── RawReading ──▶│
  │                │                │                   │   (×N)          │
  │                │                │◀── (readings, nil)─│                 │
  │                │                │── health.record_frame(N) ──────────▶│
  │                │                │── forward(reading) ─────────────────▶
```

---

## 11.6 Sequence Diagram — Frame Parse Error

```
Device          Transport       Collector           Adapter         ValidationQueue
  │                │                │                   │                 │
  │── bad bytes ──▶│                │                   │                 │
  │                │── yield ──────▶│                   │                 │
  │                │   frame        │── parse_safe() ──▶│                 │
  │                │                │                   │── AdapterParseError
  │                │                │◀── ([], error) ────│                 │
  │                │                │── health.record_parse_error()        │
  │                │                │   (no reading forwarded)             │
```

---

## 11.7 Sequence Diagram — Transport Disconnect & Reconnect

```
Collector           Transport           ExponentialBackoff
    │                   │                       │
    │── connect() ─────▶│                       │
    │                   │── OK ─────────────────│
    │── read_frames() ──▶│                       │
    │                   │── TransportReadError ─▶│
    │                   │                       │
    │── disconnect() ───▶│                       │
    │── health.mark_reconnecting()               │
    │── backoff(attempt=N, delay=1s*2^N) ───────▶│
    │                   (wait)                   │
    │── build_transport() [fresh instance]       │
    │── connect() ─────▶│ (new transport)        │
    │                   │── OK ─────────────────│
    │── read_frames() ──▶│ (reading resumes)     │
```

---

## 11.8 Collector Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          COLLECTOR LAYER                                    │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     CollectorSupervisor                              │  │
│  │  start_all() → launches each collector as asyncio.Task               │  │
│  │  _monitor_loop() → checks task health every 5s, restarts on crash    │  │
│  │  shutdown() → stops all collectors, cancels tasks, waits timeout     │  │
│  └────────────────────────────────┬─────────────────────────────────────┘  │
│           ┌────────────────────────┼─────────────────────────┐             │
│           ▼                        ▼                         ▼             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐         │
│  │  ECGCollector    │  │  BPCollector     │  │  SpO2Collector   │  ...    │
│  │  asyncio.Task    │  │  asyncio.Task    │  │  asyncio.Task    │         │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘         │
│           │                     │                      │                   │
│    Transport+Adapter      Transport+Adapter      Transport+Adapter         │
│    (fully isolated)       (fully isolated)       (fully isolated)          │
│           │                     │                      │                   │
│           └─────────────────────┴──────────────────────┘                  │
│                                 │                                          │
│                     ValidationInterface.forward()                         │
│                     asyncio.Queue[RawReading]                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 11.9 Why One Collector Per Device

| Strategy              | Justification                                          |
|-----------------------|--------------------------------------------------------|
| Failure Isolation     | One device crash cannot affect other device loops      |
| Independent Backoff   | Each device reconnects on its own schedule             |
| Per-Device Health     | Fine-grained metrics: frames/s, error rate, last read  |
| Independent Config    | Each device has its own transport + adapter config     |
| Parallel Throughput   | No head-of-line blocking across devices                |

---

## 11.10 Collector Lifecycle Diagram

```
            ┌──────────────┐
            │ INITIALIZING │  Collector constructed, not started
            └──────┬───────┘
                   │ start()
            ┌──────▼───────┐
            │  CONNECTING  │  build_transport() → transport.connect()
            └──────┬───────┘
          ┌────────┴──────────┐
          │ connect ok        │ connect failed
          ▼                   ▼
   ┌────────────┐      ┌─────────────┐
   │ CONNECTED  │      │ RECONNECTING│◀────────────────┐
   │            │      │ (backoff)   │                 │
   └─────┬──────┘      └──────┬──────┘                 │
         │                    │ retry                   │
         │ TransportReadError  └────────────────────────┘
         │                    max attempts exceeded
         │                    ▼
         │             ┌──────────┐
         │             │  FAILED  │  permanent — supervisor does not restart
         │             └──────────┘
         │ stop() called
         ▼
  ┌──────────┐
  │ DEGRADED │  >20% parse error rate — still running, flagged for review
  └────┬─────┘
       │ stop()
       ▼
  ┌──────────┐
  │ STOPPED  │  graceful shutdown complete
  └──────────┘
```

---

## 11.11 Reconnection Strategy

```
Attempt   Delay Formula            Max Cap
-------   ----------------------   -------
1         1.0s × 2^0 = 1.0s
2         1.0s × 2^1 = 2.0s
3         1.0s × 2^2 = 4.0s
4         1.0s × 2^3 = 8.0s
5         1.0s × 2^4 = 16.0s
6         1.0s × 2^5 = 32.0s
7         1.0s × 2^6 = 60.0s       ← capped at max_delay
8+        60.0s (with ±10% jitter)

Jitter: ±10% of delay to prevent thundering herd
        actual_wait = delay + random.uniform(0, delay * 0.1)
```

---

## 11.12 End-to-End Flow Walkthrough

### Input: Raw ECG Bytes

```
Raw bytes arrive on serial port /dev/ttyUSB0:
    b"DAT|72|0.84|II\r\n"
```

### Step 1: Transport reads frame

```python
# SerialTransport._read_line_frames()
line = await reader.readuntil(b"\r\n")      # b"DAT|72|0.84|II\r\n"
frame = line.rstrip(b"\r\n")               # b"DAT|72|0.84|II"
yield frame                                 # Pushed to frame buffer
```

### Step 2: Collector consumer picks frame from buffer

```python
# BaseCollector._consumer_loop()
frame = await self._frame_buffer.get()     # b"DAT|72|0.84|II"
readings, error = adapter.parse_safe(frame)
```

### Step 3: ECGAdapter parses

```python
# ECGAdapter.parse()
frame_str = "DAT|72|0.84|II"
parts = ["DAT", "72", "0.84", "II"]
heart_rate = 72.0          # float(parts[1])
amplitude_mv = 0.84        # float(parts[2])
lead = "II"                # parts[3]

# Returns:
readings = [
    RawReading(metric=MetricType.HEART_RATE, value=72.0, unit=Unit.BPM, ...),
    RawReading(metric=MetricType.ECG_LEAD_II, value=0.84, unit=Unit.MV, ...),
]
```

### Step 4: RawReading output

```python
RawReading(
    reading_id    = "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    device_type   = DeviceType.ECG,          # "ecg"
    device_id     = "ECG-BED-01-ICU",
    captured_at   = datetime(2024,6,1,12,0,0, tzinfo=timezone.utc),
    metric        = MetricType.HEART_RATE,   # "heart_rate"
    value         = 72.0,
    unit          = Unit.BPM,                # "bpm"
    raw_payload   = "DAT|72|0.84|II",
    quality       = ReadingQuality.GOOD,
    facility_id   = "FACILITY-001",
    ward          = "ICU",
    bed           = "BED-01",
    metadata      = {"lead": "II"},
)
```

### Step 5: Forwarded to ValidationInterface

```python
# QueueValidationInterface.forward()
self._queue.put_nowait(reading)
# → consumed by Validation Service (Prompt 4)
```

---

### Error Case: Malformed Frame

```
Input:  b"BADFRAME\r\n"

ECGAdapter.parse("BADFRAME"):
    frame_type = "BADFRAME"
    → raise AdapterParseError(
          "Unknown ECG frame type: 'BADFRAME'. Expected DAT|WFM|STA.",
          raw_frame="BADFRAME",
          device_id="ECG-BED-01-ICU",
          device_type=DeviceType.ECG,
      )

Collector catches via parse_safe():
    readings = []
    error    = AdapterParseError(...)
    → health.record_parse_error()  (no reading forwarded)
    → logs warning at WARN level
    → continues loop (no crash)
```

### Recovery Case: Transport Disconnect

```
SerialTransport raises TransportReadError
    → _producer_loop raises → producer task ends
    → asyncio.wait() returns first exception
    → BaseCollector catches → calls transport.disconnect()
    → health.mark_reconnecting(error)
    → exponential backoff wait
    → build_transport() → fresh SerialTransport instance
    → transport.connect() → retry
    → reading resumes from next valid frame
```

---

## 11.13 Simulator Compatibility

The `SimulatorTransport` provides full drop-in replacement for any physical transport:

```python
# Production ECG (serial):
transport = SerialTransport(device_id="ECG-001", config={"port": "/dev/ttyUSB0", ...})

# Simulator ECG (in-memory):
transport = SimulatorTransport(device_id="ECG-SIM-001")
await transport.push_frame(b"DAT|72|0.84|II")

# Collector build_transport() is swapped at runtime:
collector.build_transport = lambda: transport   # monkey-patch in tests
```

Simulators available in `mdil/simulator.py`:
- `ECGSimulator` — generates DAT, WFM, STA frames at configurable Hz
- `BPSimulator` — generates SYS/DIA/MAP/PR ASCII frames
- `SpO2Simulator` — generates 4-byte BLE binary payloads

---

## 11.14 File & Responsibility Map

| File | Responsibility |
|------|----------------|
| `mdil/schema.py` | `RawReading` dataclass + all enums — the MDIL output contract |
| `mdil/base.py` | `DeviceAdapter` abstract base + `AdapterParseError` |
| `mdil/registry.py` | `AdapterRegistry` — dynamic registration + auto-discovery |
| `mdil/simulator.py` | ECG/BP/SpO2 simulators + `run_ecg_demo()` |
| `mdil/transports/base_transport.py` | `BaseTransport` abstract base + error hierarchy |
| `mdil/transports/serial_transport.py` | RS-232/485 serial reader (pyserial-asyncio) |
| `mdil/transports/usb_transport.py` | USB HID reader (pyusb + executor) |
| `mdil/transports/ble_transport.py` | BLE GATT notification reader (bleak) |
| `mdil/transports/socket_transport.py` | TCP socket reader — raw + MLLP |
| `mdil/transports/simulator_transport.py` | In-memory asyncio.Queue transport |
| `mdil/adapters/ecg_adapter.py` | Parses DAT\|WFM\|STA ECG ASCII frames |
| `mdil/adapters/bp_adapter.py` | Parses SYS=DIA=MAP= blood pressure frames |
| `mdil/adapters/spo2_adapter.py` | Parses BLE binary + ASCII SpO2 frames |
| `mdil/adapters/ventilator_adapter.py` | Parses HL7 v2 ORU^R01 OBX segments |
| `mdil/adapters/infusion_adapter.py` | Parses binary (16-byte) + ASCII infusion frames |
| `mdil/adapters/glucometer_adapter.py` | Parses ASCII glucose frames (mmol/L + mg/dL) |
| `collectors/base/collector_base.py` | `BaseCollector` — producer/consumer loop + backoff |
| `collectors/base/health.py` | `CollectorHealth` — asyncio-safe health tracking |
| `collectors/base/supervisor.py` | `CollectorSupervisor` — start/restart/shutdown |
| `collectors/base/validation_interface.py` | Clean interface contract to Prompt 4 |
| `collectors/ecg_collector/collector.py` | ECG-specific collector (serial + socket) |
| `collectors/bp_collector/collector.py` | BP-specific collector (serial + USB) |
| `collectors/spo2_collector/collector.py` | SpO2-specific collector (BLE + serial) |
| `collectors/ventilator_collector/collector.py` | Ventilator collector (MLLP socket + serial) |
| `collectors/infusion_collector/collector.py` | Infusion pump collector (serial + socket) |
| `collectors/glucometer_collector/collector.py` | Glucometer collector (USB + serial) |
| `collectors/*/config.yaml` | Per-device transport + reconnect configuration |

---

## 11.15 Pipeline Integration Points

```
MDIL Layer Output:
    RawReading  →  ValidationInterface.forward()

Validation Interface (Prompt 4 implements):
    QueueValidationInterface → asyncio.Queue[RawReading]  (current default)
    RedisValidationInterface → Redis Streams XADD          (Prompt 4)

Prompt 4 reads from:
    ValidationInterface.get_next() or Redis Stream consumer group
    → applies clinical range validation
    → applies FHIR normalization
    → emits to downstream services
```

> **Prompt 4 contract:** The `ValidationInterface` abstract class in
> `collectors/base/validation_interface.py` is the only coupling point.
> Prompt 4 must implement `forward()`, `start()`, and `stop()`.
> No MDIL or Collector code changes are required.
