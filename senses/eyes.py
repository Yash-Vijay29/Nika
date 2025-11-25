import cv2
import face_recognition
import threading
import time
from typing import Optional
from utils.logger import setup_logger

logger = setup_logger("Eyes")


class CameraWorker:
    """Monitors camera for user presence via face detection."""
    
    def __init__(self, state, camera_index: int = 0, check_interval: float = 2.0):
        self.state = state
        self.camera_index = camera_index
        self.check_interval = check_interval
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.camera = None
    
    def start(self):
        """Start the camera monitoring thread."""
        if self.running:
            logger.warning("Camera worker already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("Camera worker started")
    
    def stop(self):
        """Stop the camera monitoring thread."""
        self.running = False
        if self.thread:
            self.thread.join()
        if self.camera:
            self.camera.release()
        logger.info("Camera worker stopped")
    
    def _run(self):
        """Main loop for camera monitoring."""
        self.camera = cv2.VideoCapture(self.camera_index)
        
        if not self.camera.isOpened():
            logger.error(f"Could not open camera {self.camera_index}")
            return
        
        logger.info("Camera opened successfully")
        
        while self.running:
            try:
                ret, frame = self.camera.read()
                if not ret:
                    logger.warning("Failed to read frame from camera")
                    time.sleep(self.check_interval)
                    continue
                
                # Convert BGR (OpenCV) to RGB (face_recognition)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Resize for faster processing
                small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.25, fy=0.25)
                
                # Detect faces
                face_locations = face_recognition.face_locations(small_frame)
                
                # Update state
                user_present = len(face_locations) > 0
                self.state.update_user_presence(user_present)
                
                if user_present:
                    logger.debug(f"Detected {len(face_locations)} face(s)")
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in camera worker: {e}")
                time.sleep(self.check_interval)
        
        self.camera.release()
