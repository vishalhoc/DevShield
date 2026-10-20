"""
TurboBoost Core Engine
Handles service stopping/starting, snapshot management for 1-click restore,
power plan switching, RAM cleaning, network tweaks, and process termination.
"""

import ctypes
import json
import os
import subprocess
import sys
import time
import winreg
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import psutil
except ImportError:
    psutil = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILES_FILE = os.path.join(BASE_DIR, "profiles.json")
SNAPSHOT_FILE = os.path.join(BASE_DIR, "snapshot.json")

# ─── Service Definitions ─────────────────────────────────────────────────────

SERVICES_DB = [
    {
        "id": "WSearch",
        "name": "Windows Search Indexer",
        "category": "High Disk I/O",
        "description": "Indexes files in the background. High disk/CPU thrashing during gaming and compiling.",
        "safe_level": "Safe"
    },
    {
        "id": "SysMain",
        "name": "SysMain (Superfetch)",
        "category": "High Disk I/O",
        "description": "Pre-loads apps into RAM. Frequently causes 100% disk usage and unwanted memory consumption.",
        "safe_level": "Safe"
    },
    {
        "id": "Spooler",
        "name": "Print Spooler",
        "category": "Hardware & Devices",
        "description": "Printer queue manager. Completely useless while gaming or compiling unless actively printing.",
        "safe_level": "Safe"
    },
    {
        "id": "DiagTrack",
        "name": "Connected User Experiences (Telemetry)",
        "category": "Telemetry & Tracking",
        "description": "Microsoft background telemetry and data collection service. Wastes CPU cycles.",
        "safe_level": "Safe"
    },
    {
        "id": "dmwappushservice",
        "name": "WAP Push Routing (Telemetry)",
        "category": "Telemetry & Tracking",
        "description": "Associated with Windows telemetry collection.",
        "safe_level": "Safe"
    },
    {
        "id": "WerSvc",
        "name": "Windows Error Reporting",
        "category": "Telemetry & Tracking",
        "description": "Captures and sends error crash reports to Microsoft.",
        "safe_level": "Safe"
    },
    {
        "id": "DoSvc",
        "name": "Delivery Optimization (P2P Update Sharing)",
        "category": "Network & Updates",
        "description": "Uploads and shares Windows update files peer-to-peer over your internet connection.",
        "safe_level": "Safe"
    },
    {
        "id": "wuauserv",
        "name": "Windows Update",
        "category": "Network & Updates",
        "description": "Checks, downloads, and installs updates in background. Can cause sudden ping spikes and stutter.",
        "safe_level": "Safe"
    },
    {
        "id": "BITS",
        "name": "Background Intelligent Transfer Service",
        "category": "Network & Updates",
        "description": "Transfers files asynchronously using idle network bandwidth.",
        "safe_level": "Safe"
    },
    {
        "id": "XblAuthManager",
        "name": "Xbox Live Auth Manager",
        "category": "Xbox Services",
        "description": "Xbox authentication. Disable for non-Xbox games or dev work.",
        "safe_level": "Optional"
    },
    {
        "id": "XblGameSave",
        "name": "Xbox Live Game Save",
        "category": "Xbox Services",
        "description": "Cloud saving for Xbox App titles. Disable if not playing Xbox PC Game Pass titles.",
        "safe_level": "Optional"
    },
    {
        "id": "XboxNetApiSvc",
        "name": "Xbox Live Networking Service",
        "category": "Xbox Services",
        "description": "Xbox Live networking layer.",
        "safe_level": "Optional"
    },
    {
        "id": "XboxGipSvc",
        "name": "Xbox Accessory Management",
        "category": "Xbox Services",
        "description": "Manages Xbox wired/wireless accessories.",
        "safe_level": "Optional"
    },
    {
        "id": "bthserv",
        "name": "Bluetooth Support Service",
        "category": "Hardware & Devices",
        "description": "Bluetooth device support. Disable if you use wired mouse/keyboard/headset.",
        "safe_level": "Optional"
    },
    {
        "id": "RemoteRegistry",
        "name": "Remote Registry",
        "category": "Security & Network",
        "description": "Allows remote users to modify Windows registry. Almost never needed locally.",
        "safe_level": "Safe"
    },
    {
        "id": "MapsBroker",
        "name": "Downloaded Maps Manager",
        "category": "Background Apps",
        "description": "Downloads and updates offline Windows Maps.",
        "safe_level": "Safe"
    },
    {
        "id": "lfsvc",
        "name": "Geolocation Service",
        "category": "Background Apps",
        "description": "Monitors system geographical location.",
        "safe_level": "Safe"
    },
    {
        "id": "TabletInputService",
        "name": "Touch Keyboard & Handwriting",
        "category": "Hardware & Devices",
        "description": "Touch keyboard pen & ink service. Unnecessary for desktop mice and keyboards.",
        "safe_level": "Safe"
    },
    {
        "id": "TrkWks",
        "name": "Distributed Link Tracking Client",
        "category": "System Maintenance",
        "description": "Maintains links between NTFS files across network domains.",
        "safe_level": "Safe"
    },
    {
        "id": "Fax",
        "name": "Fax Service",
        "category": "System Maintenance",
        "description": "Manages sending and receiving faxes.",
        "safe_level": "Safe"
    },
    {
        "id": "wisvc",
        "name": "Windows Insider Service",
        "category": "Telemetry & Tracking",
        "description": "Infrastructure for Windows Insider preview program.",
        "safe_level": "Safe"
    },
    {
        "id": "RetailDemo",
        "name": "Retail Demo Service",
        "category": "System Maintenance",
        "description": "Used by stores for retail display mode.",
        "safe_level": "Safe"
    }
]

