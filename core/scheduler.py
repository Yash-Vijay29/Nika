"""
Scheduler - Background worker for triggering scheduled Google Chat messages.

Runs in a separate thread, checking every minute for scheduled messages to send.
"""

import time
import threading
from datetime import datetime
from typing import Optional, Set
from utils.logger import setup_logger
from core.schedule_manager import ScheduleManager
from actions.chat import GoogleChatMessenger

logger = setup_logger("Scheduler")


class Scheduler:
    """Background worker that triggers scheduled messages."""
    
    def __init__(self, schedule_manager: ScheduleManager, chat_messenger: GoogleChatMessenger, 
                 check_interval: int = 60):
        """
        Initialize scheduler.
        
        Args:
            schedule_manager: ScheduleManager instance
            chat_messenger: GoogleChatMessenger instance
            check_interval: How often to check for scheduled messages (seconds)
        """
        self.schedule_manager = schedule_manager
        self.chat_messenger = chat_messenger
        self.check_interval = check_interval
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Track already-sent schedules for this minute to prevent duplicates
        self._sent_this_minute: Set[str] = set()
        self._current_minute: Optional[str] = None
    
    def start(self):
        """Start the scheduler worker thread."""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler worker thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Scheduler stopped")
    
    def _run(self):
        """Main scheduler loop."""
        logger.info(f"Scheduler worker running, checking every {self.check_interval} seconds")
        
        while self.running:
            try:
                self._check_and_trigger_schedules()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(self.check_interval)
    
    def _check_and_trigger_schedules(self):
        """Check current time and trigger any matching schedules."""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_day = now.strftime("%a").lower()  # mon, tue, wed, etc.
        
        # Reset sent tracking if we're in a new minute
        if self._current_minute != current_time:
            self._current_minute = current_time
            self._sent_this_minute.clear()
            logger.debug(f"Checking schedules for {current_time} ({current_day})")
        
        # Get schedules for this time
        schedules = self.schedule_manager.get_schedules_for_time(current_time, current_day)
        
        if not schedules:
            return
        
        logger.info(f"Found {len(schedules)} schedule(s) for {current_time}")
        
        # Send messages for each schedule
        for schedule in schedules:
            # Skip if already sent this minute
            if schedule.id in self._sent_this_minute:
                continue
            
            # Send the message
            success = self.chat_messenger.send_message(schedule.message)
            
            if success:
                self._sent_this_minute.add(schedule.id)
                logger.info(f"Triggered schedule: {schedule}")
            else:
                logger.error(f"Failed to send scheduled message: {schedule}")
