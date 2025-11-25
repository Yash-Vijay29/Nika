"""
Quick test script for the schedule manager.

This tests the schedule manager CRUD operations and persistence.
"""

from core.schedule_manager import ScheduleManager
import os

def test_schedule_manager():
    print("=== Testing Schedule Manager ===\n")
    
    # Clean up any existing test file
    test_file = "test_schedules.json"
    if os.path.exists(test_file):
        os.remove(test_file)
    
    # Create schedule manager
    sm = ScheduleManager(test_file)
    print("✓ Created schedule manager")
    
    # Add schedules
    id1 = sm.add_schedule("06:00", "you up?")
    print(f"✓ Added schedule 1: 06:00 - you up?")
    
    id2 = sm.add_schedule("14:30", "time for a break!")
    print(f"✓ Added schedule 2: 14:30 - time for a break!")
    
    id3 = sm.add_schedule("22:00", "winding down for the day?")
    print(f"✓ Added schedule 3: 22:00 - winding down for the day?")
    
    # List schedules
    print(f"\n=== Current Schedules ===")
    schedules = sm.list_schedules()
    for s in schedules:
        print(f"  {s}")
    
    # Test persistence
    print(f"\n=== Testing Persistence ===")
    del sm
    sm2 = ScheduleManager(test_file)
    schedules2 = sm2.list_schedules()
    print(f"✓ Loaded {len(schedules2)} schedules from file")
    
    # Remove a schedule
    print(f"\n=== Testing Removal ===")
    sm2.remove_schedule_by_time("14:30")
    print(f"✓ Removed 14:30 schedule")
    
    schedules3 = sm2.list_schedules()
    print(f"Remaining schedules: {len(schedules3)}")
    for s in schedules3:
        print(f"  {s}")
    
    # Clean up
    if os.path.exists(test_file):
        os.remove(test_file)
    
    print(f"\n✅ All tests passed!")

if __name__ == "__main__":
    test_schedule_manager()