# Common background processes to close on boost
BACKGROUND_TARGETS = [
    {"name": "OneDrive.exe", "display": "Microsoft OneDrive", "desc": "Cloud sync background process"},
    {"name": "Spotify.exe", "display": "Spotify", "desc": "Music streaming app"},
    {"name": "Discord.exe", "display": "Discord", "desc": "Voice and chat app"},
    {"name": "EpicGamesLauncher.exe", "display": "Epic Games Launcher", "desc": "Game store client"},
    {"name": "Battle.net.exe", "display": "Battle.net Client", "desc": "Blizzard game launcher"},
    {"name": "Steam.exe", "display": "Steam Client (Background)", "desc": "Game platform client"},
    {"name": "Teams.exe", "display": "Microsoft Teams", "desc": "Work chat and video app"},
    {"name": "ms-teams.exe", "display": "Microsoft Teams (New)", "desc": "New Teams background client"},
    {"name": "Skype.exe", "display": "Skype", "desc": "Video/voice call client"},
    {"name": "Dropbox.exe", "display": "Dropbox", "desc": "File sync process"},
    {"name": "PhoneExperienceHost.exe", "display": "Phone Link", "desc": "Windows mobile phone sync"},
    {"name": "Cortana.exe", "display": "Cortana Assistant", "desc": "Voice assistant background task"},
    {"name": "WhatsApp.exe", "display": "WhatsApp Desktop", "desc": "Messaging app"},
    {"name": "Slack.exe", "display": "Slack", "desc": "Messaging app"}
]

# ─── Default Profiles ────────────────────────────────────────────────────────

DEFAULT_PROFILES = {
    "Extreme Game Mode": {
        "description": "Maximum FPS, ultra-low input latency. Stops Search, SysMain, Spooler, Updates, Telemetry, sets High/Ultimate power plan, optimizes network throttling.",
        "services": [
            "WSearch", "SysMain", "Spooler", "DiagTrack", "dmwappushservice",
            "WerSvc", "DoSvc", "wuauserv", "BITS", "RemoteRegistry",
            "MapsBroker", "lfsvc", "TabletInputService", "TrkWks", "Fax",
            "wisvc", "RetailDemo"
        ],
        "tweaks": {
            "power_plan": True,              # Switch to High/Ultimate Performance
            "clean_ram": True,                # Empty working sets & cache
            "game_mode": True,                # Enable Windows Game Mode
            "network_throttling": True,       # Disable network throttling (0xffffffff)
            "system_responsiveness": True,    # 100% CPU priority for foreground games (0)
            "flush_dns": True                 # Flush DNS resolver cache
        },
        "kill_background_apps": [
            "OneDrive.exe", "Spotify.exe", "PhoneExperienceHost.exe",
            "Cortana.exe", "Skype.exe", "Dropbox.exe"
        ]
    },
    "Heavy Dev Mode": {
        "description": "Maximum compile speed, instant I/O response for Gradle, Docker, Android Studio, IDEs. Stops indexing, SysMain, Updates, purges RAM cache.",
        "services": [
            "WSearch", "SysMain", "Spooler", "DiagTrack", "dmwappushservice",
            "WerSvc", "DoSvc", "wuauserv", "BITS", "RemoteRegistry",
            "MapsBroker", "lfsvc", "TabletInputService", "TrkWks", "Fax"
        ],
        "tweaks": {
            "power_plan": True,
            "clean_ram": True,
            "game_mode": False,
            "network_throttling": True,
            "system_responsiveness": True,
            "flush_dns": True
        },
        "kill_background_apps": [
            "OneDrive.exe", "Spotify.exe", "PhoneExperienceHost.exe",
            "Cortana.exe", "Skype.exe"
        ]
    },
    "Balanced Boost": {
        "description": "Safe daily boost. Stops telemetry, diagnostic tracking, and cleans RAM. Keeps Bluetooth, printing, and Windows Update available.",
        "services": [
            "DiagTrack", "dmwappushservice", "WerSvc", "RemoteRegistry",
            "MapsBroker", "lfsvc", "TabletInputService", "Fax", "RetailDemo"
        ],
        "tweaks": {
            "power_plan": True,
            "clean_ram": True,
            "game_mode": True,
            "network_throttling": False,
            "system_responsiveness": False,
            "flush_dns": False
        },
        "kill_background_apps": []
    }
}


