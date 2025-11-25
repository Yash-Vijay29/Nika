import json
import os
from datetime import datetime
from typing import List, Dict, Any


class Memory:
    """Simple JSON-based memory system for the assistant."""
    
    def __init__(self, memory_file: str = "memory.json"):
        self.memory_file = memory_file
        self.data = self._load()
    
    def _load(self) -> dict:
        """Load memory from file."""
        if os.path.exists(self.memory_file):
            with open(self.memory_file, 'r') as f:
                return json.load(f)
        return {
            "user_plans": [],
            "interaction_history": [],
            "user_preferences": {}
        }
    
    def save(self):
        """Save memory to file."""
        with open(self.memory_file, 'w') as f:
            json.dump(self.data, f, indent=2, default=str)
    
    def add_plan(self, plan: str):
        """Add a user plan/goal."""
        self.data["user_plans"].append({
            "plan": plan,
            "created_at": datetime.now().isoformat(),
            "completed": False
        })
        self.save()
    
    def complete_plan(self, plan_index: int):
        """Mark a plan as completed."""
        if 0 <= plan_index < len(self.data["user_plans"]):
            self.data["user_plans"][plan_index]["completed"] = True
            self.data["user_plans"][plan_index]["completed_at"] = datetime.now().isoformat()
            self.save()
    
    def get_active_plans(self) -> List[Dict[str, Any]]:
        """Get all active (incomplete) plans."""
        return [p for p in self.data["user_plans"] if not p["completed"]]
    
    def add_interaction(self, interaction_type: str, content: str):
        """Log an interaction."""
        self.data["interaction_history"].append({
            "type": interaction_type,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        # Keep only last 100 interactions
        if len(self.data["interaction_history"]) > 100:
            self.data["interaction_history"] = self.data["interaction_history"][-100:]
        self.save()
    
    def get_recent_interactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent interactions."""
        return self.data["interaction_history"][-limit:]
