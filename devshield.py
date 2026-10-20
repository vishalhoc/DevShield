"""
DevShield - Developer-Friendly Windows Defender Manager
========================================================
System tray tool to manage Windows Defender exclusions and real-time
protection for improved development performance.

Requires: Run as Administrator for all operations.
"""

import ctypes
import json
import os
import subprocess
import sys
import threading
import winreg
from pathlib import Path

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Installing required packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pystray", "Pillow"])
    import pystray
    from PIL import Image, ImageDraw, ImageFont


# ─── Constants ────────────────────────────────────────────────────────────────

APP_NAME = "DevShield"
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
SCRIPTS_DIR = os.path.join(APP_DIR, "_scripts")
LAUNCHER_VBS = os.path.join(APP_DIR, "devshield_silent.vbs")
STARTUP_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


# ─── Hide Console Window ────────────────────────────────────────────────────

def hide_console():
    """Hide the console window immediately."""
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
    except Exception:
        pass


# ─── Utility Functions ───────────────────────────────────────────────────────

def is_admin():
    """Check if the current process has administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def run_as_admin():
    """Relaunch the script with administrator privileges (hidden)."""
    script = os.path.abspath(__file__)
    # Use pythonw.exe to avoid console window on relaunch
    python_exe = _get_pythonw()
    ctypes.windll.shell32.ShellExecuteW(None, "runas", python_exe, f'"{script}"', None, 0)
    sys.exit(0)


def _get_pythonw():
    """Get path to pythonw.exe (no console window)."""
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    if os.path.exists(pythonw):
        return pythonw
    # Fallback: try replacing python.exe with pythonw.exe in the path
    if sys.executable.lower().endswith("python.exe"):
        candidate = sys.executable[:-10] + "pythonw.exe"
        if os.path.exists(candidate):
            return candidate
    return sys.executable  # fallback to python.exe


def expand_path(path_str):
    """Expand environment variables in a path string."""
    return os.path.expandvars(path_str)


def load_config():
    """Load exclusion configuration from config.json."""
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"exclusion_folders": [], "exclusion_processes": []}


def run_ps_script(script_content):
    """
    Write a PowerShell script to a temp file and execute it.
    This avoids all escaping issues with $true/$false and special characters.
    """
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    script_path = os.path.join(SCRIPTS_DIR, "_devshield_cmd.ps1")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    args = [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", script_path
    ]
    result = subprocess.run(
        args, capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def notify(icon, title, message):
    """Send a system tray notification."""
    try:
        icon.notify(message, title)
    except Exception:
        pass


def msgbox(title, message, style=0x40):
    """Show a Windows message box. style: 0x40=Info, 0x30=Warning, 0x10=Error."""
    threading.Thread(
        target=lambda: ctypes.windll.user32.MessageBoxW(0, message, title, style),
        daemon=True
    ).start()


# ─── Startup Management ─────────────────────────────────────────────────────

def _get_startup_command():
    """Build the command that should run at startup (elevated + hidden)."""
    _ensure_vbs_launcher()
    return f'wscript.exe "{LAUNCHER_VBS}"'


def _ensure_vbs_launcher():
    """Create a VBS launcher that runs DevShield silently with admin elevation."""
    script = os.path.abspath(__file__)
    pythonw = _get_pythonw()
    vbs_content = (
        'Set objShell = CreateObject("Shell.Application")\n'
        f'objShell.ShellExecute "{pythonw}", """{script}""", "", "runas", 0\n'
    )
    with open(LAUNCHER_VBS, "w") as f:
        f.write(vbs_content)


def is_startup_enabled():
    """Check if DevShield is in the Windows startup registry."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


def enable_startup():
    """Add DevShield to Windows startup."""
    try:
        _ensure_vbs_launcher()
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_SET_VALUE)
        cmd = _get_startup_command()
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        return False