# ─── Privilege & Helper Utilities ────────────────────────────────────────────

def is_admin() -> bool:
    """Check if the current script is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def run_as_admin():
    """Relaunch the current script with administrator elevation."""
    script = os.path.abspath(sys.argv[0])
    params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
    try:
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
        if ret > 32:
            sys.exit(0)
    except Exception:
        pass
    # Fallback via PowerShell
    try:
        ps_cmd = f'Start-Process python -ArgumentList \'"{script}" {params}\' -Verb RunAs'
        subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_cmd])
        sys.exit(0)
    except Exception:
        pass


def run_command(cmd: str) -> tuple[str, str, int]:
    """Execute a system shell command safely."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), -1


# ─── Power Scheme Utilities ──────────────────────────────────────────────────

def get_active_power_scheme() -> Optional[str]:
    """Get the GUID of the currently active Windows Power Scheme."""
    stdout, _, code = run_command("powercfg /getactivescheme")
    if code == 0 and "GUID:" in stdout:
        parts = stdout.split("GUID:")
        if len(parts) > 1:
            guid = parts[1].strip().split()[0]
            return guid
    return None


def get_available_power_schemes() -> Dict[str, str]:
    """Get all existing power scheme GUIDs mapped to their friendly names."""
    schemes = {}
    stdout, _, code = run_command("powercfg /list")
    if code == 0:
        for line in stdout.splitlines():
            if "GUID:" in line:
                try:
                    parts = line.split("GUID:")
                    guid_and_name = parts[1].strip()
                    guid = guid_and_name.split()[0]
                    # Extract name inside parentheses e.g. (High performance)
                    if "(" in guid_and_name and ")" in guid_and_name:
                        name = guid_and_name[guid_and_name.find("(")+1:guid_and_name.rfind(")")]
                    else:
                        name = "Custom Scheme"
                    schemes[guid] = name
                except Exception:
                    pass
    return schemes


def set_power_scheme(guid: str) -> bool:
    """Set the active Windows Power Scheme."""
    _, _, code = run_command(f"powercfg /setactive {guid}")
    return code == 0


def ensure_high_or_ultimate_performance() -> Optional[str]:
    """
    Find or unlock Ultimate / High Performance plan and switch to it.
    Returns the applied GUID.
    """
    schemes = get_available_power_schemes()

    # Look for Ultimate Performance first
    for guid, name in schemes.items():
        if "ultimate" in name.lower():
            set_power_scheme(guid)
            return guid

    # Try unlocking Ultimate Performance if not already available
    stdout, _, code = run_command("powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61")
    if code == 0 and "GUID:" in stdout:
        try:
            new_guid = stdout.split("GUID:")[1].strip().split()[0]
            set_power_scheme(new_guid)
            return new_guid
        except Exception:
            pass

    # Fallback to High Performance
    for guid, name in schemes.items():
        if "high performance" in name.lower():
            set_power_scheme(guid)
            return guid

    # Standard High performance GUID fallback
    high_perf_guid = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
    set_power_scheme(high_perf_guid)
    return high_perf_guid


# ─── Windows Service Operations ──────────────────────────────────────────────

def get_service_status(service_name: str) -> str:
    """Return status of service: 'Running', 'Stopped', or 'NotFound'."""
    cmd = f'powershell -NoProfile -Command "(Get-Service -Name {service_name} -ErrorAction SilentlyContinue).Status"'
    stdout, _, code = run_command(cmd)
    if code == 0 and stdout:
        return stdout.strip()
    return "NotFound"


