from pynput import keyboard
import threading
from typing import Callable
from utils.logger import setup_logger

logger = setup_logger("KeyboardListener")

class GlobalKeyMonitor:
    """
    Listens for global hotkeys to trigger assistant features.
    """
    
    def __init__(self, on_trigger: Callable):
        self.on_trigger = on_trigger
        self.listener = None
        self.running = False

    def start(self):
        """Start the keyboard listener in a background thread."""
        if self.running:
            return
            
        self.running = True
        
        # Define the hotkey signature
        # <cmd> usually maps to Super/Windows key on Linux
        hotkeys = {
            '<ctrl>+<cmd>+n': self._on_activate
        }
        
        self.listener = keyboard.GlobalHotKeys(hotkeys)
        self.listener.start()
        logger.info("Global keyboard listener started (Ctrl+Super+N)")

    def stop(self):
        """Stop the keyboard listener."""
        self.running = False
        if self.listener:
            self.listener.stop()
            logger.info("Global keyboard listener stopped")

    def _on_activate(self):
        """Callback when hotkey is triggered."""
        logger.info("Global hotkey triggered!")
        if self.on_trigger:
            self.on_trigger()