def disable_startup():
    """Remove DevShield from Windows startup."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


# ─── Icon Generation ─────────────────────────────────────────────────────────

def create_icon(color="green"):
    """Create a tray icon image. Green = protected, Orange = exclusions active, Red = RT off."""
    colors = {
        "green": "#4CAF50",
        "orange": "#FF9800",
        "red": "#F44336",
        "gray": "#9E9E9E"
    }
    fill = colors.get(color, colors["green"])

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Shield shape
    draw.rounded_rectangle([8, 4, 56, 56], radius=8, fill=fill, outline="white", width=2)

    # "D" letter for DevShield
    try:
        font = ImageFont.truetype("arial.ttf", 32)
    except (OSError, IOError):
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), "D", font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((64 - tw) / 2, (64 - th) / 2 - 4), "D", fill="white", font=font)

    return img


# ─── Defender Status ─────────────────────────────────────────────────────────

def is_tamper_protected():
    """Check if Tamper Protection is enabled."""
    out, _, code = run_ps_script("Write-Output (Get-MpComputerStatus).IsTamperProtected")
    if code != 0:
        return None
    return out.strip().lower() == "true"


def get_realtime_status():
    """Check if Windows Defender real-time protection is enabled."""
    out, _, code = run_ps_script("Write-Output (Get-MpPreference).DisableRealtimeMonitoring")
    if code != 0:
        return None
    return out.strip().lower() != "true"


def get_cloud_status():
    """Check cloud protection and submission settings."""
    script = (
        "$p = Get-MpPreference\n"
        "Write-Output \"MAPS=$($p.MAPSReporting)\"\n"
        "Write-Output \"SUBMIT=$($p.SubmitSamplesConsent)\"\n"
        "Write-Output \"BLOCK_FIRST=$($p.DisableBlockAtFirstSeen)\"\n"
        "Write-Output \"IOAV=$($p.DisableIOAVProtection)\"\n"
        "Write-Output \"PRIVACY=$($p.DisablePrivacyMode)\"\n"
    )
    out, _, code = run_ps_script(script)
    if code != 0:
        return {}
    result = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            result[k.strip()] = v.strip()
    return result


def get_current_exclusion_paths():
    """Get the list of current Defender exclusion paths."""
    out, _, code = run_ps_script("Write-Output ((Get-MpPreference).ExclusionPath -join '|')")
    if code != 0:
        return []
    return [p.strip() for p in out.split("|") if p.strip()]


def get_current_exclusion_processes():
    """Get the list of current Defender exclusion processes."""
    out, _, code = run_ps_script("Write-Output ((Get-MpPreference).ExclusionProcess -join '|')")
    if code != 0:
        return []
    return [p.strip() for p in out.split("|") if p.strip()]


# ─── Actions ─────────────────────────────────────────────────────────────────

class DefenderManager:
    """Manages Windows Defender settings via PowerShell."""

    def __init__(self):
        self.config = load_config()
        self.icon = None
        self._lock = threading.Lock()

    def _update_icon(self):
        """Update the tray icon based on current state."""
        if self.icon is None:
            return
        try:
            rt_on = get_realtime_status()
            if rt_on is None:
                self.icon.icon = create_icon("gray")
            elif not rt_on:
                self.icon.icon = create_icon("red")
            else:
                current_paths = get_current_exclusion_paths()
                config_paths = [expand_path(p) for p in self.config.get("exclusion_folders", [])]
                has_exclusions = any(
                    cp.lower() in [x.lower() for x in current_paths]
                    for cp in config_paths
                )
                self.icon.icon = create_icon("orange" if has_exclusions else "green")
        except Exception:
            self.icon.icon = create_icon("gray")

    def _check_tamper_and_warn(self, icon):
        """Check Tamper Protection and warn if blocking. Returns True if tamper is ON."""
        tamper = is_tamper_protected()
        if tamper:
            msgbox(
                f"{APP_NAME} - Tamper Protection is ON",
                "Windows Tamper Protection is blocking this change.\n\n"
                "To fix this, you must MANUALLY turn it off:\n\n"
                "1. Click OK — Windows Security will open\n"
                "2. Go to: Virus & threat protection\n"
                "3. Click: Manage settings\n"
                "4. Scroll down and turn OFF: Tamper Protection\n"
                "5. Then try this action again in DevShield\n\n"
                "Note: Only YOU can disable Tamper Protection — "
                "no program can do it automatically (by design).",
                0x30
            )
            try:
                os.startfile("windowsdefender://threatsettings")
            except Exception:
                os.startfile("windowsdefender:")
            return True
        return False

    # ── Real-time Protection ──

    def toggle_realtime(self, icon, item):
        """Toggle Windows Defender real-time protection."""
        def _do():
            with self._lock:
                rt_on = get_realtime_status()
                if rt_on is None:
                    notify(icon, APP_NAME, "Could not read Defender status.")
                    return

                if rt_on:
                    if self._check_tamper_and_warn(icon):
                        return
                    _, stderr, code = run_ps_script(
                        "Set-MpPreference -DisableRealtimeMonitoring $true"
                    )
                    rt_after = get_realtime_status()
                    if rt_after is not None and not rt_after:
                        notify(icon, APP_NAME,
                               "Real-time protection DISABLED.\n"
                               "Remember to re-enable after development.")
                    else:
                        msgbox(f"{APP_NAME} - Failed",
                               f"Could not disable real-time protection.\n\n"
                               f"Tamper Protection may still be ON.\n"
                               f"Please disable it manually in Windows Security.\n\n"
                               f"Error: {stderr[:200] if stderr else 'Unknown'}",
                               0x10)
                else:
                    run_ps_script("Set-MpPreference -DisableRealtimeMonitoring $false")
                    rt_after = get_realtime_status()
                    if rt_after:
                        notify(icon, APP_NAME, "Real-time protection ENABLED.")
                    else:
                        notify(icon, APP_NAME, "Failed to enable real-time protection.")
                self._update_icon()
        threading.Thread(target=_do, daemon=True).start()

    # ── Cloud / Submission / Telemetry ──

    def disable_cloud_features(self, icon, item):
        """Disable cloud protection, sample submission, block-at-first-seen."""
        def _do():
            with self._lock:
                if self._check_tamper_and_warn(icon):
                    return
                script = (
                    "# Disable cloud-delivered protection (MAPS)\n"
                    "Set-MpPreference -MAPSReporting Disabled\n"
                    "\n"
                    "# Never send samples automatically\n"
                    "Set-MpPreference -SubmitSamplesConsent 2\n"
                    "\n"
                    "# Disable Block at First Seen\n"
                    "Set-MpPreference -DisableBlockAtFirstSeen $true\n"
                    "\n"
                    "# Disable IOAV protection (scans downloaded files/attachments)\n"
                    "Set-MpPreference -DisableIOAVProtection $true\n"
                    "\n"
                    "Write-Output 'Cloud features disabled'\n"
                )
                out, stderr, code = run_ps_script(script)
                if "disabled" in out.lower():
                    notify(icon, APP_NAME,
                           "Cloud features DISABLED:\n"
                           "- Cloud protection (MAPS)\n"
                           "- Sample submission\n"
                           "- Block at First Seen\n"
                           "- Download scanning (IOAV)")
                else:
                    notify(icon, APP_NAME,
                           f"Some cloud settings may have failed.\n{stderr[:150] if stderr else ''}")
        threading.Thread(target=_do, daemon=True).start()

    def enable_cloud_features(self, icon, item):
        """Re-enable cloud protection, sample submission, block-at-first-seen."""
        def _do():
            with self._lock:
                script = (
                    "Set-MpPreference -MAPSReporting Advanced\n"
                    "Set-MpPreference -SubmitSamplesConsent 1\n"
                    "Set-MpPreference -DisableBlockAtFirstSeen $false\n"
                    "Set-MpPreference -DisableIOAVProtection $false\n"
                    "Write-Output 'Cloud features enabled'\n"
                )
                out, stderr, code = run_ps_script(script)
                if "enabled" in out.lower():
                    notify(icon, APP_NAME, "Cloud features restored to defaults.")
                else:
                    notify(icon, APP_NAME, f"Some settings may have failed.\n{stderr[:150]}")
        threading.Thread(target=_do, daemon=True).start()

    # ── Dev Mode: Disable Everything At Once ──

    def dev_mode_on(self, icon, item):
        """One-click: disable RT, cloud, submissions + add exclusions."""
        def _do():
            with self._lock:
                if self._check_tamper_and_warn(icon):
                    return

                config = load_config()
                lines = [
                    "# === DevShield: DEV MODE ON ===",
                    "",
                    "# Disable Real-time Protection",
                    "Set-MpPreference -DisableRealtimeMonitoring $true",
                    "",
                    "# Disable Cloud / Submissions",
                    "Set-MpPreference -MAPSReporting Disabled",
                    "Set-MpPreference -SubmitSamplesConsent 2",
                    "Set-MpPreference -DisableBlockAtFirstSeen $true",
                    "Set-MpPreference -DisableIOAVProtection $true",
                    "",
                    "# Add Dev Exclusions",
                ]
                for folder in config.get("exclusion_folders", []):
                    expanded = expand_path(folder)
                    lines.append(f'Add-MpPreference -ExclusionPath "{expanded}" -ErrorAction SilentlyContinue')
                for proc in config.get("exclusion_processes", []):
                    lines.append(f'Add-MpPreference -ExclusionProcess "{proc}" -ErrorAction SilentlyContinue')

                lines.append("")
                lines.append("Write-Output 'DEV_MODE_ON'")

                out, stderr, code = run_ps_script("\n".join(lines))
                rt_after = get_realtime_status()

                if rt_after is not None and not rt_after:
                    notify(icon, APP_NAME,
                           "DEV MODE ON\n"
                           "- Real-time protection: OFF\n"
                           "- Cloud/submissions: OFF\n"
                           "- Dev exclusions: Added")
                else:
                    msgbox(f"{APP_NAME}",
                           f"Dev Mode partially applied.\n"
                           f"Real-time protection may still be on.\n"
                           f"Check Tamper Protection.\n\n{stderr[:200] if stderr else ''}",
                           0x30)
                self._update_icon()
        threading.Thread(target=_do, daemon=True).start()

    def dev_mode_off(self, icon, item):
        """One-click: re-enable RT, cloud, submissions + remove exclusions."""
        def _do():
            with self._lock:
                config = load_config()
                lines = [
                    "# === DevShield: DEV MODE OFF ===",
                    "",
                    "# Enable Real-time Protection",
                    "Set-MpPreference -DisableRealtimeMonitoring $false",
                    "",
                    "# Enable Cloud / Submissions",
                    "Set-MpPreference -MAPSReporting Advanced",
                    "Set-MpPreference -SubmitSamplesConsent 1",
                    "Set-MpPreference -DisableBlockAtFirstSeen $false",
                    "Set-MpPreference -DisableIOAVProtection $false",
                    "",
                    "# Remove Dev Exclusions",
                ]
                for folder in config.get("exclusion_folders", []):
                    expanded = expand_path(folder)
                    lines.append(f'Remove-MpPreference -ExclusionPath "{expanded}" -ErrorAction SilentlyContinue')
                for proc in config.get("exclusion_processes", []):
                    lines.append(f'Remove-MpPreference -ExclusionProcess "{proc}" -ErrorAction SilentlyContinue')

                lines.append("")
                lines.append("Write-Output 'DEV_MODE_OFF'")

                run_ps_script("\n".join(lines))
                notify(icon, APP_NAME,
                       "DEV MODE OFF\n"
                       "- Real-time protection: ON\n"
                       "- Cloud/submissions: ON\n"
                       "- Dev exclusions: Removed")
                self._update_icon()
        threading.Thread(target=_do, daemon=True).start()

    # ── Exclusions ──

    def add_dev_exclusions(self, icon, item):
        """Add all configured developer exclusions to Defender."""
        def _do():
            with self._lock:
                config = load_config()
                lines = []
                folders = config.get("exclusion_folders", [])
                processes = config.get("exclusion_processes", [])

                for folder in folders:
                    expanded = expand_path(folder)
                    lines.append(f'Add-MpPreference -ExclusionPath "{expanded}" -ErrorAction SilentlyContinue')
                for proc in processes:
                    lines.append(f'Add-MpPreference -ExclusionProcess "{proc}" -ErrorAction SilentlyContinue')
                lines.append(f'Write-Output "Done"')

                run_ps_script("\n".join(lines))
                notify(icon, APP_NAME,
                       f"Added {len(folders)} folder(s) and {len(processes)} process(es) to exclusions.")
                self._update_icon()
        threading.Thread(target=_do, daemon=True).start()

    def remove_dev_exclusions(self, icon, item):
        """Remove all configured developer exclusions from Defender."""
        def _do():
            with self._lock:
                config = load_config()
                lines = []
                for folder in config.get("exclusion_folders", []):
                    expanded = expand_path(folder)
                    lines.append(f'Remove-MpPreference -ExclusionPath "{expanded}" -ErrorAction SilentlyContinue')
                for proc in config.get("exclusion_processes", []):
                    lines.append(f'Remove-MpPreference -ExclusionProcess "{proc}" -ErrorAction SilentlyContinue')
                lines.append('Write-Output "Done"')

                run_ps_script("\n".join(lines))
                notify(icon, APP_NAME, "Removed dev exclusions. Full scanning restored.")
                self._update_icon()
        threading.Thread(target=_do, daemon=True).start()

    # ── Startup ──

    def toggle_startup(self, icon, item):
        """Toggle auto-start on Windows login."""
        if is_startup_enabled():
            if disable_startup():
                notify(icon, APP_NAME, "Removed from Windows startup.")
            else:
                notify(icon, APP_NAME, "Failed to remove from startup.")
        else:
            if enable_startup():
                notify(icon, APP_NAME, "Added to Windows startup.\nDevShield will start automatically on login.")
            else:
                notify(icon, APP_NAME, "Failed to add to startup.")

    # ── Status ──

    def show_status(self, icon, item):
        """Show current Defender status in a popup."""
        def _do():
            rt_on = get_realtime_status()
            tamper = is_tamper_protected()
            cloud = get_cloud_status()
            paths = get_current_exclusion_paths()
            procs = get_current_exclusion_processes()
            startup = is_startup_enabled()

            rt_str = "ON" if rt_on else ("OFF" if rt_on is not None else "Unknown")
            tamper_str = "ON (blocks changes)" if tamper else ("OFF" if tamper is not None else "Unknown")

            maps_val = cloud.get("MAPS", "?")
            maps_str = "OFF" if maps_val == "0" else f"ON ({maps_val})"
            submit_val = cloud.get("SUBMIT", "?")
            submit_map = {"0": "Default", "1": "Always", "2": "Never", "3": "Auto"}
            submit_str = submit_map.get(submit_val, submit_val)

            msg = (
                f"=== DevShield Status ===\n\n"
                f"Real-time Protection: {rt_str}\n"
                f"Tamper Protection: {tamper_str}\n"
                f"Cloud Protection (MAPS): {maps_str}\n"
                f"Sample Submission: {submit_str}\n"
                f"Block at First Seen: {'OFF' if cloud.get('BLOCK_FIRST', '').lower() == 'true' else 'ON'}\n"
                f"\n"
                f"Excluded Folders: {len(paths)}\n"
                f"Excluded Processes: {len(procs)}\n"
                f"Auto-start on login: {'YES' if startup else 'NO'}\n"
            )

            if paths:
                msg += "\n--- Excluded Folders ---\n"
                for p in paths[:8]:
                    msg += f"  {p}\n"
                if len(paths) > 8:
                    msg += f"  ... and {len(paths) - 8} more\n"

            msgbox(f"{APP_NAME} - Status", msg, 0x40)
        threading.Thread(target=_do, daemon=True).start()

    # ── Settings Pages ──

    def open_tamper_settings(self, icon, item):
        """Open Windows Security Tamper Protection settings."""
        try:
            os.startfile("windowsdefender://threatsettings")
        except Exception:
            os.startfile("windowsdefender:")

    def open_defender_settings(self, icon, item):
        """Open Windows Security settings."""
        os.startfile("windowsdefender:")

    def open_config(self, icon, item):
        """Open the config.json file in the default editor."""
        os.startfile(CONFIG_FILE)

    def quit_app(self, icon, item):
        """Quit the application."""
        icon.stop()

    # ── Dynamic Menu Text ──

    def get_rt_status_text(self, item):
        rt_on = get_realtime_status()
        if rt_on is None:
            return "Toggle Real-time Protection (Unknown)"
        return f"{'Disable' if rt_on else 'Enable'} Real-time Protection"

    def get_startup_text(self, item):
        enabled = is_startup_enabled()
        return f"{'Remove from' if enabled else 'Add to'} Windows Startup"

    def get_startup_checked(self, item):
        return is_startup_enabled()

    # ── Menu ──

    def build_menu(self):
        """Build the system tray context menu."""
        return pystray.Menu(
            pystray.MenuItem("Show Status", self.show_status, default=True),
            pystray.Menu.SEPARATOR,

            # ── Quick Dev Mode ──
            pystray.MenuItem(
                "Dev Mode",
                pystray.Menu(
                    pystray.MenuItem("DEV MODE ON  (disable all, add exclusions)", self.dev_mode_on),
                    pystray.MenuItem("DEV MODE OFF (restore all protections)", self.dev_mode_off),
                )
            ),
            pystray.Menu.SEPARATOR,

            # ── Individual Controls ──
            pystray.MenuItem(
                self.get_rt_status_text,
                self.toggle_realtime
            ),
            pystray.MenuItem(
                "Cloud & Submissions",
                pystray.Menu(
                    pystray.MenuItem("Disable Cloud + Submissions", self.disable_cloud_features),
                    pystray.MenuItem("Enable Cloud + Submissions", self.enable_cloud_features),
                )
            ),
            pystray.MenuItem(
                "Dev Exclusions",
                pystray.Menu(
                    pystray.MenuItem("Add Dev Exclusions", self.add_dev_exclusions),
                    pystray.MenuItem("Remove Dev Exclusions", self.remove_dev_exclusions),
                )
            ),
            pystray.Menu.SEPARATOR,

            # ── Settings ──
            pystray.MenuItem(
                self.get_startup_text,
                self.toggle_startup,
                checked=self.get_startup_checked
            ),
            pystray.MenuItem("Edit Config (config.json)", self.open_config),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open Tamper Protection Settings", self.open_tamper_settings),
            pystray.MenuItem("Open Windows Security", self.open_defender_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit DevShield", self.quit_app),
        )

    def run(self):
        """Start the system tray application."""
        self.icon = pystray.Icon(
            APP_NAME,
            create_icon("green"),
            f"{APP_NAME} - Defender Manager",
            menu=self.build_menu()
        )

        # Update icon on startup in background
        def _init_icon():
            import time
            time.sleep(1)
            self._update_icon()
        threading.Thread(target=_init_icon, daemon=True).start()

        self.icon.run()


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    # Hide the console window immediately
    hide_console()

    # Check for admin privileges
    if not is_admin():
        run_as_admin()
        return

    manager = DefenderManager()
    manager.run()


if __name__ == "__main__":
    main()