def get_all_services_status(service_ids: List[str]) -> Dict[str, str]:
    """Batch query service statuses for high performance UI updates."""
    if not service_ids:
        return {}
    ids_str = ",".join([f"'{s}'" for s in service_ids])
    cmd = f'powershell -NoProfile -Command "Get-Service -Name {ids_str} -ErrorAction SilentlyContinue | Select-Object -Property Name, Status | ForEach-Object {{ $_.Name + \':\' + $_.Status }}"'
    stdout, _, code = run_command(cmd)
    result = {sid: "Stopped" for sid in service_ids}
    if code == 0 and stdout:
        for line in stdout.splitlines():
            if ":" in line:
                name, status = line.split(":", 1)
                result[name.strip()] = status.strip()
    return result


def stop_service(service_name: str) -> bool:
    """Stop a Windows service gracefully."""
    cmd = f'powershell -NoProfile -Command "Stop-Service -Name {service_name} -Force -ErrorAction SilentlyContinue"'
    _, _, code = run_command(cmd)
    return code == 0


def start_service(service_name: str) -> bool:
    """Start a Windows service."""
    cmd = f'powershell -NoProfile -Command "Start-Service -Name {service_name} -ErrorAction SilentlyContinue"'
    _, _, code = run_command(cmd)
    return code == 0


# ─── RAM Cleaning & Process Trimming ─────────────────────────────────────────

def clean_system_ram() -> Dict[str, Any]:
    """
    Purge working sets across running processes using Windows EmptyWorkingSet API.
    Releases dirty and standby memory pages back to the system.
    """
    freed_processes = 0
    failed_processes = 0
    ram_before = psutil.virtual_memory().used if psutil else 0

    if psutil:
        for p in psutil.process_iter(['pid', 'name']):
            try:
                pid = p.info['pid']
                if pid <= 4:
                    continue  # Skip System / Idle
                # PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION = 0x0100 | 0x0400 = 0x0500
                handle = ctypes.windll.kernel32.OpenProcess(0x0500, False, pid)
                if handle:
                    res = ctypes.windll.psapi.EmptyWorkingSet(handle)
                    ctypes.windll.kernel32.CloseHandle(handle)
                    if res:
                        freed_processes += 1
                    else:
                        failed_processes += 1
            except Exception:
                failed_processes += 1

    ram_after = psutil.virtual_memory().used if psutil else 0
    diff_mb = max(0, round((ram_before - ram_after) / (1024 * 1024), 1))

    return {
        "processes_trimmed": freed_processes,
        "memory_freed_mb": diff_mb,
        "ram_used_percent": psutil.virtual_memory().percent if psutil else 0
    }


# ─── Registry & Network Tweaks ───────────────────────────────────────────────

def set_game_mode(enable: bool = True) -> bool:
    """Enable or disable Windows Game Mode in registry."""
    try:
        key_path = r"Software\Microsoft\GameBar"
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        val = 1 if enable else 0
        winreg.SetValueEx(key, "AllowAutoGameMode", 0, winreg.REG_DWORD, val)
        winreg.SetValueEx(key, "AutoGameModeEnabled", 0, winreg.REG_DWORD, val)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def set_network_and_system_responsiveness(boost: bool = True) -> Dict[str, Any]:
    """
    Tweak Multimedia SystemProfile in registry:
    - NetworkThrottlingIndex: 0xffffffff (boost) vs 0x0000000a (default 10)
    - SystemResponsiveness: 0 (boost 100% priority) vs 20 (default 20%)
    """
    key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
    original_values = {}
    try:
        # Read current/original values before applying
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ) as key:
            try:
                original_values["NetworkThrottlingIndex"], _ = winreg.QueryValueEx(key, "NetworkThrottlingIndex")
            except Exception:
                original_values["NetworkThrottlingIndex"] = 10
            try:
                original_values["SystemResponsiveness"], _ = winreg.QueryValueEx(key, "SystemResponsiveness")
            except Exception:
                original_values["SystemResponsiveness"] = 20

        # Apply tweaks
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if boost:
                # 0xffffffff disables network throttling
                winreg.SetValueEx(key, "NetworkThrottlingIndex", 0, winreg.REG_DWORD, 0xffffffff)
                winreg.SetValueEx(key, "SystemResponsiveness", 0, winreg.REG_DWORD, 0)
            else:
                winreg.SetValueEx(key, "NetworkThrottlingIndex", 0, winreg.REG_DWORD, original_values.get("NetworkThrottlingIndex", 10))
                winreg.SetValueEx(key, "SystemResponsiveness", 0, winreg.REG_DWORD, original_values.get("SystemResponsiveness", 20))
    except Exception:
        pass
    return original_values


