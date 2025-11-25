"""
Schedule Manager - Manages scheduled Google Chat reminders.

Handles CRUD operations for schedules and persists to JSON file.
"""

import json
import uuid
import threading
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path
from utils.logger import setup_logger

logger = setup_logger("ScheduleManager")


class Schedule:
    """Represents a scheduled reminder."""
    
    def __init__(self, time: str, message: str, schedule_id: Optional[str] = None, 
                 enabled: bool = True, days: Optional[List[str]] = None, 
                 created_at: Optional[str] = None):
        """
        Initialize a schedule.
        
        Args:
            time: Time in HH:MM format (24-hour)
            message: Message to send
            schedule_id: Unique identifier (auto-generated if None)
            enabled: Whether schedule is active
            days: Optional list of days (e.g., ["mon", "wed", "fri"]), None means daily
            created_at: Creation timestamp (auto-generated if None)
        """
        self.id = schedule_id or str(uuid.uuid4())
        self.time = time
        self.message = message
        self.enabled = enabled
        self.days = days
        self.created_at = created_at or datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "time": self.time,
            "message": self.message,
            "enabled": self.enabled,
            "days": self.days,
            "created_at": self.created_at
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Schedule':
        """Create Schedule from dictionary."""
        return Schedule(
            time=data["time"],
            message=data["message"],
            schedule_id=data["id"],
            enabled=data.get("enabled", True),
            days=data.get("days"),
            created_at=data.get("created_at")
        )
    
    def __str__(self) -> str:
        """String representation."""
        status = "✓" if self.enabled else "✗"
        days_str = f" ({', '.join(self.days)})" if self.days else " (daily)"
        return f"{status} {self.time}{days_str}: {self.message}"


class ScheduleManager:
    """Manages schedules with persistence to JSON file."""
    
    def __init__(self, schedules_file: str = "schedules.json"):
        """
        Initialize schedule manager.
        
        Args:
            schedules_file: Path to JSON file for storing schedules
        """
        self.schedules_file = Path(schedules_file)
        self.schedules: List[Schedule] = []
        self._lock = threading.Lock()
        self._load_schedules()
    
    def _load_schedules(self):
        """Load schedules from JSON file."""
        if not self.schedules_file.exists():
            logger.info(f"No existing schedules file found, starting fresh")
            return
        
        try:
            with open(self.schedules_file, 'r') as f:
                data = json.load(f)
                self.schedules = [Schedule.from_dict(s) for s in data.get("schedules", [])]
                logger.info(f"Loaded {len(self.schedules)} schedules from {self.schedules_file}")
        except Exception as e:
            logger.error(f"Error loading schedules: {e}")
            self.schedules = []
    
    def _save_schedules(self):
        """Save schedules to JSON file."""
        try:
            data = {
                "schedules": [s.to_dict() for s in self.schedules]
            }
            with open(self.schedules_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(self.schedules)} schedules to {self.schedules_file}")
        except Exception as e:
            logger.error(f"Error saving schedules: {e}")
    
    def add_schedule(self, time: str, message: str, days: Optional[List[str]] = None) -> str:
        """
        Add a new schedule.
        
        Args:
            time: Time in HH:MM format (24-hour)
            message: Message to send
            days: Optional list of days (e.g., ["mon", "wed", "fri"])
        
        Returns:
            Schedule ID
        """
        with self._lock:
            schedule = Schedule(time=time, message=message, days=days)
            self.schedules.append(schedule)
            self._save_schedules()
            logger.info(f"Added schedule: {schedule}")
            return schedule.id
    
    def remove_schedule(self, schedule_id: str) -> bool:
        """
        Remove a schedule by ID.
        
        Args:
            schedule_id: Schedule ID to remove
        
        Returns:
            True if removed, False if not found
        """
        with self._lock:
            original_count = len(self.schedules)
            self.schedules = [s for s in self.schedules if s.id != schedule_id]
            
            if len(self.schedules) < original_count:
                self._save_schedules()
                logger.info(f"Removed schedule: {schedule_id}")
                return True
            else:
                logger.warning(f"Schedule not found: {schedule_id}")
                return False
    
    def remove_schedule_by_time(self, time: str) -> bool:
        """
        Remove schedule(s) by time.
        
        Args:
            time: Time in HH:MM format
        
        Returns:
            True if any removed, False otherwise
        """
        with self._lock:
            original_count = len(self.schedules)
            self.schedules = [s for s in self.schedules if s.time != time]
            
            if len(self.schedules) < original_count:
                self._save_schedules()
                removed_count = original_count - len(self.schedules)
                logger.info(f"Removed {removed_count} schedule(s) at {time}")
                return True
            else:
                logger.warning(f"No schedules found at {time}")
                return False
    
    def list_schedules(self, enabled_only: bool = False) -> List[Schedule]:
        """
        List all schedules.
        
        Args:
            enabled_only: If True, only return enabled schedules
        
        Returns:
            List of schedules
        """
        with self._lock:
            if enabled_only:
                return [s for s in self.schedules if s.enabled]
            return self.schedules.copy()
    
    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """
        Get a specific schedule by ID.
        
        Args:
            schedule_id: Schedule ID
        
        Returns:
            Schedule if found, None otherwise
        """
        with self._lock:
            for schedule in self.schedules:
                if schedule.id == schedule_id:
                    return schedule
            return None
    
    def enable_schedule(self, schedule_id: str) -> bool:
        """Enable a schedule."""
        with self._lock:
            schedule = self.get_schedule(schedule_id)
            if schedule:
                schedule.enabled = True
                self._save_schedules()
                logger.info(f"Enabled schedule: {schedule_id}")
                return True
            return False
    
    def disable_schedule(self, schedule_id: str) -> bool:
        """Disable a schedule."""
        with self._lock:
            schedule = self.get_schedule(schedule_id)
            if schedule:
                schedule.enabled = False
                self._save_schedules()
                logger.info(f"Disabled schedule: {schedule_id}")
                return True
            return False
    
    def get_schedules_for_time(self, time: str, day_of_week: Optional[str] = None) -> List[Schedule]:
        """
        Get all enabled schedules for a specific time.
        
        Args:
            time: Time in HH:MM format
            day_of_week: Day of week (e.g., "mon", "tue", etc.)
        
        Returns:
            List of enabled schedules matching the time
        """
        with self._lock:
            matching = []
            for schedule in self.schedules:
                if not schedule.enabled:
                    continue
                if schedule.time != time:
                    continue
                
                # Check day of week if schedule has day restrictions
                if schedule.days:
                    if day_of_week and day_of_week.lower() in [d.lower() for d in schedule.days]:
                        matching.append(schedule)
                else:
                    # No day restrictions, runs daily
                    matching.append(schedule)
            
            return matching
