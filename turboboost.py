"""
TurboBoost - Main Entry Point
Launches the TurboBoost GUI directly.
"""

import os
import sys
import ctypes
import traceback

def main():
    try:
        import turboboost_engine as engine
        import turboboost_gui as gui

        app = gui.TurboBoostGUI()
        app.mainloop()
    except Exception:
        err_msg = traceback.format_exc()
        print("TurboBoost Startup Error:\n", err_msg)
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                f"TurboBoost failed to start:\n\n{err_msg}",
                "TurboBoost Error",
                0x10
            )
        except Exception:
            pass

if __name__ == "__main__":
    main()
