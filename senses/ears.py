import multiprocessing
import time
import numpy as np
import io
import wave
import tempfile
import ctypes
from typing import Optional, Callable
from utils.logger import setup_logger

logger = setup_logger("Ears")


def _audio_process(api_key: str, 
                   speech_queue: multiprocessing.Queue, 
                   status_queue: multiprocessing.Queue,
                   stop_event: multiprocessing.Event, 
                   listening_flag: multiprocessing.Value,
                   silence_threshold: float, 
                   silence_duration: float, 
                   mode: str):
    """
    Standalone process for audio monitoring and transcription.
    """
    import sounddevice as sd
    from openai import OpenAI
    
    # Initialize OpenAI client inside process
    client = OpenAI(api_key=api_key)
    
    rate = 16000
    channels = 1
    
    frames = []
    is_speaking = False
    silence_start = None
    
    # Manual mode buffer
    manual_frames = []
    
    def process_and_transcribe(audio_frames):
        if not audio_frames or len(audio_frames) < 5:
            return
            
        try:
            # Notify start of processing
            status_queue.put("processing_start")
            
            # Concatenate frames
            audio_data = np.concatenate(audio_frames, axis=0)
            
            # Convert to int16
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            # Write to WAV buffer
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(2)
                wf.setframerate(rate)
                wf.writeframes(audio_int16.tobytes())
            
            wav_buffer.seek(0)
            
            # Temp file for Whisper
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(wav_buffer.read())
                temp_path = temp_file.name
            
            # Transcribe
            with open(temp_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )
            
            # Cleanup
            import os
            os.unlink(temp_path)
            
            text = transcript.text.strip()
            if text:
                logger.info(f"User said: {text}")
                speech_queue.put(text)
                
            # Notify completion
            status_queue.put("processing_complete")
            
        except Exception as e:
            logger.error(f"Error in transcription: {e}")
            status_queue.put("processing_complete")

    def audio_callback(indata, frames_count, time_info, status):
        nonlocal frames, is_speaking, silence_start, manual_frames
        
        if status:
            pass # Ignore overflow for now
            
        # Check shared listening flag for manual mode
        is_manual_listening = False
        with listening_flag.get_lock():
            is_manual_listening = listening_flag.value
            
        if mode == "manual":
            if is_manual_listening:
                manual_frames.append(indata.copy())
            elif manual_frames:
                # Stopped listening, process what we have
                to_process = manual_frames.copy()
                manual_frames.clear()
                process_and_transcribe(to_process)
            return

        # Auto mode logic
        rms = np.sqrt(np.mean(indata**2))
        
        if rms > silence_threshold:
            is_speaking = True
            silence_start = None
            frames.append(indata.copy())
        else:
            if is_speaking:
                frames.append(indata.copy())
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > silence_duration:
                    # Silence timeout, process speech
                    to_process = frames.copy()
                    frames = []
                    is_speaking = False
                    silence_start = None
                    process_and_transcribe(to_process)

    try:
        with sd.InputStream(samplerate=rate, channels=channels, callback=audio_callback, dtype=np.float32):
            logger.info(f"Audio process running (mode={mode})")
            while not stop_event.is_set():
                time.sleep(0.1)
    except Exception as e:
        logger.error(f"Audio process crashed: {e}")
    finally:
        logger.info("Audio process stopped")


class EarsWorker:
    """Monitors microphone for user speech via a separate process."""
    
    def __init__(self, api_key: str, 
                 on_speech_callback: Optional[Callable] = None, 
                 silence_threshold: float = 0.01, silence_duration: float = 2.0,
                 mode: str = "auto",
                 on_processing_start: Optional[Callable] = None,
                 on_processing_complete: Optional[Callable] = None):
        
        self.api_key = api_key
        self.on_speech_callback = on_speech_callback
        self.on_processing_start = on_processing_start
        self.on_processing_complete = on_processing_complete
        
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.mode = mode
        
        # IPC Primitives
        self.speech_queue = multiprocessing.Queue()
        self.status_queue = multiprocessing.Queue()
        self.stop_event = multiprocessing.Event()
        self.listening_flag = multiprocessing.Value(ctypes.c_bool, False) # For manual mode control
        
        self.process: Optional[multiprocessing.Process] = None

    def start(self):
        """Start the audio monitoring process."""
        if self.process and self.process.is_alive():
            logger.warning("Ears worker already running")
            return
            
        self.stop_event.clear()
        self.process = multiprocessing.Process(
            target=_audio_process,
            args=(self.api_key, self.speech_queue, self.status_queue, self.stop_event, 
                  self.listening_flag, self.silence_threshold, self.silence_duration, self.mode),
            daemon=True
        )
        self.process.start()
        logger.info("Ears worker process started")

    def stop(self):
        """Stop the audio monitoring process."""
        if self.process and self.process.is_alive():
            self.stop_event.set()
            self.process.join(timeout=3)
            if self.process.is_alive():
                self.process.terminate()
            logger.info("Ears worker stopped")

    def start_listening(self):
        """Manual mode: Start recording."""
        if self.mode == "manual":
            with self.listening_flag.get_lock():
                self.listening_flag.value = True
            logger.info("Manual listening started")

    def stop_listening(self):
        """Manual mode: Stop recording and process."""
        if self.mode == "manual":
            with self.listening_flag.get_lock():
                self.listening_flag.value = False
            logger.info("Manual listening stopped")

    def check_queues(self):
        """
        Poll queues for new data. call this from the main loop!
        """
        # Check speech queue
        while not self.speech_queue.empty():
            try:
                text = self.speech_queue.get_nowait()
                if self.on_speech_callback:
                    self.on_speech_callback(text)
            except:
                break
        
        # Check status queue
        while not self.status_queue.empty():
            try:
                status = self.status_queue.get_nowait()
                if status == "processing_start" and self.on_processing_start:
                    self.on_processing_start()
                elif status == "processing_complete" and self.on_processing_complete:
                    self.on_processing_complete()
            except:
                break
