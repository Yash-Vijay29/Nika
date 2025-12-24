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
from PyQt6.QtWidgets import QApplication

logger = setup_logger("Main")


class LivingAssistant:
    """Main orchestrator for the Living Assistant."""
    
    def __init__(self):
        logger.info("Initializing Living Assistant...")
        
        # Core components
        self.state = AssistantState()
        self.memory = Memory()
        
        # Actions
        
        # Initialize voice engine based on TTS backend
        if config.TTS_BACKEND == "elevenlabs":
            if not config.ELEVENLABS_API_KEY:
                logger.error("ELEVENLABS_API_KEY not set! Please configure .env file")
                sys.exit(1)
            
            self.voice = VoiceEngine(
                backend="elevenlabs",
                api_key=config.ELEVENLABS_API_KEY,
                voice_id=config.VOICE_ID
            )
        elif config.TTS_BACKEND == "paroli":
            # Validate paroli configuration
            import os
            for path, name in [
                (config.PAROLI_ENCODER_PATH, "PAROLI_ENCODER_PATH"),
                (config.PAROLI_DECODER_PATH, "PAROLI_DECODER_PATH"),
                (config.PAROLI_CONFIG_PATH, "PAROLI_CONFIG_PATH")
            ]:
                if not os.path.exists(path):
                    logger.error(f"{name} file not found: {path}")
                    sys.exit(1)
            
            self.voice = VoiceEngine(
                backend="paroli",
                encoder_path=config.PAROLI_ENCODER_PATH,
                decoder_path=config.PAROLI_DECODER_PATH,
                config_path=config.PAROLI_CONFIG_PATH,
                use_gpu=config.PAROLI_USE_GPU,
                espeak_data_path=config.PAROLI_ESPEAK_DATA_PATH if os.path.exists(config.PAROLI_ESPEAK_DATA_PATH) else None
            )
        else:
            logger.error(f"Unknown TTS_BACKEND: {config.TTS_BACKEND}. Use 'elevenlabs' or 'paroli'")
            sys.exit(1)
        self.chat = GoogleChatMessenger(config.GOOGLE_CHAT_WEBHOOK)
        
        # Senses
        self.eyes = CameraWorker(
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
        
        # Unified Control Panel (combines text and voice mode)
        self.control_panel = None
        self.kb_listener = None
        self.ears = None
        
        if config.ENABLE_SPEECH_TO_TEXT:
            try:
                from senses.ears import EarsWorker
                from gui.unified_control_qt import UnifiedControlPanel
                from senses.keyboard_listener import GlobalKeyMonitor
                
                # Initialize unified control panel first
                self.control_panel = UnifiedControlPanel(
                    on_text_submit=self._on_text_query,
                    ears_worker=None,  # Will be set after ears worker is created
                    microphone_mode=config.MICROPHONE_MODE
                )
                
                # Initialize ears worker (callbacks handled via polling in main loop)
                self.ears = EarsWorker(
                    api_key=config.OPENAI_API_KEY,
                    on_speech_callback=self._on_user_speech,
                    silence_threshold=config.SILENCE_THRESHOLD,
                    silence_duration=config.SILENCE_DURATION,
                    mode=config.MICROPHONE_MODE,
                    on_processing_start=self.control_panel.on_transcription_start,
                    on_processing_complete=self.control_panel.on_transcription_complete
                )
                
                # Now connect ears worker to panel
                self.control_panel.ears_worker = self.ears
                
                # Initialize keyboard listener to toggle the panel
                self.kb_listener = GlobalKeyMonitor(
                    on_trigger=self.control_panel.request_toggle
                )
                
                logger.info(f"Unified Control Panel initialized (microphone_mode={config.MICROPHONE_MODE})")
                
            except Exception as e:
                logger.warning(f"Could not initialize control panel: {e}")
                self.control_panel = None
                self.ears = None
                self.kb_listener = None
        else:
            # Text mode only (no speech-to-text)
            try:
                from gui.unified_control_qt import UnifiedControlPanel
                from senses.keyboard_listener import GlobalKeyMonitor
                
                self.control_panel = UnifiedControlPanel(
                    on_text_submit=self._on_text_query,
                    ears_worker=None,
                    microphone_mode="manual"  # Doesn't matter since no ears worker
                )
                
                self.kb_listener = GlobalKeyMonitor(
                    on_trigger=self.control_panel.request_toggle
                )
                
                logger.info("Unified Control Panel initialized (text only)")
                
            except Exception as e:
                logger.error(f"Failed to initialize control panel: {e}")
                self.control_panel = None
                self.kb_listener = None

        
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
        
        # Start Unified Control Panel (hidden initially) and Keyboard Listener
        if self.control_panel:
            self.control_panel.start()
            logger.info("Unified Control Panel ready")
        if self.kb_listener:
            self.kb_listener.start()
        
        # Main loop
        try:
            self._main_loop()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.stop()
    
    def _main_loop(self):
        """Main decision loop with Qt event processing."""
        from PyQt6.QtWidgets import QApplication
        
        # Schedule brain analysis separately (slower)
        self._schedule_brain_analysis()
        
        # Fast GUI update loop
        while self.running:
            try:
                # Process Qt events (needed for signals/slots to work)
                QApplication.processEvents()
                
                # Poll Ears Queue (Multiprocessing IPC)
                if self.ears:
                    self.ears.check_queues()
                
                # Poll Eyes State (Multiprocessing IPC)
                # (Optional: If we want to mirror presence in GUI later)
                
                # Sleep to avoid CPU spinning
                time.sleep(0.05)  # 50ms = 20 FPS, plenty for UI
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(0.1)
    
    def _schedule_brain_analysis(self):
        """Schedule periodic brain analysis (runs independently of GUI)."""
        if not self.running:
            return
            
        try:
            # Check user presence from Eyes (IPC Value)
            is_present = self.eyes.is_user_present()
            self.state.update_user_presence(is_present)

            # Get current screenshot if available
            screenshot = self.screen.get_screenshot_base64()
            
            # Let the brain decide what to do
            decision = self.brain.analyze_and_decide(screenshot)
            
            # Execute the decision
            self.brain.execute_decision(decision)
            
        except Exception as e:
            logger.error(f"Error in brain analysis: {e}")
        
        # Schedule next analysis
        if self.running:
            # Use threading.Timer for next iteration
            import threading
            timer = threading.Timer(
                config.CHECK_INTERVAL_SECONDS,
                self._schedule_brain_analysis
            )
            timer.daemon = True
            timer.start()
    
    def stop(self):
        """Stop all components."""
        logger.info("Shutting down Living Assistant...")
        
        self.running = False
        
        # Stop Keyboard Listener
        if self.kb_listener:
            self.kb_listener.stop()
            
        # Stop Control Panel (handled by the panel itself on hide)
        if self.control_panel:
            self.control_panel.request_hide()
        
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

    def _on_text_query(self, text: str):
        """Callback when user submits text via Control Panel."""
        logger.info(f"Processing text query: {text}")
        
        # Reuse the logic for speech handling since it's just text input
        response = self.brain.handle_user_speech(text)
        
        logger.info(f"Got response from brain: {response}")
        
        # Display actual response in the Control Panel
        if self.control_panel and response:
            logger.info("Sending response to GUI...")
            self.control_panel.add_response(response)
        else:
            logger.warning(f"Not sending to GUI - control_panel={self.control_panel}, response={response}")


def main():
    """Entry point."""
    import multiprocessing
    # Important: Set start method to 'spawn' for safe GUI/Multiprocessing interaction
    multiprocessing.set_start_method('spawn', force=True)
    
    # Initialize Qt application first (required for Qt widgets)
    app = QApplication(sys.argv)
    
    assistant = LivingAssistant()
    assistant.start()


if __name__ == "__main__":
    main()
