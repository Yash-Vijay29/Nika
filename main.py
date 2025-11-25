#!/usr/bin/env python3
"""
Living Laptop Assistant - Main Entry Point

A persistent AI companion that:
- Monitors your presence via camera
- Observes your screen activity
- Speaks to you via TTS
- Messages you via Google Chat
- Helps you stay on track with your goals
"""

import time
import signal
import sys
from utils.logger import setup_logger
from core.state import AssistantState
from core.memory import Memory
from core.brain import Brain
from senses.eyes import CameraWorker
from senses.screen import ScreenWorker
from actions.voice import VoiceEngine
from actions.chat import GoogleChatMessenger
from core.schedule_manager import ScheduleManager
from core.scheduler import Scheduler
import config

logger = setup_logger("Main")


class LivingAssistant:
    """Main orchestrator for the Living Assistant."""
    
    def __init__(self):
        logger.info("Initializing Living Assistant...")
        
        # Core components
        self.state = AssistantState()
        self.memory = Memory()
        
        # Actions
        if not config.ELEVENLABS_API_KEY:
            logger.error("ELEVENLABS_API_KEY not set! Please configure .env file")
            sys.exit(1)
        
        self.voice = VoiceEngine(
            api_key=config.ELEVENLABS_API_KEY,
            voice_id=config.VOICE_ID
        )
        self.chat = GoogleChatMessenger(config.GOOGLE_CHAT_WEBHOOK)
        
        # Senses
        self.eyes = CameraWorker(
            state=self.state,
            camera_index=config.CAMERA_INDEX,
            check_interval=config.CHECK_INTERVAL_SECONDS
        )
        self.screen = ScreenWorker(
            state=self.state,
            check_interval=config.SCREEN_ANALYSIS_INTERVAL_SECONDS
        )
        
        # Brain (needs API key)
        if not config.OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY not set! Please configure .env file")
            sys.exit(1)
        
        self.brain = Brain(
            api_key=config.OPENAI_API_KEY,
            state=self.state,
            memory=self.memory,
            voice_engine=self.voice,
            chat_messenger=self.chat
        )
        
        # Scheduler for scheduled Google Chat messages
        self.schedule_manager = ScheduleManager(config.SCHEDULES_FILE)
        self.scheduler = Scheduler(
            schedule_manager=self.schedule_manager,
            chat_messenger=self.chat,
            check_interval=config.SCHEDULER_CHECK_INTERVAL_SECONDS
        )
        # Update brain with schedule manager for voice command integration
        self.brain.schedule_manager = self.schedule_manager
        
        # Ears (microphone) - optional, only if enabled and PyAudio works
        self.ears = None
        self.mic_gui = None
        if config.ENABLE_SPEECH_TO_TEXT:
            try:
                from senses.ears import EarsWorker
                self.ears = EarsWorker(
                    api_key=config.OPENAI_API_KEY,
                    on_speech_callback=self._on_user_speech,
                    silence_threshold=config.SILENCE_THRESHOLD,
                    silence_duration=config.SILENCE_DURATION,
                    mode=config.MICROPHONE_MODE
                )
                logger.info(f"Ears worker initialized in '{config.MICROPHONE_MODE}' mode")
                
                # Initialize GUI for manual mode
                if config.MICROPHONE_MODE == "manual":
                    from gui.microphone_control import MicrophoneGUI
                    self.mic_gui = MicrophoneGUI(self.ears)
                    logger.info("Microphone GUI initialized for manual mode")
                    
            except Exception as e:
                logger.warning(f"Could not initialize ears worker (speech-to-text disabled): {e}")
                logger.warning("Speech-to-text requires sounddevice. Check if your microphone is accessible.")
                self.ears = None
                self.mic_gui = None

        
        self.running = False
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Shutdown signal received")
        self.stop()
    
    def start(self):
        """Start all components."""
        logger.info("Starting Living Assistant...")
        
        self.running = True
        
        # Start action engines
        self.voice.start()
        
        # Start sensory workers
        self.eyes.start()
        self.screen.start()
        if self.ears:
            self.ears.start()
        
        # Start scheduler
        self.scheduler.start()
        
        logger.info("All systems online! 🚀")
        self.voice.speak("Hello! I'm awake and ready to assist you.")
        
        # Start GUI if in manual mode (must be created in main thread)
        if self.mic_gui:
            self.mic_gui.start()
            logger.info("Microphone GUI window opened")
        
        # Main loop
        try:
            self._main_loop()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.stop()
    
    def _main_loop(self):
        """Main decision loop."""
        while self.running:
            try:
                # Process GUI events if in manual mode
                if self.mic_gui and self.mic_gui.root:
                    self.mic_gui.root.update()
                
                # Get current screenshot if available
                screenshot = self.screen.get_screenshot_base64()
                
                # Let the brain decide what to do
                decision = self.brain.analyze_and_decide(screenshot)
                
                # Execute the decision
                self.brain.execute_decision(decision)
                
                # Sleep before next iteration
                time.sleep(config.CHECK_INTERVAL_SECONDS)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(config.CHECK_INTERVAL_SECONDS)
    
    def stop(self):
        """Stop all components."""
        logger.info("Shutting down Living Assistant...")
        
        self.running = False
        
        # Stop GUI if running
        if self.mic_gui:
            self.mic_gui.stop()
        
        # Stop workers
        self.eyes.stop()
        self.screen.stop()
        if self.ears:
            self.ears.stop()
        self.voice.stop()
        self.scheduler.stop()
        
        logger.info("Goodbye! 👋")
        sys.exit(0)
    
    def _on_user_speech(self, text: str):
        """Callback when user speech is detected."""
        logger.info(f"Processing user speech: {text}")
        self.brain.handle_user_speech(text)


def main():
    """Entry point."""
    assistant = LivingAssistant()
    assistant.start()


if __name__ == "__main__":
    main()