def flush_dns_cache() -> bool:
    """Flush the Windows DNS client resolver cache."""
    _, _, code = run_command("ipconfig /flushdns")
    return code == 0


# ─── Background App Killer ───────────────────────────────────────────────────

def scan_running_background_apps() -> List[Dict[str, Any]]:
    """Scan which target background apps are currently running."""
    running_apps = []
    if not psutil:
        return running_apps

    running_names = set()
    for p in psutil.process_iter(['name']):
        try:
            running_names.add(p.info['name'].lower())
        except Exception:
            pass

    for target in BACKGROUND_TARGETS:
        is_running = target["name"].lower() in running_names
        running_apps.append({
            "name": target["name"],
            "display": target["display"],
            "desc": target["desc"],
            "running": is_running
        })
    return running_apps


def terminate_background_apps(target_names: List[str]) -> List[str]:
    """Terminate selected background apps and return list of killed process names."""
    killed = []
    if not psutil or not target_names:
        return killed

    targets_lower = {t.lower() for t in target_names}
    for p in psutil.process_iter(['pid', 'name']):
        try:
            p_name = p.info['name']
            if p_name.lower() in targets_lower:
                p.kill()
                killed.append(p_name)
        except Exception:
            pass
    return list(set(killed))


# ─── Snapshot & Restore Engine ───────────────────────────────────────────────

