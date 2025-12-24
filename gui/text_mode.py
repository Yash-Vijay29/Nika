import tkinter as tk
from tkinter import ttk
import threading
from typing import Optional, Callable
from utils.logger import setup_logger

logger = setup_logger("TextModeGUI")

class TextQueryGUI:
    """
    A dynamic overlay GUI for text interactions.
    Appears as a search bar, expands to a chat panel after query submission.
    """
    
    def __init__(self, on_submit_callback: Callable[[str], None]):
        self.on_submit_callback = on_submit_callback
        self.root: Optional[tk.Tk] = None
        self.entry: Optional[tk.Entry] = None
        self.history_area: Optional[tk.Text] = None
        self.is_visible = False
        self.is_expanded = False
        
        # Geometry constants
        self.WIDTH = 800
        self.SEARCH_HEIGHT = 60
        self.CHAT_HEIGHT = 500
        
        # Initialize in a separate thread context usually, but here we prepare for the main loop
        # We don't start the loop here, assuming it's part of the main application flow 
        # or managed via update() calls if integrated into existing tk loop.
        # However, since this is a separate window that might need its own lifecycle or 
        # coexist with MicrophoneGUI, we need to be careful.
        # For this architecture, we'll assume it's created and hidden.

    def start(self):
        """Create the window but keep it hidden initially."""
        if self.root:
            return
            
        self.root = tk.Tk()
        self.root.title("Living Assistant")
        self.root.withdraw() # Start hidden
        
        # Frameless and always on top
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg='#1e1e1e')
        
        # Center horizontally, top 20% vertically
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - self.WIDTH) // 2
        y = int(screen_height * 0.2)
        self.geometry_base = f"+{x}+{y}"
        
        self.root.geometry(f"{self.WIDTH}x{self.SEARCH_HEIGHT}{self.geometry_base}")
        
        # Styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Input Frame
        input_frame = tk.Frame(self.root, bg='#1e1e1e')
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Search Entry
        self.entry = tk.Entry(
            input_frame,
            font=('Segoe UI', 14),
            bg='#2d2d2d',
            fg='white',
            insertbackground='white',
            relief=tk.FLAT,
            bd=5
        )
        self.entry.pack(fill=tk.X, expand=True)
        self.entry.bind('<Return>', self._handle_submit)
        self.entry.bind('<Escape>', self.hide)
        self.entry.focus_set()
        
        # History Area (Initially Hidden or packed with 0 height?)
        # We'll pack it but manage visibility via window size
        self.history_frame = tk.Frame(self.root, bg='#1e1e1e')
        # Don't pack immediately
        
        self.history_area = tk.Text(
            self.history_frame,
            font=('Segoe UI', 11),
            bg='#1e1e1e',
            fg='#dddddd',
            relief=tk.FLAT,
            wrap=tk.WORD,
            state=tk.DISABLED,
            height=20
        )
        self.history_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        logger.info("Text Mode GUI initialized")

    def show(self):
        """Show the GUI (must be called from main thread)."""
        if not self.root:
            return
            
        self.root.deiconify()
        self.root.lift()
        self.entry.delete(0, tk.END)
        self.entry.focus_force()
        self._set_search_mode()
        self.is_visible = True
        logger.info("Text Mode GUI shown")

    def hide(self, event=None):
        """Hide the GUI."""
        if self.root:
            self.root.withdraw()
            self.is_visible = False
            self._set_search_mode() # Reset state
            logger.info("Text Mode GUI hidden")

    def toggle(self):
        """Toggle visibility."""
        if self.is_visible:
            self.hide()
        else:
            self.show()

    def _set_search_mode(self):
        """Set window to small search bar mode."""
        self.root.geometry(f"{self.WIDTH}x{self.SEARCH_HEIGHT}{self.geometry_base}")
        self.history_frame.pack_forget()
        self.is_expanded = False

    def _set_chat_mode(self):
        """Expand window to chat mode."""
        self.root.geometry(f"{self.WIDTH}x{self.CHAT_HEIGHT}{self.geometry_base}")
        self.history_frame.pack(fill=tk.BOTH, expand=True)
        self.is_expanded = True

    def _handle_submit(self, event=None):
        """Handle Enter key press."""
        query = self.entry.get().strip()
        if not query:
            return
            
        if not self.is_expanded:
            self._set_chat_mode()
            
        self._add_to_history(f"> {query}", "user")
        self.entry.delete(0, tk.END)
        
        # Execute callback asynchronously
        self._add_to_history("Processing...", "system")
        threading.Thread(target=self.on_submit_callback, args=(query,), daemon=True).start()

    def _add_to_history(self, text: str, tag: str):
        """Add text to the history area."""
        self.history_area.config(state=tk.NORMAL)
        self.history_area.insert(tk.END, text + "\n\n", tag)
        self.history_area.see(tk.END)
        self.history_area.config(state=tk.DISABLED)

    def add_response(self, text: str):
        """Public method to add a response from the system."""
        # Clean up "Processing..." if it was the last line? (Simplification: just append)
        def _update():
            self._add_to_history(text, "assistant")
        if self.root:
            self.root.after(0, _update)

    def update(self):
        """Run update loop step (if integrated in external loop)."""
        if self.root:
            self.root.update()
