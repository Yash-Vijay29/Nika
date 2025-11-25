import mss
import threading
import time
from typing import Optional
from PIL import Image
import io
import base64
from utils.logger import setup_logger

logger = setup_logger("Screen")


class ScreenWorker:
    """Monitors screen activity and captures screenshots."""
    
    def __init__(self, state, check_interval: float = 30.0):
        self.state = state
        self.check_interval = check_interval
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.sct = None
        self.last_screenshot: Optional[bytes] = None
    
    def start(self):
        """Start the screen monitoring thread."""
        if self.running:
            logger.warning("Screen worker already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("Screen worker started")
    
    def stop(self):
        """Stop the screen monitoring thread."""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Screen worker stopped")
    
    def _run(self):
        """Main loop for screen monitoring."""
        self.sct = mss.mss()
        
        while self.running:
            try:
                # Only capture if user is present
                if not self.state.user_present:
                    time.sleep(self.check_interval)
                    continue
                
                # Capture screenshot
                screenshot = self.sct.grab(self.sct.monitors[1])  # Primary monitor
                
                # Convert to PIL Image
                img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
                
                # Resize to reduce size (for LLM processing)
                img.thumbnail((1024, 768), Image.Resampling.LANCZOS)
                
                # Store as bytes
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG', quality=70)
                self.last_screenshot = img_byte_arr.getvalue()
                
                logger.debug("Captured screenshot")
                
                # Update state with placeholder (actual analysis done by Brain)
                self.state.update_activity("Activity analysis pending")
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in screen worker: {e}")
                time.sleep(self.check_interval)
    
    def get_screenshot_base64(self) -> Optional[str]:
        """Get the last screenshot as base64 encoded string."""
        if self.last_screenshot:
            return base64.b64encode(self.last_screenshot).decode('utf-8')
        return None