class TurboBoostEngine:
    """
    Central controller for TurboBoost:
    - Maintains live state
    - Records precise snapshots of active services before disabling them
    - Restores only what was originally running on 1-click restore
    - Manages profile persistence
    """

    def __init__(self):
        self.profiles = self.load_profiles()
        self.snapshot = self.load_snapshot()

    def is_boosted(self) -> bool:
        """Check if TurboBoost is currently active."""
        return self.snapshot.get("is_boosted", False)

    def load_profiles(self) -> Dict[str, Any]:
        """Load profiles from JSON file or create with defaults."""
        if os.path.exists(PROFILES_FILE):
            try:
                with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        # Save defaults
        self.save_profiles(DEFAULT_PROFILES)
        return DEFAULT_PROFILES

    def save_profiles(self, profiles: Dict[str, Any]):
        """Persist profiles to file."""
        try:
            with open(PROFILES_FILE, "w", encoding="utf-8") as f:
                json.dump(profiles, f, indent=4)
            self.profiles = profiles
        except Exception:
            pass

    def load_snapshot(self) -> Dict[str, Any]:
        """Load existing snapshot file."""
        if os.path.exists(SNAPSHOT_FILE):
            try:
                with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"is_boosted": False}

    def save_snapshot(self, snapshot_data: Dict[str, Any]):
        """Save state snapshot to file."""
        try:
            with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
                json.dump(snapshot_data, f, indent=4)
            self.snapshot = snapshot_data
        except Exception:
            pass

    def clear_snapshot(self):
        """Mark snapshot as not boosted."""
        self.snapshot["is_boosted"] = False
        self.save_snapshot(self.snapshot)

    def activate_boost(self, profile_name: str = "Extreme Game Mode", custom_config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        1-Click Enable Game/Dev Mode:
        1. Query and record all target services that are currently RUNNING.
        2. Record current active power scheme.
        3. Record original network & system responsiveness registry values.
        4. Save everything to snapshot.json.
        5. Stop the selected services.
        6. Apply power plan, registry optimizations, RAM cleaning, and close target apps.
        """
        # Determine config
        if custom_config:
            config = custom_config
        else:
            config = self.profiles.get(profile_name, DEFAULT_PROFILES["Extreme Game Mode"])

        target_services = config.get("services", [])
        tweaks = config.get("tweaks", {})
        kill_apps = config.get("kill_background_apps", [])

        # Step 1: Detect which services are currently Running
        status_map = get_all_services_status(target_services)
        services_to_stop = [s_id for s_id, status in status_map.items() if status.lower() == "running"]

        # Step 2: Record original power scheme
        original_power_scheme = get_active_power_scheme()

        # Step 3: Stop the running target services
        stopped_successfully = []
        for s_id in services_to_stop:
            if stop_service(s_id):
                stopped_successfully.append(s_id)

        # Step 4: Apply Tweaks
        applied_tweaks = {}
        applied_power_guid = None
        if tweaks.get("power_plan", False):
            applied_power_guid = ensure_high_or_ultimate_performance()
            applied_tweaks["power_plan"] = applied_power_guid

        if tweaks.get("game_mode", False):
            set_game_mode(True)
            applied_tweaks["game_mode"] = True

        orig_multimedia = {}
        if tweaks.get("network_throttling", False) or tweaks.get("system_responsiveness", False):
            orig_multimedia = set_network_and_system_responsiveness(boost=True)
            applied_tweaks["network_throttling"] = True
            applied_tweaks["system_responsiveness"] = True

        if tweaks.get("flush_dns", False):
            flush_dns_cache()
            applied_tweaks["flush_dns"] = True

        # Step 5: Terminate background apps
        killed_apps = []
        if kill_apps:
            killed_apps = terminate_background_apps(kill_apps)

        # Step 6: Clean RAM
        ram_report = {}
        if tweaks.get("clean_ram", False):
            ram_report = clean_system_ram()

        # Step 7: Save Complete Snapshot
        snapshot = {
            "is_boosted": True,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "profile_name": profile_name,
            "stopped_services": stopped_successfully,
            "original_power_scheme": original_power_scheme,
            "original_network_values": orig_multimedia,
            "killed_apps": killed_apps,
            "applied_tweaks": applied_tweaks,
            "config_used": config
        }
        self.save_snapshot(snapshot)

        return {
            "status": "success",
            "profile_name": profile_name,
            "services_stopped_count": len(stopped_successfully),
            "services_stopped": stopped_successfully,
            "killed_apps_count": len(killed_apps),
            "ram_report": ram_report,
            "power_scheme": applied_power_guid
        }

    def restore_normal_mode(self) -> Dict[str, Any]:
        """
        1-Click Restore Normal Mode:
        1. Reads snapshot.json.
        2. Restarts ONLY the services that were previously stopped by TurboBoost.
        3. Restores the user's original Windows Power Scheme.
        4. Restores original network & responsiveness registry values.
        5. Flushes memory and clears boost state.
        """
        snapshot = self.load_snapshot()
        if not snapshot.get("is_boosted", False):
            return {"status": "not_boosted", "message": "System is already in Normal Mode."}

        stopped_services = snapshot.get("stopped_services", [])
        original_power = snapshot.get("original_power_scheme", None)
        orig_net_vals = snapshot.get("original_network_values", {})

        # Step 1: Restart only the services that were stopped
        restarted_services = []
        for s_id in stopped_services:
            if start_service(s_id):
                restarted_services.append(s_id)

        # Step 2: Restore Power Scheme
        if original_power:
            set_power_scheme(original_power)

        # Step 3: Restore Registry Multimedia Values
        if orig_net_vals:
            try:
                key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    if "NetworkThrottlingIndex" in orig_net_vals:
                        winreg.SetValueEx(key, "NetworkThrottlingIndex", 0, winreg.REG_DWORD, orig_net_vals["NetworkThrottlingIndex"])
                    if "SystemResponsiveness" in orig_net_vals:
                        winreg.SetValueEx(key, "SystemResponsiveness", 0, winreg.REG_DWORD, orig_net_vals["SystemResponsiveness"])
            except Exception:
                pass

        # Step 4: Reset Game Mode
        set_game_mode(False)

        # Step 5: Clean RAM working set
        clean_system_ram()

        # Step 6: Mark snapshot as restored
        self.clear_snapshot()

        return {
            "status": "success",
            "restarted_services_count": len(restarted_services),
            "restarted_services": restarted_services,
            "power_scheme_restored": original_power
        }

    def save_custom_profile(self, name: str, description: str, services: List[str], tweaks: Dict[str, bool], kill_apps: List[str]):
        """Create or update a custom profile and persist it."""
        self.profiles[name] = {
            "description": description or f"Custom profile: {name}",
            "services": services,
            "tweaks": tweaks,
            "kill_background_apps": kill_apps
        }
        self.save_profiles(self.profiles)

    def delete_profile(self, name: str) -> bool:
        """Delete a profile if it's not a protected default."""
        if name in DEFAULT_PROFILES:
            return False  # Protected
        if name in self.profiles:
            del self.profiles[name]
            self.save_profiles(self.profiles)
            return True
        return False
