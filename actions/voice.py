from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
import threading
from queue import Queue
from typing import Optional
from utils.logger import setup_logger

logger = setup_logger("Voice")


class VoiceEngine:
    """Text-to-speech engine using ElevenLabs API with queued output."""
    
    def __init__(self, api_key: Optional[str] = None, voice_id: str = "lhTvHflPVOqgSWyuWQry"):
        """
        Initialize ElevenLabs voice engine.
        
        Args:
            api_key: ElevenLabs API key
            voice_id: Voice ID to use (default: Rachel - warm female voice)
        """
        if not api_key:
            raise ValueError("ElevenLabs API key is required")
        
        self.client = ElevenLabs(api_key=api_key)
        self.voice_id = voice_id
        self.queue = Queue()
        self.running = False
        self.thread = None
        
        # Voice settings for natural-sounding speech
        self.voice_settings = VoiceSettings(
            stability=0.5,  # Lower = more expressive
            similarity_boost=0.75,  # Voice consistency
            style=0.5,  # Style exaggeration
            use_speaker_boost=True
        )
    
    def start(self):
        """Start the voice processing thread."""
        if self.running:
            logger.warning("Voice engine already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._process_queue, daemon=True)
        self.thread.start()
        logger.info("ElevenLabs voice engine started")
    
    def stop(self):
        """Stop the voice processing thread."""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Voice engine stopped")
    
    def speak(self, text: str):
        """Queue text to be spoken."""
        self.queue.put(text)
        logger.info(f"Queued speech: {text[:50]}...")
    
    def _process_queue(self):
        """Process the speech queue."""
        import io
        import soundfile as sf
        import sounddevice as sd
        
        while self.running:
            try:
                if not self.queue.empty():
                    text = self.queue.get(timeout=0.5)
                    logger.info(f"Speaking: {text}")
                    
                    # Generate audio using ElevenLabs
                    audio_generator = self.client.text_to_speech.convert(
                        voice_id=self.voice_id,
                        text=text,
                        model_id="eleven_turbo_v2_5",  # Fast model
                        voice_settings=self.voice_settings
                    )
                    
                    # Collect audio chunks
                    audio_bytes = b"".join(audio_generator)
                    
                    # Play audio
                    audio_data, sample_rate = sf.read(io.BytesIO(audio_bytes))
                    sd.play(audio_data, sample_rate)
                    sd.wait()  # Wait for playback to complete
                    
                    logger.debug("Speech completed")
            except Exception as e:
                logger.error(f"Error in voice processing: {e}")
                continue
