"""
TurboBoost - Main Entry Point
Checks for Administrator privileges, auto-elevates if necessary, and starts the GUI.
"""

import sys
import turboboost_engine as engine
import turboboost_gui as gui

def main():
    if not engine.is_admin():
        print("TurboBoost requires Administrator privileges to manage services and power plans.")
        print("Requesting elevation...")
        engine.run_as_admin()
        return

    app = gui.TurboBoostGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
