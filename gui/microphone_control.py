import tkinter as tk
from tkinter import ttk
from typing import Optional
from utils.logger import setup_logger
import threading

logger = setup_logger("MicrophoneGUI")


class MicrophoneGUI:
    """GUI control for manual microphone activation."""
    
    def __init__(self, ears_worker):
        """
        Initialize the microphone control GUI.
        
        Args:
            ears_worker: Reference to EarsWorker instance for manual control
        """
        self.ears_worker = ears_worker
        self.root: Optional[tk.Tk] = None
        self.button: Optional[tk.Button] = None
        self.status_label: Optional[tk.Label] = None
        self.is_listening = False
        
        logger.info("Microphone GUI initialized")
    
    def start(self):
        """Start the GUI in the main thread."""
        self._create_window()
        logger.info("Microphone GUI window created")
    
    def _create_window(self):
        """Create the GUI window."""
        self.root = tk.Tk()
        self.root.title("Living Assistant - Microphone")
        
        # Window configuration
        self.root.geometry("250x120")
        self.root.resizable(False, False)
        
        # Always on top
        self.root.attributes('-topmost', True)
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title label
        title_label = ttk.Label(
            main_frame, 
            text="Microphone Control",
            font=('Arial', 11, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(
            main_frame,
            text="Ready",
            font=('Arial', 9),
            foreground='gray'
        )
        self.status_label.pack(pady=(0, 8))
        
        # Button
        self.button = tk.Button(
            main_frame,
            text="Start Speaking",
            command=self._toggle_listening,
            bg='#4CAF50',
            fg='white',
            font=('Arial', 10, 'bold'),
            relief=tk.RAISED,
            bd=3,
            padx=20,
            pady=8,
            cursor='hand2'
        )
        self.button.pack()
        
        logger.info("GUI window configured")
    
    def _toggle_listening(self):
        """Toggle listening state when button is clicked."""
        if not self.is_listening:
            # Start listening
            self.is_listening = True
            self.button.config(
                text="Stop Speaking",
                bg='#f44336'
            )
            self.status_label.config(
                text="Listening...",
                foreground='red'
            )
            
            # Start recording in ears worker
            if self.ears_worker:
                threading.Thread(
                    target=self.ears_worker.start_listening,
                    daemon=True
                ).start()
            
            logger.info("Started listening (manual mode)")
        else:
            # Stop listening
            self.is_listening = False
            self.button.config(
                text="Processing...",
                bg='#FF9800',
                state=tk.DISABLED
            )
            self.status_label.config(
                text="Processing...",
                foreground='orange'
            )
            
            # Stop recording and process in ears worker
            if self.ears_worker:
                threading.Thread(
                    target=self._stop_and_reset,
                    daemon=True
                ).start()
            
            logger.info("Stopped listening, processing speech")
    
    def _stop_and_reset(self):
        """Stop listening and reset button state after processing."""
        if self.ears_worker:
            self.ears_worker.stop_listening()
        
        # Wait a moment for processing to complete
        import time
        time.sleep(1)
        
        # Reset button state in main thread
        self.root.after(0, self._reset_button)
    
    def _reset_button(self):
        """Reset button to initial state (must be called from main thread)."""
        if self.button:
            self.button.config(
                text="Start Speaking",
                bg='#4CAF50',
                state=tk.NORMAL
            )
        if self.status_label:
            self.status_label.config(
                text="Ready",
                foreground='gray'
            )
        logger.debug("Button reset to ready state")
    
    def run(self):
        """Run the GUI main loop (blocking)."""
        if self.root:
            logger.info("Starting GUI main loop")
            self.root.mainloop()
    
    def stop(self):
        """Stop the GUI."""
        if self.root:
            self.root.quit()
            logger.info("GUI stopped")
