import sounddevice as sd
import wave
import threading
import time
import numpy as np
from typing import Optional, Callable
from openai import OpenAI
from utils.logger import setup_logger
import io
import tempfile

logger = setup_logger("Ears")


class EarsWorker:
    """Monitors microphone for user speech and transcribes using OpenAI Whisper."""
    
    def __init__(self, api_key: str, on_speech_callback: Optional[Callable] = None, 
                 silence_threshold: float = 0.01, silence_duration: float = 2.0,
                 mode: str = "auto"):
        """
        Initialize the ears worker.
        
        Args:
            api_key: OpenAI API key
            on_speech_callback: Callback function(text) when speech is detected
            silence_threshold: RMS threshold for silence detection (normalized 0-1)
            silence_duration: Seconds of silence before processing audio
            mode: "auto" for automatic detection, "manual" for GUI-controlled recording
        """
        self.client = OpenAI(api_key=api_key)
        self.on_speech_callback = on_speech_callback
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.mode = mode
        
        # Audio settings
        self.rate = 16000  # 16kHz recommended for Whisper
        self.channels = 1
        
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Manual mode control
        self.listening_active = False  # For manual mode: True when recording
        self.manual_frames = []  # Store frames in manual mode
        self.manual_lock = threading.Lock()  # Thread safety for manual mode
    
    def start(self):
        """Start the microphone monitoring thread."""
        if self.running:
            logger.warning("Ears worker already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("Ears worker started - listening for speech")
    
    def stop(self):
        """Stop the microphone monitoring thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Ears worker stopped")
    
    def start_listening(self):
        """Start listening in manual mode (called by GUI button)."""
        if self.mode != "manual":
            logger.warning("start_listening() only works in manual mode")
            return
        
        with self.manual_lock:
            self.listening_active = True
            self.manual_frames = []
        logger.info("Manual listening started")
    
    def stop_listening(self):
        """Stop listening and process speech in manual mode (called by GUI button)."""
        if self.mode != "manual":
            logger.warning("stop_listening() only works in manual mode")
            return
        
        with self.manual_lock:
            self.listening_active = False
            frames_to_process = self.manual_frames.copy()
            self.manual_frames = []
        
        logger.info("Manual listening stopped, processing audio")
        
        # Process the recorded frames
        if frames_to_process:
            self._process_speech(frames_to_process)
    
    def _calculate_rms(self, audio_data: np.ndarray) -> float:
        """Calculate RMS (root mean square) of audio data."""
        return np.sqrt(np.mean(audio_data**2))
    
    def _run(self):
        """Main loop for microphone monitoring."""
        try:
            logger.info("Microphone stream opened")
            self._listen_for_speech()
        except Exception as e:
            logger.error(f"Error in ears worker: {e}")
    
    def _listen_for_speech(self):
        """Listen for speech and transcribe when detected."""
        frames = []
        is_speaking = False
        silence_start = None
        
        def audio_callback(indata, frames_count, time_info, status):
            """Callback for sounddevice stream."""
            nonlocal frames, is_speaking, silence_start
            
            if status:
                logger.warning(f"Audio callback status: {status}")
            
            # Manual mode: only record when listening_active is True
            if self.mode == "manual":
                with self.manual_lock:
                    if self.listening_active:
                        self.manual_frames.append(indata.copy())
                return
            
            # Auto mode: use threshold-based detection
            # Calculate RMS
            rms = self._calculate_rms(indata)
            
            # Detect speech vs silence
            if rms > self.silence_threshold:
                is_speaking = True
                silence_start = None
                frames.append(indata.copy())
            else:
                if is_speaking:
                    frames.append(indata.copy())
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start > self.silence_duration:
                        # Process the recorded speech in a separate thread
                        recorded_frames = frames.copy()
                        threading.Thread(
                            target=self._process_speech,
                            args=(recorded_frames,),
                            daemon=True
                        ).start()
                        frames = []
                        is_speaking = False
                        silence_start = None
        
        try:
            # Open audio stream
            with sd.InputStream(
                samplerate=self.rate,
                channels=self.channels,
                callback=audio_callback,
                dtype=np.float32
            ):
                mode_desc = "manual (GUI-controlled)" if self.mode == "manual" else "auto (threshold-based)"
                logger.info(f"Listening for speech in {mode_desc} mode...")
                while self.running:
                    time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in audio stream: {e}")
    
    def _process_speech(self, frames: list):
        """Process recorded audio frames and transcribe."""
        if not frames or len(frames) < 5:  # Ignore very short recordings
            return
        
        try:
            # Concatenate all frames
            audio_data = np.concatenate(frames, axis=0)
            
            # Convert float32 to int16 for WAV file
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            # Convert to WAV format in memory
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 2 bytes for int16
                wf.setframerate(self.rate)
                wf.writeframes(audio_int16.tobytes())
            
            wav_buffer.seek(0)
            
            # Create temporary file for Whisper API (it requires a file)
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(wav_buffer.read())
                temp_path = temp_file.name
            
            # Transcribe using OpenAI Whisper
            with open(temp_path, 'rb') as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"  # Can be set to None for auto-detection
                )
            
            # Clean up temp file
            import os
            os.unlink(temp_path)
            
            text = transcript.text.strip()
            if text:
                logger.info(f"User said: {text}")
                if self.on_speech_callback:
                    self.on_speech_callback(text)
            
        except Exception as e:
            logger.error(f"Error transcribing speech: {e}")
