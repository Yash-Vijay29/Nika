from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
import threading
from queue import Queue
from typing import Optional
from utils.logger import setup_logger

logger = setup_logger("Voice")



class VoiceEngine:
    """Text-to-speech engine with support for multiple backends (ElevenLabs or Paroli)."""
    
    def __init__(self, backend: str = "elevenlabs", **kwargs):
        """
        Initialize voice engine with specified backend.
        
        Args:
            backend: "elevenlabs" or "paroli"
            **kwargs: Backend-specific parameters
                For ElevenLabs: api_key, voice_id
                For Paroli: encoder_path, decoder_path, config_path, use_gpu, espeak_data_path
        """
        self.backend = backend
        
        if backend == "elevenlabs":
            self._init_elevenlabs(**kwargs)
        elif backend == "paroli":
            self._init_paroli(**kwargs)
        else:
            raise ValueError(f"Unknown TTS backend: {backend}. Use 'elevenlabs' or 'paroli'")
    
    def _init_elevenlabs(self, api_key: Optional[str] = None, voice_id: str = "lhTvHflPVOqgSWyuWQry"):
        """Initialize ElevenLabs backend."""
        if not api_key:
            raise ValueError("ElevenLabs API key is required")
        
        self.client = ElevenLabs(api_key=api_key)
        self.voice_id = voice_id
        self.queue = Queue()
        self.running = False
        self.thread = None
        
        # Voice settings for natural-sounding speech
        self.voice_settings = VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            style=0.5,
            use_speaker_boost=True
        )
        logger.info(f"ElevenLabs voice engine initialized (voice: {voice_id})")
    
    def _init_paroli(self, encoder_path: str, decoder_path: str, config_path: str, 
                     use_gpu: bool = True, espeak_data_path: Optional[str] = None):
        """Initialize Paroli TTS backend."""
        from actions.paroli_tts import ParoliTTS
        
        self.paroli_engine = ParoliTTS(
            encoder_path=encoder_path,
            decoder_path=decoder_path,
            config_path=config_path,
            use_gpu=use_gpu,
            espeak_data_path=espeak_data_path
        )
        logger.info(f"Paroli TTS engine initialized (GPU: {use_gpu})")
    
    def start(self):
        """Start the voice processing thread."""
        if self.backend == "paroli":
            self.paroli_engine.start()
        else:
            if self.running:
                logger.warning("Voice engine already running")
                return
            
            self.running = True
            self.thread = threading.Thread(target=self._process_queue_elevenlabs, daemon=True)
            self.thread.start()
            logger.info("ElevenLabs voice engine started")
    
    def stop(self):
        """Stop the voice processing thread."""
        if self.backend == "paroli":
            self.paroli_engine.stop()
        else:
            self.running = False
            if self.thread:
                self.thread.join()
            logger.info("Voice engine stopped")
    
    def speak(self, text: str):
        """Queue text to be spoken."""
        if self.backend == "paroli":
            self.paroli_engine.speak(text)
        else:
            self.queue.put(text)
            logger.info(f"Queued speech: {text[:50]}...")
    
    def _process_queue_elevenlabs(self):
        """Process the speech queue using ElevenLabs."""
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
