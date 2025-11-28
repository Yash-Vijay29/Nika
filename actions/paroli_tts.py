"""
Paroli TTS Engine - Local GPU-accelerated Text-to-Speech
Uses the simplified paroli-cli binary for streaming audio synthesis.
"""

import subprocess
import threading
from queue import Queue
from typing import Optional
import numpy as np
import sounddevice as sd
from utils.logger import setup_logger
import os

logger = setup_logger("ParoliTTS")


class ParoliTTS:
    """Local TTS engine using paroli (streaming Piper) with GPU acceleration."""
    
    def __init__(
        self,
        encoder_path: str,
        decoder_path: str,
        config_path: str,
        use_gpu: bool = False,
        espeak_data_path: Optional[str] = None,
        sample_rate: int = 22050
    ):
        """
        Initialize Paroli TTS engine.
        
        Args:
            encoder_path: Path to encoder.onnx model
            decoder_path: Path to decoder.onnx model  
            config_path: Path to model config JSON
            use_gpu: Enable CUDA GPU acceleration
            espeak_data_path: Optional path to espeak-ng-data directory
            sample_rate: Audio sample rate (default: 22050 Hz)
        """
        self.encoder_path = encoder_path
        self.decoder_path = decoder_path
        self.config_path = config_path
        self.use_gpu = False
        self.espeak_data_path = espeak_data_path
        self.sample_rate = sample_rate
        
        # Find paroli-cli binary
        self.cli_path = os.path.join(
            os.path.dirname(__file__),
            "../paroli/build/paroli-cli"
        )
        
        if not os.path.exists(self.cli_path):
            raise FileNotFoundError(f"paroli-cli not found at {self.cli_path}. Please build it first.")
        
        # Verify model files exist
        for path, name in [
            (encoder_path, "encoder"),
            (decoder_path, "decoder"),
            (config_path, "config")
        ]:
            if not os.path.exists(path):
                raise FileNotFoundError(f"{name} model file not found: {path}")
        
        self.queue = Queue()
        self.running = False
        self.thread = None
        
        logger.info(f"Paroli TTS initialized (GPU: {use_gpu})")
    
    def start(self):
        """Start the TTS processing thread."""
        if self.running:
            logger.warning("Paroli TTS already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._process_queue, daemon=True)
        self.thread.start()
        logger.info("Paroli TTS engine started")
    
    def stop(self):
        """Stop the TTS processing thread."""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Paroli TTS engine stopped")
    
    def speak(self, text: str):
        """Queue text to be spoken."""
        self.queue.put(text)
        logger.info(f"Queued speech: {text[:50]}...")
    
    def _process_queue(self):
        """Process the speech queue."""
        while self.running:
            try:
                if not self.queue.empty():
                    text = self.queue.get(timeout=0.5)
                    logger.info(f"Synthesizing: {text}")
                    
                    # Build paroli-cli command
                    cmd = [
                        self.cli_path,
                        "--encoder", self.encoder_path,
                        "--decoder", self.decoder_path,
                        "-c", self.config_path
                    ]
                    
                    if self.use_gpu:
                        cmd.extend(["--accelerator", "cuda"])
                    
                    if self.espeak_data_path:
                        cmd.extend(["--espeak_data", self.espeak_data_path])
                    
                    # Prepare environment with library paths
                    env = os.environ.copy()
                    lib_paths = [
                        "/home/yash/Documents/Libraries/onnxruntime-linux-x64-gpu-1.22.0/lib",
                        "/home/yash/Documents/Libraries/piper_phonemize/lib"
                    ]
                    current_ld_path = env.get("LD_LIBRARY_PATH", "")
                    env["LD_LIBRARY_PATH"] = f"{':'.join(lib_paths)}:{current_ld_path}"

                    # Run paroli-cli with text input, get raw PCM audio output
                    process = subprocess.Popen(
                        cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        env=env
                    )
                    
                    # Send text and close stdin
                    stdout, stderr = process.communicate(input=text.encode('utf-8') + b'\n')
                    
                    if process.returncode != 0:
                        logger.error(f"paroli-cli error: {stderr.decode('utf-8', errors='ignore')}")
                        continue
                    
                    # Convert raw PCM bytes to numpy array
                    # paroli outputs int16 PCM audio
                    audio_data = np.frombuffer(stdout, dtype=np.int16).astype(np.float32) / 32768.0
                    
                    # Play audio immediately
                    sd.play(audio_data, self.sample_rate)
                    sd.wait()  # Wait for playback to complete
                    
                    logger.debug("Speech synthesis and playback completed")
                    
            except Exception as e:
                logger.error(f"Error in Paroli TTS processing: {e}")
                continue
