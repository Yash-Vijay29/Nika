import multiprocessing
import time
import ctypes
from typing import Optional
from utils.logger import setup_logger

logger = setup_logger("Eyes")


def _camera_process(camera_index: int, check_interval: float, 
                    user_present_val: multiprocessing.Value, 
                    stop_event: multiprocessing.Event):
    """
    Standalone function to run in a separate process.
    Imports are done here to avoid loading heavy libraries in the main process.
    """
    import cv2
    import face_recognition

    logger.info(f"Camera process started (Index: {camera_index})")
    
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        logger.error(f"Could not open camera {camera_index}")
        return

    try:
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                logger.warning("Failed to read frame")
                time.sleep(check_interval)
                continue

            # Convert BGR (OpenCV) to RGB (face_recognition)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Resize for faster processing
            small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.25, fy=0.25)

            # Detect faces
            face_locations = face_recognition.face_locations(small_frame)
            
            # Update shared state
            is_present = len(face_locations) > 0
            with user_present_val.get_lock():
                user_present_val.value = is_present
            
            if is_present:
                # logger.debug(f"Detected {len(face_locations)} face(s)")
                pass

            time.sleep(check_interval)

    except Exception as e:
        logger.error(f"Error in camera process: {e}")
    finally:
        cap.release()
        logger.info("Camera process stopped")


class CameraWorker:
    """Monitors camera for user presence via face detection using a separate process."""
    
    def __init__(self, camera_index: int = 0, check_interval: float = 2.0):
        self.camera_index = camera_index
        self.check_interval = check_interval
        
        # Shared memory for state
        self.user_present = multiprocessing.Value(ctypes.c_bool, False)
        self.stop_event = multiprocessing.Event()
        self.process: Optional[multiprocessing.Process] = None
    
    def start(self):
        """Start the camera monitoring process."""
        if self.process and self.process.is_alive():
            logger.warning("Camera worker already running")
            return
        
        self.stop_event.clear()
        self.process = multiprocessing.Process(
            target=_camera_process,
            args=(self.camera_index, self.check_interval, self.user_present, self.stop_event),
            daemon=True
        )
        self.process.start()
    
    def stop(self):
        """Stop the camera monitoring process."""
        if self.process and self.process.is_alive():
            self.stop_event.set()
            self.process.join(timeout=3)
            if self.process.is_alive():
                self.process.terminate()
            logger.info("Camera worker stopped")
    
    def is_user_present(self) -> bool:
        """Read the current shared state."""
        with self.user_present.get_lock():
            return self.user_present.value
