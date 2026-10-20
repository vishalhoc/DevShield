# ⚡ TurboBoost — Windows Game & Dev Mode Optimizer

A modern, high-performance Windows optimization tool built for **gamers** and **developers**. With **1-click**, safely disable background resource-hogs (services, telemetry, background apps, disk indexers) and unleash maximum CPU, RAM, and network throughput.

When you're done, **1-click restores everything** back to its exact original state using state snapshots.

---

## 🎯 Why TurboBoost?

Modern Windows runs dozens of background tasks that kill gaming FPS and slow down dev workflows:

- ❌ **Windows Search Indexer (`WSearch`)** causes random 100% disk spikes during compilation and gameplay.
- ❌ **SysMain (`Superfetch`)** aggressively caches memory, starving emulator instances and Docker containers.
- ❌ **Windows Update & Delivery Optimization (`DoSvc`)** uploads P2P updates in the background, causing ping spikes.
- ❌ **Connected User Experiences & Telemetry (`DiagTrack`)** constantly consumes CPU cycles.
- ❌ **Power Throttling** parks CPU cores and reduces clock frequencies when you need instantaneous burst power.

**TurboBoost fixes all of this with a single click.**

---

## ✨ Key Features

### 1. ⚡ 1-Click Boost & 100% Clean Restore
- **Smart Snapshot Engine**: Before stopping any service, TurboBoost scans and records which services were *actually* running.
- When you click **Restore Normal Mode**, it restarts *only* the services that were previously active — never breaking your system configuration.
- Saves your original Windows Power Scheme GUID and restores it cleanly.

### 2. 🎛️ Pre-configured & Custom Profiles
- 🚀 **Extreme Game Mode**: Maximum FPS, minimum input latency, disables telemetry, stops indexing, switches power plan to Ultimate Performance, disables network packet throttling.
- 💻 **Heavy Dev Mode**: Optimized for Android Studio, Gradle, Docker, and IDEs. Halts indexing, frees standby RAM cache, sets high performance power scheme.
- ⚡ **Balanced Boost**: Safe daily boost. Kills telemetry & diagnostic tracking, keeps Bluetooth and printers available.
- 💾 **Custom Profiles**: Select any combination of 22+ services, system tweaks, and background apps, then click **Save Profile** to reuse anytime.

### 3. ⚙️ Granular Windows Service Controls (22+ Services)
Includes detailed explanations and safety ratings for:
- `WSearch` (Windows Search Indexer)
- `SysMain` (Superfetch)
- `Spooler` (Print Spooler)
- `DiagTrack` & `dmwappushservice` (Microsoft Telemetry)
- `WerSvc` (Windows Error Reporting)
- `DoSvc` (Delivery Optimization P2P uploads)
- `wuauserv` & `BITS` (Windows Update & Background Transfer)
- `RemoteRegistry`, `MapsBroker`, `lfsvc`, `TabletInputService`, `TrkWks`, `Fax`
- Xbox Services (`XblAuthManager`, `XblGameSave`, `XboxNetApiSvc`)

### 4. 🚀 System & Network Tweaks
- **High / Ultimate Performance Power Scheme**: Unlocks zero-latency CPU clock states.
- **RAM Working Set Purge**: Cleans dirty memory pages and standby cache using Windows `EmptyWorkingSet` API.
- **Windows Game Mode**: Enables OS game thread scheduling prioritization.
- **Disable Network Packet Throttling**: Sets `NetworkThrottlingIndex` to `0xffffffff` in registry for lowest multiplayer ping.
- **System Responsiveness**: Sets `SystemResponsiveness` to `0` (dedicating 100% CPU priority to foreground applications).
- **DNS Resolver Flush**: Instant DNS cache cleanup.

### 5. 🛑 Background App Terminator
- Detects running background resource hogs: OneDrive, Discord, Spotify, Epic Games Launcher, Steam, Teams, Cortana, Phone Link, Dropbox.
- Selectively terminates them when activating boost.

### 6. 📊 Real-time Monitoring & System Tray
- Live CPU & RAM gauges with GB memory indicators.
- Minimize to System Tray with quick 1-click Boost / Restore / RAM clean actions.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch TurboBoost
```bash
# Launch with GUI
python turboboost.py

# Or double-click the launcher:
run_turboboost.bat
```
*(Auto-requests Administrator privileges required for service management)*

---

## 📸 Usage Guide

1. **Select a Profile** from the dropdown (`Extreme Game Mode`, `Heavy Dev Mode`, or `Balanced Boost`).
2. Click **⚡ ACTIVATE BOOST (1-CLICK)**.
3. Your system is now optimized for maximum performance.
4. When finished, click **🟢 RESTORE NORMAL MODE (1-CLICK RESTORE)** to return all services and settings to normal.
5. You can also customize any checkmark, enter a new name under **Profiles & Restore**, and click **Save Profile Now**!

---

## 📄 License
MIT License. Free and open source.
