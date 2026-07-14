# Telemetry Simulation Module

This folder contains helper utilities to generate simulated patient data streams for testing the SevraOS patient terminal UI, edge backend, and Central Redis Event Bus integrations. It acts as the simulation zone of the wider [Sevra Healthcare Operating Ecosystem](file:///c:/Users/ThePC/SevraOS/README.md).

## 🛠️ Telemetry Generator (Console Output)

[telemetry_generator.py](file:///c:/Users/ThePC/SevraOS/simulations/telemetry_generator.py) simulates a real-time patient gateway. It outputs a scrolling console screen printing Heart Rate, Blood Pressure, SpO2, Temperature, and a live ASCII ECG waveform.

### Running the Generator

Ensure you have Python installed, then run directly:

```bash
python simulations/telemetry_generator.py
```

Press `Ctrl+C` in your terminal to exit the simulator.

---

## 📡 Redis Event Bus Simulator

[simulate.py](file:///c:/Users/ThePC/SevraOS/simulations/simulate.py) simulates a medical monitor pushing live high-frequency heart rate readings into the Redis Event Bus stream (`helios.telemetry.raw`) for ingestion by the backend.

### Running the Redis Simulator

Ensure you have the `redis` library installed:

```bash
pip install redis
```

Run the script:

```bash
python simulations/simulate.py
```

For full deployment testing steps, refer to the [System Deployment Guide](file:///c:/Users/ThePC/SevraOS/docs/architecture/deployment_guide.md).
