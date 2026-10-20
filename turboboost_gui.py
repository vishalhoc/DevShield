"""
TurboBoost Modern GUI
Built with CustomTkinter for sleek dark-themed Windows 11 aesthetics.
Features real-time system monitoring, 1-click boost/restore, profile manager,
services selector, system tweaks, and background app killer.
"""

import ctypes
import os
import sys
import threading
import time
from typing import Dict, List, Any, Optional

import customtkinter as ctk

try:
    import psutil
except ImportError:
    psutil = None

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    pystray = None

import turboboost_engine as engine

# ─── Appearance Setup ────────────────────────────────────────────────────────
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

APP_NAME = "TurboBoost"
APP_SUBTITLE = "Windows Game & Development Optimizer"
VERSION = "v1.0.0"


class TurboBoostGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.engine = engine.TurboBoostEngine()
        self.service_checkboxes: Dict[str, ctk.CTkCheckBox] = {}
        self.tweak_switches: Dict[str, ctk.CTkSwitch] = {}
        self.app_checkboxes: Dict[str, ctk.CTkCheckBox] = {}
        self.service_status_labels: Dict[str, ctk.CTkLabel] = {}
        
        self.tray_icon = None
        self.monitoring_active = True

        # Window setup
        self.title(f"{APP_NAME} {VERSION} — {APP_SUBTITLE}")
        self.geometry("1020x740")
        self.minsize(960, 680)

        # Main Layout
        self.create_header()
        self.create_action_bar()
        self.create_tabview()
        self.create_footer()

        # Load initial active profile into controls
        self.current_profile_name = "Extreme Game Mode"
        self.apply_profile_to_ui(self.current_profile_name)

        # Start live monitoring thread
        self.monitor_thread = threading.Thread(target=self.realtime_metrics_loop, daemon=True)
        self.monitor_thread.start()

        # Handle close event (minimize to tray or quit)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ─── Header & Live Metrics ───────────────────────────────────────────────

    def create_header(self):
        header_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#181a20")
        header_frame.pack(fill="x", padx=16, pady=(12, 6))

        # Title & Subtitle
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=10)

        title_lbl = ctk.CTkLabel(
            title_box,
            text=f"⚡ {APP_NAME.upper()}",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#00E5FF"
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = ctk.CTkLabel(
            title_box,
            text=APP_SUBTITLE,
            font=ctk.CTkFont(size=12),
            text_color="#8F9CAE"
        )
        subtitle_lbl.pack(anchor="w")

        # Live Metrics Cards (Right Side)
        metrics_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        metrics_box.pack(side="right", padx=16, pady=6)

        # CPU Metric Card
        self.cpu_card = ctk.CTkFrame(metrics_box, fg_color="#222630", corner_radius=8, width=120)
        self.cpu_card.pack(side="left", padx=6, pady=4)
        ctk.CTkLabel(self.cpu_card, text="CPU USAGE", font=ctk.CTkFont(size=10, weight="bold"), text_color="#7A889B").pack(pady=(4, 0))
        self.cpu_val_lbl = ctk.CTkLabel(self.cpu_card, text="0%", font=ctk.CTkFont(size=15, weight="bold"), text_color="#FFFFFF")
        self.cpu_val_lbl.pack(pady=(0, 2))
        self.cpu_bar = ctk.CTkProgressBar(self.cpu_card, width=90, height=6, progress_color="#00E5FF")
        self.cpu_bar.set(0.0)
        self.cpu_bar.pack(pady=(0, 6))

        # RAM Metric Card
        self.ram_card = ctk.CTkFrame(metrics_box, fg_color="#222630", corner_radius=8, width=140)
        self.ram_card.pack(side="left", padx=6, pady=4)
        ctk.CTkLabel(self.ram_card, text="RAM USAGE", font=ctk.CTkFont(size=10, weight="bold"), text_color="#7A889B").pack(pady=(4, 0))
        self.ram_val_lbl = ctk.CTkLabel(self.ram_card, text="0% (0/0 GB)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#FFFFFF")
        self.ram_val_lbl.pack(pady=(0, 2))
        self.ram_bar = ctk.CTkProgressBar(self.ram_card, width=110, height=6, progress_color="#00E676")
        self.ram_bar.set(0.0)
        self.ram_bar.pack(pady=(0, 6))

        # Mode Badge
        self.mode_badge = ctk.CTkLabel(
            metrics_box,
            text="NORMAL MODE",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2A2F3D",
            text_color="#A0AAB8",
            corner_radius=8,
            padx=14,
            pady=8
        )
        self.mode_badge.pack(side="left", padx=(10, 0))

    # ─── Master 1-Click Action Bar ───────────────────────────────────────────

    def create_action_bar(self):
        action_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#181a20")
        action_frame.pack(fill="x", padx=16, pady=6)

        # Profile Selector
        left_box = ctk.CTkFrame(action_frame, fg_color="transparent")
        left_box.pack(side="left", padx=16, pady=10)

        ctk.CTkLabel(
            left_box,
            text="ACTIVE PROFILE:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#8F9CAE"
        ).pack(anchor="w", pady=(0, 2))

        self.profile_names = list(self.engine.profiles.keys())
        self.profile_combo = ctk.CTkComboBox(
            left_box,
            values=self.profile_names,
            width=230,
            command=self.on_profile_selected,
            font=ctk.CTkFont(size=13, weight="bold"),
            dropdown_font=ctk.CTkFont(size=12)
        )
        self.profile_combo.set(self.current_profile_name)
        self.profile_combo.pack(anchor="w")

        # Huge 1-Click Master Action Button
        self.master_btn = ctk.CTkButton(
            action_frame,
            text="⚡ ACTIVATE BOOST (1-CLICK)",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#00C853",
            hover_color="#00B248",
            text_color="#FFFFFF",
            height=46,
            corner_radius=8,
            command=self.on_master_toggle_click
        )
        self.master_btn.pack(side="left", fill="x", expand=True, padx=20, pady=10)

        # Quick RAM Cleaner Button
        self.ram_clean_btn = ctk.CTkButton(
            action_frame,
            text="🧹 Clean RAM Now",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#303846",
            hover_color="#3F495A",
            height=46,
            width=160,
            corner_radius=8,
            command=self.on_clean_ram_click
        )
        self.ram_clean_btn.pack(side="right", padx=16, pady=10)

        # Update initial state of button based on snapshot
        self.refresh_boost_status_ui()

    # ─── Tabview (5 Sections) ────────────────────────────────────────────────

    def create_tabview(self):
        self.tabview = ctk.CTkTabview(self, corner_radius=10, fg_color="#181a20")
        self.tabview.pack(fill="both", expand=True, padx=16, pady=6)

        self.tab_dashboard = self.tabview.add("📊 Dashboard")
        self.tab_services = self.tabview.add("⚙️ Windows Services")
        self.tab_tweaks = self.tabview.add("🚀 System Tweaks")
        self.tab_apps = self.tabview.add("🛑 Background Apps")
        self.tab_profiles = self.tabview.add("💾 Profiles & Restore")

        self.setup_tab_dashboard()
        self.setup_tab_services()
        self.setup_tab_tweaks()
        self.setup_tab_apps()
        self.setup_tab_profiles()

    # ── Tab 1: Dashboard ──

    def setup_tab_dashboard(self):
        parent = self.tab_dashboard

        # Two Column Layout
        cols = ctk.CTkFrame(parent, fg_color="transparent")
        cols.pack(fill="both", expand=True, padx=10, pady=10)

        # Left Column: Profile Summary & Quick Stats
        left_col = ctk.CTkFrame(cols, fg_color="#1E222B", corner_radius=8)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=0)

        ctk.CTkLabel(
            left_col,
            text="ACTIVE PROFILE SUMMARY",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#00E5FF"
        ).pack(anchor="w", padx=14, pady=(12, 4))

        self.dash_profile_title = ctk.CTkLabel(
            left_col,
            text="Extreme Game Mode",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#FFFFFF"
        )
        self.dash_profile_title.pack(anchor="w", padx=14, pady=(0, 2))

        self.dash_profile_desc = ctk.CTkLabel(
            left_col,
            text="Maximum FPS, ultra-low input latency. Stops Search, SysMain, Spooler, Updates, Telemetry.",
            font=ctk.CTkFont(size=12),
            text_color="#9AA6B8",
            wraplength=380,
            justify="left"
        )
        self.dash_profile_desc.pack(anchor="w", padx=14, pady=(0, 10))

        # Quick Stats List
        stats_box = ctk.CTkFrame(left_col, fg_color="#15171E", corner_radius=6)
        stats_box.pack(fill="x", padx=14, pady=6)

        self.dash_stat_services = ctk.CTkLabel(stats_box, text="• Services Configured to Stop: 17", font=ctk.CTkFont(size=12), text_color="#E0E6ED")
        self.dash_stat_services.pack(anchor="w", padx=12, pady=(8, 2))

        self.dash_stat_tweaks = ctk.CTkLabel(stats_box, text="• Active Tweaks: High Perf Power, Game Mode, Network Unthrottle, RAM Trim", font=ctk.CTkFont(size=12), text_color="#E0E6ED")
        self.dash_stat_tweaks.pack(anchor="w", padx=12, pady=2)

        self.dash_stat_apps = ctk.CTkLabel(stats_box, text="• Background Apps to Terminate: 6", font=ctk.CTkFont(size=12), text_color="#E0E6ED")
        self.dash_stat_apps.pack(anchor="w", padx=12, pady=(2, 8))

        # Quick Actions Row
        quick_row = ctk.CTkFrame(left_col, fg_color="transparent")
        quick_row.pack(fill="x", padx=14, pady=10)

        ctk.CTkButton(
            quick_row,
            text="Flush DNS Cache",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2E3846",
            hover_color="#3D4B5C",
            command=self.on_flush_dns_click
        ).pack(side="left", padx=(0, 6), expand=True, fill="x")

        ctk.CTkButton(
            quick_row,
            text="Refresh Services Status",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2E3846",
            hover_color="#3D4B5C",
            command=self.refresh_services_status_ui
        ).pack(side="left", padx=(6, 0), expand=True, fill="x")

        # Right Column: Live Status & Activity Log
        right_col = ctk.CTkFrame(cols, fg_color="#1E222B", corner_radius=8)
        right_col.pack(side="right", fill="both", expand=True, padx=(6, 0), pady=0)

        ctk.CTkLabel(
            right_col,
            text="ACTIVITY & SNAPSHOT LOG",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#00E5FF"
        ).pack(anchor="w", padx=14, pady=(12, 6))

        self.log_textbox = ctk.CTkTextbox(
            right_col,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#121419",
            text_color="#00E676"
        )
        self.log_textbox.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.log("TurboBoost Engine initialized.")
        self.log("System ready. Select a profile or click ACTIVATE BOOST.")

    # ── Tab 2: Windows Services ──

    def setup_tab_services(self):
        parent = self.tab_services

        # Controls bar at top of services tab
        ctrl_bar = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl_bar.pack(fill="x", padx=10, pady=(8, 6))

        ctk.CTkLabel(
            ctrl_bar,
            text="SELECT SERVICES TO STOP DURING BOOST:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#8F9CAE"
        ).pack(side="left")

        ctk.CTkButton(
            ctrl_bar,
            text="Select All Safe",
            width=110,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#2E3846",
            hover_color="#3D4B5C",
            command=self.select_all_safe_services
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            ctrl_bar,
            text="Deselect All",
            width=90,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#2E3846",
            hover_color="#3D4B5C",
            command=self.deselect_all_services
        ).pack(side="right", padx=4)

        # Scrollable Frame for 22+ Services
        self.services_scroll = ctk.CTkScrollableFrame(parent, fg_color="#1E222B", corner_radius=8)
        self.services_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Populate Service Cards
        for svc in engine.SERVICES_DB:
            card = ctk.CTkFrame(self.services_scroll, fg_color="#171920", corner_radius=6)
            card.pack(fill="x", padx=6, pady=4)

            # Left side: Checkbox + Name
            chk = ctk.CTkCheckBox(
                card,
                text=f"{svc['name']}  ({svc['id']})",
                font=ctk.CTkFont(size=13, weight="bold"),
                checkbox_width=20,
                checkbox_height=20,
                corner_radius=4
            )
            chk.pack(side="left", padx=12, pady=10)
            self.service_checkboxes[svc["id"]] = chk

            # Middle/Right: Category badge + Safety Badge
            badge_box = ctk.CTkFrame(card, fg_color="transparent")
            badge_box.pack(side="right", padx=12, pady=10)

            # Live Status Pill
            status_lbl = ctk.CTkLabel(
                badge_box,
                text="● Querying...",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#8F9CAE",
                fg_color="#222630",
                corner_radius=6,
                padx=8,
                pady=2
            )
            status_lbl.pack(side="right", padx=4)
            self.service_status_labels[svc["id"]] = status_lbl

            # Safety Level Pill
            is_safe = svc["safe_level"] == "Safe"
            safety_lbl = ctk.CTkLabel(
                badge_box,
                text=svc["safe_level"],
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#00E676" if is_safe else "#FFB300",
                fg_color="#182A20" if is_safe else "#2B2412",
                corner_radius=6,
                padx=8,
                pady=2
            )
            safety_lbl.pack(side="right", padx=4)

            # Description (sub-row in card)
            desc_lbl = ctk.CTkLabel(
                card,
                text=f"[{svc['category']}] {svc['description']}",
                font=ctk.CTkFont(size=11),
                text_color="#7A889B",
                wraplength=480,
                justify="left"
            )
            desc_lbl.pack(side="left", padx=10, pady=(2, 6), anchor="w")

    # ── Tab 3: System & Network Tweaks ──

    def setup_tab_tweaks(self):
        parent = self.tab_tweaks

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        tweaks_list = [
            {
                "key": "power_plan",
                "title": "⚡ High / Ultimate Performance Power Scheme",
                "desc": "Forces Windows power policy to 100% CPU clock speed with zero core sleep latency. Prevents micro-stutters during heavy compiles or high-refresh-rate gaming."
            },
            {
                "key": "clean_ram",
                "title": "🧠 Purge Memory Working Sets & Standby Cache",
                "desc": "Flushes dirty pages, background working sets, and standby memory via Windows EmptyWorkingSet API. Immediately frees up gigabytes of RAM for your game or compiler."
            },
            {
                "key": "game_mode",
                "title": "🎮 Enable Windows Game Mode",
                "desc": "Signals Windows thread scheduler to prioritize the foreground window and pause background driver interrupts and updates."
            },
            {
                "key": "network_throttling",
                "title": "🌐 Disable Network Packet Throttling",
                "desc": "Sets NetworkThrottlingIndex to 0xffffffff in registry. Disables Windows built-in network packet throttling mechanism, delivering lowest ping and maximum network throughput."
            },
            {
                "key": "system_responsiveness",
                "title": "🏎️ Maximize System Responsiveness Priority",
                "desc": "Sets SystemResponsiveness to 0 in Multimedia SystemProfile. Dedicates 100% CPU priority to foreground applications instead of reserving 20% for background OS tasks."
            },
            {
                "key": "flush_dns",
                "title": "🧹 Automatic DNS Cache Flush",
                "desc": "Cleans the DNS resolver cache upon boost activation to ensure direct routing to game and dev package servers."
            }
        ]

        for tweak in tweaks_list:
            card = ctk.CTkFrame(scroll, fg_color="#1E222B", corner_radius=8)
            card.pack(fill="x", pady=6)

            left = ctk.CTkFrame(card, fg_color="transparent")
            left.pack(side="left", fill="both", expand=True, padx=14, pady=12)

            ctk.CTkLabel(
                left,
                text=tweak["title"],
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#FFFFFF"
            ).pack(anchor="w")

            ctk.CTkLabel(
                left,
                text=tweak["desc"],
                font=ctk.CTkFont(size=12),
                text_color="#8F9CAE",
                wraplength=600,
                justify="left"
            ).pack(anchor="w", pady=(4, 0))

            switch = ctk.CTkSwitch(
                card,
                text="",
                width=45,
                progress_color="#00E5FF"
            )
            switch.pack(side="right", padx=16)
            self.tweak_switches[tweak["key"]] = switch

    # ── Tab 4: Background Apps ──

    def setup_tab_apps(self):
        parent = self.tab_apps

        top_bar = ctk.CTkFrame(parent, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=(8, 6))

        ctk.CTkLabel(
            top_bar,
            text="TERMINATE RESOURCE-HEAVY BACKGROUND APPS ON BOOST:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#8F9CAE"
        ).pack(side="left")

        ctk.CTkButton(
            top_bar,
            text="🔄 Refresh Process List",
            width=160,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#2E3846",
            hover_color="#3D4B5C",
            command=self.refresh_apps_list_ui
        ).pack(side="right")

        self.apps_scroll = ctk.CTkScrollableFrame(parent, fg_color="#1E222B", corner_radius=8)
        self.apps_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.refresh_apps_list_ui()

    def refresh_apps_list_ui(self):
        # Clear existing
        for widget in self.apps_scroll.winfo_children():
            widget.destroy()
        self.app_checkboxes.clear()

        scanned_apps = engine.scan_running_background_apps()
        for app in scanned_apps:
            card = ctk.CTkFrame(self.apps_scroll, fg_color="#171920", corner_radius=6)
            card.pack(fill="x", padx=6, pady=4)

            chk = ctk.CTkCheckBox(
                card,
                text=f"{app['display']}  ({app['name']})",
                font=ctk.CTkFont(size=13, weight="bold"),
                checkbox_width=20,
                checkbox_height=20,
                corner_radius=4
            )
            chk.pack(side="left", padx=12, pady=10)
            self.app_checkboxes[app["name"]] = chk

            # Status pill
            is_running = app["running"]
            status_lbl = ctk.CTkLabel(
                card,
                text="● Running" if is_running else "○ Not Running",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#00E676" if is_running else "#7A889B",
                fg_color="#182A20" if is_running else "#222630",
                corner_radius=6,
                padx=8,
                pady=2
            )
            status_lbl.pack(side="right", padx=12, pady=10)

            # Desc
            ctk.CTkLabel(
                card,
                text=app["desc"],
                font=ctk.CTkFont(size=11),
                text_color="#7A889B"
            ).pack(side="left", padx=10, pady=10)

        # Re-apply selected profile app checks
        current_cfg = self.engine.profiles.get(self.current_profile_name, {})
        for app_name, chk in self.app_checkboxes.items():
            if app_name in current_cfg.get("kill_background_apps", []):
                chk.select()
            else:
                chk.deselect()

    # ── Tab 5: Profiles & Restore ──

    def setup_tab_profiles(self):
        parent = self.tab_profiles

        cols = ctk.CTkFrame(parent, fg_color="transparent")
        cols.pack(fill="both", expand=True, padx=10, pady=10)

        # Left: Save Current Settings as Profile
        left_box = ctk.CTkFrame(cols, fg_color="#1E222B", corner_radius=8)
        left_box.pack(side="left", fill="both", expand=True, padx=(0, 6))

        ctk.CTkLabel(
            left_box,
            text="SAVE CURRENT SETUP AS A PROFILE",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#00E5FF"
        ).pack(anchor="w", padx=14, pady=(12, 6))

        ctk.CTkLabel(left_box, text="Profile Name:", font=ctk.CTkFont(size=12), text_color="#A0AAB8").pack(anchor="w", padx=14, pady=(4, 0))
        self.prof_name_entry = ctk.CTkEntry(left_box, placeholder_text="e.g. My Android Studio Sprint", width=340)
        self.prof_name_entry.pack(anchor="w", padx=14, pady=(2, 8))

        ctk.CTkLabel(left_box, text="Description:", font=ctk.CTkFont(size=12), text_color="#A0AAB8").pack(anchor="w", padx=14, pady=(4, 0))
        self.prof_desc_entry = ctk.CTkEntry(left_box, placeholder_text="e.g. Stops disk indexing, frees max RAM", width=340)
        self.prof_desc_entry.pack(anchor="w", padx=14, pady=(2, 12))

        ctk.CTkButton(
            left_box,
            text="💾 Save Profile Now",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#00C853",
            hover_color="#00B248",
            command=self.on_save_custom_profile_click
        ).pack(anchor="w", padx=14, pady=6)

        ctk.CTkLabel(
            left_box,
            text="Saving records all current checked services, tweaks, and background apps so you can re-apply them in 1-click anytime.",
            font=ctk.CTkFont(size=11),
            text_color="#7A889B",
            wraplength=340,
            justify="left"
        ).pack(anchor="w", padx=14, pady=(6, 12))

        # Right: Snapshot Recovery & Emergency Restore
        right_box = ctk.CTkFrame(cols, fg_color="#1E222B", corner_radius=8)
        right_box.pack(side="right", fill="both", expand=True, padx=(6, 0))

        ctk.CTkLabel(
            right_box,
            text="STATE RECOVERY & EMERGENCY RESTORE",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#00E5FF"
        ).pack(anchor="w", padx=14, pady=(12, 6))

        self.snapshot_info_lbl = ctk.CTkLabel(
            right_box,
            text="No active boost snapshot recorded.",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#9AA6B8",
            wraplength=360,
            justify="left"
        )
        self.snapshot_info_lbl.pack(anchor="w", padx=14, pady=8)

        ctk.CTkButton(
            right_box,
            text="🟢 1-Click Restore to Normal",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2979FF",
            hover_color="#2264D1",
            command=self.on_restore_click
        ).pack(anchor="w", padx=14, pady=6)

        ctk.CTkButton(
            right_box,
            text="⚠️ Emergency Restore (Restart All Services)",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#D50000",
            hover_color="#B70000",
            command=self.on_emergency_restore_click
        ).pack(anchor="w", padx=14, pady=(10, 6))

        self.refresh_snapshot_info_ui()

    # ─── Footer ──────────────────────────────────────────────────────────────

    def create_footer(self):
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            footer,
            text="TurboBoost // Built for Developers & Gamers. Clean 1-Click Snapshot & Restore.",
            font=ctk.CTkFont(size=11),
            text_color="#556070"
        ).pack(side="left")

        ctk.CTkButton(
            footer,
            text="Minimize to Tray",
            width=120,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#222630",
            hover_color="#2D3340",
            command=self.minimize_to_tray
        ).pack(side="right")

    # ─── Live Monitoring Loop ────────────────────────────────────────────────

    def realtime_metrics_loop(self):
        """Background thread updating CPU and RAM gauges every 1.5 seconds."""
        while self.monitoring_active:
            try:
                if psutil:
                    cpu = psutil.cpu_percent(interval=None)
                    vmem = psutil.virtual_memory()
                    ram_pct = vmem.percent
                    used_gb = round(vmem.used / (1024 ** 3), 1)
                    total_gb = round(vmem.total / (1024 ** 3), 1)

                    # Update UI on main thread safely
                    self.after(0, self._update_metrics_ui, cpu, ram_pct, used_gb, total_gb)
            except Exception:
                pass
            time.sleep(1.5)

    def _update_metrics_ui(self, cpu: float, ram_pct: float, used_gb: float, total_gb: float):
        try:
            self.cpu_val_lbl.configure(text=f"{int(cpu)}%")
            self.cpu_bar.set(cpu / 100.0)

            self.ram_val_lbl.configure(text=f"{int(ram_pct)}% ({used_gb}/{total_gb} GB)")
            self.ram_bar.set(ram_pct / 100.0)
        except Exception:
            pass

    # ─── Profile & UI Sync ───────────────────────────────────────────────────

    def apply_profile_to_ui(self, profile_name: str):
        self.current_profile_name = profile_name
        cfg = self.engine.profiles.get(profile_name, {})

        # Dashboard labels
        self.dash_profile_title.configure(text=profile_name)
        self.dash_profile_desc.configure(text=cfg.get("description", "Custom profile"))

        target_services = cfg.get("services", [])
        self.dash_stat_services.configure(text=f"• Services Configured to Stop: {len(target_services)}")

        # Check service checkboxes
        for sid, chk in self.service_checkboxes.items():
            if sid in target_services:
                chk.select()
            else:
                chk.deselect()

        # Check tweak switches
        tweaks = cfg.get("tweaks", {})
        for key, switch in self.tweak_switches.items():
            if tweaks.get(key, False):
                switch.select()
            else:
                switch.deselect()

        # Check background apps
        target_apps = cfg.get("kill_background_apps", [])
        self.dash_stat_apps.configure(text=f"• Background Apps to Terminate: {len(target_apps)}")
        for app_name, chk in self.app_checkboxes.items():
            if app_name in target_apps:
                chk.select()
            else:
                chk.deselect()

        # Update service live status pills asynchronously
        threading.Thread(target=self.refresh_services_status_ui, daemon=True).start()

    def on_profile_selected(self, choice: str):
        self.apply_profile_to_ui(choice)
        self.log(f"Profile loaded: [{choice}]")

    def select_all_safe_services(self):
        safe_ids = {s["id"] for s in engine.SERVICES_DB if s["safe_level"] == "Safe"}
        for sid, chk in self.service_checkboxes.items():
            if sid in safe_ids:
                chk.select()
        self.log("Selected all safe services.")

    def deselect_all_services(self):
        for chk in self.service_checkboxes.values():
            chk.deselect()
        self.log("Deselected all services.")

    def refresh_services_status_ui(self):
        """Batch query service statuses in background and update pills."""
        all_ids = [s["id"] for s in engine.SERVICES_DB]
        status_map = engine.get_all_services_status(all_ids)

        def update():
            for sid, status in status_map.items():
                lbl = self.service_status_labels.get(sid)
                if lbl:
                    is_run = status.lower() == "running"
                    lbl.configure(
                        text=f"● {status}",
                        text_color="#00E676" if is_run else "#7A889B",
                        fg_color="#182A20" if is_run else "#222630"
                    )
        self.after(0, update)

    def refresh_boost_status_ui(self):
        """Update master button, badge, and dashboard based on snapshot state."""
        is_boosted = self.engine.is_boosted()
        if is_boosted:
            self.mode_badge.configure(
                text="⚡ BOOST ACTIVE",
                fg_color="#00E676",
                text_color="#0D1117"
            )
            self.master_btn.configure(
                text="🟢 RESTORE NORMAL MODE (1-CLICK RESTORE)",
                fg_color="#2979FF",
                hover_color="#1C54B2"
            )
        else:
            self.mode_badge.configure(
                text="NORMAL MODE",
                fg_color="#2A2F3D",
                text_color="#A0AAB8"
            )
            self.master_btn.configure(
                text="⚡ ACTIVATE BOOST (1-CLICK)",
                fg_color="#00C853",
                hover_color="#00B248"
            )
        self.refresh_snapshot_info_ui()

    def refresh_snapshot_info_ui(self):
        snapshot = self.engine.snapshot
        if snapshot.get("is_boosted", False):
            info = (
                f"Status: ⚡ BOOSTED\n"
                f"Timestamp: {snapshot.get('timestamp')}\n"
                f"Profile Used: {snapshot.get('profile_name')}\n"
                f"Services Stopped: {len(snapshot.get('stopped_services', []))}\n"
                f"Processes Closed: {len(snapshot.get('killed_apps', []))}\n"
                f"Original Power Scheme: {snapshot.get('original_power_scheme', 'Default')}"
            )
            self.snapshot_info_lbl.configure(text=info, text_color="#00E5FF")
        else:
            self.snapshot_info_lbl.configure(
                text="System is in Normal Mode.\nNo active boost snapshot currently loaded.",
                text_color="#8F9CAE"
            )

    # ─── Actions Execution ───────────────────────────────────────────────────

    def get_current_ui_config(self) -> Dict[str, Any]:
        """Harvest current checked services, tweaks, and apps from UI."""
        services = [sid for sid, chk in self.service_checkboxes.items() if chk.get() == 1]
        tweaks = {k: bool(sw.get()) for k, sw in self.tweak_switches.items()}
        apps = [name for name, chk in self.app_checkboxes.items() if chk.get() == 1]
        return {
            "services": services,
            "tweaks": tweaks,
            "kill_background_apps": apps
        }

    def on_master_toggle_click(self):
        if self.engine.is_boosted():
            self.on_restore_click()
        else:
            self.on_boost_click()

    def on_boost_click(self):
        self.log("Starting 1-Click Boost sequence...")
        self.master_btn.configure(state="disabled", text="⏳ Applying Boost...")

        def _do():
            cfg = self.get_current_ui_config()
            res = self.engine.activate_boost(profile_name=self.current_profile_name, custom_config=cfg)

            def finish():
                self.master_btn.configure(state="normal")
                self.refresh_boost_status_ui()
                self.refresh_services_status_ui()
                self.refresh_apps_list_ui()

                self.log(f"✅ Boost Activated successfully!")
                self.log(f"   • Services stopped: {res['services_stopped_count']}")
                if res['services_stopped']:
                    self.log(f"     ({', '.join(res['services_stopped'])})")
                self.log(f"   • Background apps closed: {res['killed_apps_count']}")
                if res.get('ram_report'):
                    self.log(f"   • RAM freed: {res['ram_report'].get('memory_freed_mb', 0)} MB")
                if res.get('power_scheme'):
                    self.log(f"   • Power Scheme: High/Ultimate Performance Active")
            self.after(0, finish)

        threading.Thread(target=_do, daemon=True).start()

    def on_restore_click(self):
        self.log("Starting 1-Click Restore sequence...")
        self.master_btn.configure(state="disabled", text="⏳ Restoring Normal Mode...")

        def _do():
            res = self.engine.restore_normal_mode()

            def finish():
                self.master_btn.configure(state="normal")
                self.refresh_boost_status_ui()
                self.refresh_services_status_ui()
                self.refresh_apps_list_ui()

                if res.get("status") == "success":
                    self.log(f"🟢 Normal Mode Restored successfully!")
                    self.log(f"   • Services restarted: {res['restarted_services_count']}")
                    if res['restarted_services']:
                        self.log(f"     ({', '.join(res['restarted_services'])})")
                    self.log(f"   • Original Power Scheme restored: {res.get('power_scheme_restored')}")
                else:
                    self.log(f"ℹ️ {res.get('message', 'Already in normal mode.')}")
            self.after(0, finish)

        threading.Thread(target=_do, daemon=True).start()

    def on_clean_ram_click(self):
        self.log("Purging memory working sets and standby cache...")
        self.ram_clean_btn.configure(state="disabled", text="Cleaning...")

        def _do():
            res = engine.clean_system_ram()
            def finish():
                self.ram_clean_btn.configure(state="normal", text="🧹 Clean RAM Now")
                self.log(f"🧠 Memory Cleaned: {res['memory_freed_mb']} MB released across {res['processes_trimmed']} processes.")
            self.after(0, finish)

        threading.Thread(target=_do, daemon=True).start()

    def on_flush_dns_click(self):
        self.log("Flushing DNS resolver cache...")
        if engine.flush_dns_cache():
            self.log("✅ DNS Cache flushed successfully.")
        else:
            self.log("⚠️ Could not flush DNS cache.")

    def on_emergency_restore_click(self):
        self.log("⚠️ Executing Emergency Restore: restarting all safe services...")
        def _do():
            restarted = []
            for svc in engine.SERVICES_DB:
                if engine.start_service(svc["id"]):
                    restarted.append(svc["id"])
            self.engine.clear_snapshot()
            engine.clean_system_ram()

            def finish():
                self.refresh_boost_status_ui()
                self.refresh_services_status_ui()
                self.log(f"✅ Emergency Restore complete. Restarted {len(restarted)} services.")
            self.after(0, finish)

        threading.Thread(target=_do, daemon=True).start()

    def on_save_custom_profile_click(self):
        name = self.prof_name_entry.get().strip()
        desc = self.prof_desc_entry.get().strip()
        if not name:
            self.log("❌ Please enter a profile name first.")
            return

        cfg = self.get_current_ui_config()
        self.engine.save_custom_profile(
            name=name,
            description=desc,
            services=cfg["services"],
            tweaks=cfg["tweaks"],
            kill_apps=cfg["kill_background_apps"]
        )

        # Update combobox
        self.profile_names = list(self.engine.profiles.keys())
        self.profile_combo.configure(values=self.profile_names)
        self.profile_combo.set(name)
        self.current_profile_name = name

        self.prof_name_entry.delete(0, "end")
        self.prof_desc_entry.delete(0, "end")

        self.log(f"💾 Custom profile saved: [{name}] ({len(cfg['services'])} services, {len(cfg['kill_background_apps'])} apps)")

    def log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.log_textbox.insert("end", f"[{timestamp}] {message}\n")
        self.log_textbox.see("end")

    # ─── System Tray ─────────────────────────────────────────────────────────

    def minimize_to_tray(self):
        self.withdraw()
        self.init_tray_icon()

    def on_closing(self):
        # Minimize to tray instead of abruptly closing
        self.minimize_to_tray()

    def init_tray_icon(self):
        if self.tray_icon or not pystray:
            return

        def create_image():
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle([6, 6, 58, 58], radius=10, fill="#00E5FF", outline="white", width=2)
            try:
                font = ImageFont.truetype("arial.ttf", 34)
            except Exception:
                font = ImageFont.load_default()
            draw.text((20, 10), "T", fill="#0D1117", font=font)
            return img

        def tray_toggle_boost(icon, item):
            self.on_master_toggle_click()

        def tray_clean_ram(icon, item):
            self.on_clean_ram_click()

        def tray_show_window(icon, item):
            self.after(0, self.deiconify)
            if self.tray_icon:
                self.tray_icon.stop()
                self.tray_icon = None

        def tray_exit(icon, item):
            self.monitoring_active = False
            if self.tray_icon:
                self.tray_icon.stop()
            self.destroy()
            sys.exit(0)

        menu = pystray.Menu(
            pystray.MenuItem("📊 Open TurboBoost Dashboard", tray_show_window, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⚡ 1-Click Toggle Boost", tray_toggle_boost),
            pystray.MenuItem("🧹 Clean RAM Now", tray_clean_ram),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Exit TurboBoost", tray_exit)
        )

        self.tray_icon = pystray.Icon("TurboBoost", create_image(), "TurboBoost Optimizer", menu=menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()


# ─── Entry Point & Auto-Elevation ────────────────────────────────────────────

def main():
    if not engine.is_admin():
        engine.run_as_admin()
        return

    app = TurboBoostGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
