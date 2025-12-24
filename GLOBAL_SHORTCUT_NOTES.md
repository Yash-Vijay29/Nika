# Global Shortcut Limitation on KDE Wayland

## Current Implementation: `pynput`

The current global shortcut (`Ctrl + Super + N`) uses `pynput`:

```python
from pynput import keyboard

listener = keyboard.GlobalHotKeys({
    '<ctrl>+<cmd>+n': callback
})
```

### ⚠️ Known Issues

**On KDE Wayland:**
- `pynput` relies on X11 input monitoring
- Works via XWayland compatibility, but is **fragile**
- May break in future KDE/Plasma versions
- Can conflict with compositor shortcuts

**Security:**
- Wayland restricts global input monitoring
- X11 fallback may be disabled in secure environments

## Recommended Solution: KGlobalAccel

For production-ready KDE integration, use KDE's native shortcut system:

### Option 1: Python KDE Bindings (PyKF6)

```python
from PyKF6.KConfigWidgets import KGlobalAccel
from PyQt6.QtGui import QKeySequence

# Register shortcut through KDE
action = QAction("Show Assistant", self)
action.triggered.connect(self.control_panel.request_toggle)

KGlobalAccel.setGlobalShortcut(
    action,
    QKeySequence("Ctrl+Meta+N")
)
```

**Benefits:**
- Native KDE integration
- Survives Wayland security updates
- User can reconfigure in System Settings
- No X11 dependency

### Option 2: DBus Service

Register as a KDE service and let KWin trigger you:

```python
# Listen for DBus calls from KWin shortcut
from dbus.mainloop.pyqt6 import DBusQtMainLoop
import dbus
import dbus.service

class AssistantService(dbus.service.Object):
    @dbus.service.method("org.assistant.Interface")
    def Toggle(self):
        self.control_panel.request_toggle()
```

User sets shortcut in KDE System Settings → run custom command → `dbus-send ...`

## Migration Path

1. **Now:** Keep `pynput` for quick testing
2. **Production:** Add PyKF6 dependency
3. **Future:** Full KDE Plasma applet

## Installation

```bash
# For KGlobalAccel support
pip install PyKF6-KConfigWidgets
```

---

**Current Status:** Using `pynput` for rapid development. Works on most systems but may need KGlobalAccel for long-term stability on pure Wayland.
