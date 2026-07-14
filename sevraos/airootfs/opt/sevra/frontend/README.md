# SevraOS Patient Terminal Frontend

This directory contains the completed user interface and patient terminal application for the [Sevra Healthcare Operating Ecosystem](file:///c:/Users/ThePC/SevraOS/README.md). It provides real-time patient monitoring, clinical records, interactive telemetry, diagnostic reports, medical history timeline, and edge settings.

It integrates directly with the [SevraOS Edge Telemetry Backend](file:///c:/Users/ThePC/SevraOS/backend/README.md) using WebSocket endpoints for vitals streaming.

## 🚀 Technical Stack

- **Core**: HTML5, Vanilla JavaScript, CSS3
- **Aesthetics**: Premium dark glassmorphism (translucent cards with backdrop blur, glowing neon states) and responsive flex/grid layouts.
- **Charts & Waves**: HTML5 Canvas rendering for real-time scrolling wave logic (ECG/SpO2) and status risk indicators.
- **Icons & Fonts**: Google Fonts (Outfit) and Google Material Symbols.

## 📁 File Structure

- 🖥️ **[index.html](file:///c:/Users/ThePC/SevraOS/frontend/index.html)**: Main frame structure housing the sidebar navigation, patient telemetry header, and the 7 main view panels (including the new Setup Guide).
- 🎨 **[index.css](file:///c:/Users/ThePC/SevraOS/frontend/index.css)**: Core design system stylesheet detailing responsive grids, modal layers, custom progress rings, animations, and Dark/Light theme values.
- ⚙️ **[index.js](file:///c:/Users/ThePC/SevraOS/frontend/index.js)**: Application logic handling sidebar panels, canvas rendering cycles, scan comparisons, local data binding, and WebSocket API listeners.

## 🛠️ Interactive Features

1. **Telemetry Stream**: Simulated heartbeat spike (PQRST) and pulse cycle scrolling waveforms drawn on canvas.
2. **Scan Comparison**: Interactive split slider to compare historical and current CT scans with draggable handle.
3. **Theme Engine**: Toggle between Default Dark Mode and High-Contrast Light Mode directly from the Settings tab.
4. **Case Control**: Interactive confirmation dialog overlay to securely close or reset cases.
5. **Setup Guide**: Embedded step-by-step documentation detailing edge backend, production stacks, and operating system build guidelines.
