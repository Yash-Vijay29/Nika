from openai import OpenAI
from datetime import datetime, timedelta
from typing import Optional
from utils.logger import setup_logger
import json

logger = setup_logger("Brain")


class Brain:
    """The decision-making center using OpenAI's GPT LLM."""
    
    def __init__(self, api_key: str, state, memory, voice_engine, chat_messenger):
        self.client = OpenAI(api_key=api_key)
        self.model = 'gpt-4o-mini'  # GPT-4o-mini supports vision and is cost-effective
        self.state = state
        self.memory = memory
        self.voice = voice_engine
        self.chat = chat_messenger
        self.schedule_manager = None  # Will be set by main.py after initialization
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the LLM."""
        return """You are an AI assistant living inside a laptop, acting as a caring companion and productivity coach.

Your personality:
- Warm, encouraging, and slightly playful
- Genuine interest in the user's wellbeing and goals
- Non-judgmental but gently nudging towards productivity
- Brief and conversational (1-2 sentences max)

Your capabilities:
- Monitor user presence via camera
- See what's on their screen
- Speak to them via voice
- Send messages via Google Chat

Your role:
- Check if user is staying on track with their plans
- Offer encouragement when they're working hard
- Gently remind them if they're distracted
- Celebrate their wins

Keep responses SHORT and natural, like a friend casually checking in."""
    
    def should_speak(self) -> bool:
        """Determine if enough time has passed since last speech."""
        if not self.state.last_spoke:
            return True
        time_since_spoke = datetime.now() - self.state.last_spoke
        return time_since_spoke > timedelta(minutes=15)
    
    def should_message(self) -> bool:
        """Determine if enough time has passed since last message."""
        if not self.state.last_chat_message:
            return True
        time_since_message = datetime.now() - self.state.last_chat_message
        return time_since_message > timedelta(hours=2)
    
    def analyze_and_decide(self, screenshot_base64: Optional[str] = None) -> dict:
        """Analyze current state and decide what action to take."""
        snapshot = self.state.get_snapshot()
        active_plans = self.memory.get_active_plans()
        
        # Don't do anything if user is not present
        if not snapshot["user_present"]:
            return {"action": "wait", "reason": "User not present"}
        
        # Build context for LLM
        context_parts = [
            f"Current time: {datetime.now().strftime('%H:%M')}",
            f"User present: {snapshot['user_present']}",
            f"Current activity: {snapshot['current_activity']}",
        ]
        
        if active_plans:
            plans_text = "\n".join([f"- {p['plan']}" for p in active_plans[:3]])
            context_parts.append(f"\nUser's active goals:\n{plans_text}")
        else:
            context_parts.append("\nNo active goals set by user.")
        
        if snapshot['last_spoke']:
            mins_since_spoke = (datetime.now() - snapshot['last_spoke']).seconds // 60
            context_parts.append(f"Last spoke {mins_since_spoke} minutes ago")
        
        context = "\n".join(context_parts)
        
        # Build prompt for LLM
        prompt = f"""{context}

Based on this, should I:
1. SPEAK - Say something encouraging via voice (only if >15 mins since last speech)
2. MESSAGE - Send a Google Chat message (only if >2 hours since last message)
3. WAIT - Do nothing for now

Respond in JSON format:
{{"action": "speak|message|wait", "content": "what to say if action is speak or message"}}"""
        
        try:
            # Prepare messages for API call
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": []}
            ]
            
            # Add text content
            messages[1]["content"].append({
                "type": "text",
                "text": prompt
            })
            
            # Add screenshot if available
            if screenshot_base64:
                messages[1]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{screenshot_base64}",
                        "detail": "low"  # Use low detail to reduce costs
                    }
                })
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=150
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            action = result.get("action", "wait").lower()
            content = result.get("content", "")
            
            # Validate action against timing constraints
            if action == "speak" and self.should_speak():
                return {"action": "speak", "content": content}
            elif action == "message" and self.should_message():
                return {"action": "message", "content": content}
            else:
                return {"action": "wait", "reason": "No compelling reason to interrupt"}
            
        except Exception as e:
            logger.error(f"Error in analysis: {e}")
            return {"action": "wait", "reason": f"Error: {e}"}
    
    def execute_decision(self, decision: dict):
        """Execute the decided action."""
        action = decision.get("action")
        
        if action == "speak":
            content = decision.get("content", "")
            self.voice.speak(content)
            self.state.update_interaction("voice")
            self.memory.add_interaction("voice", content)
            logger.info(f"Spoke: {content}")
        
        elif action == "message":
            content = decision.get("content", "")
            self.chat.send_message(content)
            self.state.update_interaction("chat")
            self.memory.add_interaction("chat", content)
            logger.info(f"Sent message: {content}")
        
        elif action == "wait":
            logger.debug(f"Waiting: {decision.get('reason', 'No reason')}")
    
    def handle_user_speech(self, user_text: str):
        """Handle user speech input and generate a response."""
        try:
            snapshot = self.state.get_snapshot()
            active_plans = self.memory.get_active_plans()
            
            # Build context
            context_parts = [f"Current time: {datetime.now().strftime('%H:%M')}"]
            if active_plans:
                plans_text = "\n".join([f"- {p['plan']}" for p in active_plans[:3]])
                context_parts.append(f"\nUser's active goals:\n{plans_text}")
            
            context = "\n".join(context_parts)
            
            # Generate response using OpenAI
            messages = [
                {"role": "system", "content": self.system_prompt + f"\n\nContext:\n{context}"},
                {"role": "user", "content": user_text}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=100
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Speak the response
            self.voice.speak(response_text)
            self.state.update_interaction("voice")
            self.memory.add_interaction("user_speech", user_text)
            self.memory.add_interaction("voice", response_text)
            logger.info(f"User: {user_text} | Response: {response_text}")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error handling user speech: {e}")
            return "Sorry, I encountered an error processing your request."
    
    def _detect_schedule_command(self, text: str) -> Optional[str]:
        """Detect if user is trying to manage schedules."""
        text_lower = text.lower()
        
        # Add schedule commands
        add_keywords = ["add reminder", "create reminder", "remind me", "set reminder", 
                       "schedule reminder", "new reminder", "add schedule"]
        if any(kw in text_lower for kw in add_keywords):
            return "add"
        
        # List schedule commands
        list_keywords = ["list reminder", "show reminder", "what reminder", "my reminder", 
                        "list schedule", "show schedule", "what schedule"]
        if any(kw in text_lower for kw in list_keywords):
            return "list"
        
        # Remove schedule commands
        remove_keywords = ["remove reminder", "delete reminder", "cancel reminder", 
                          "remove schedule", "delete schedule", "cancel schedule"]
        if any(kw in text_lower for kw in remove_keywords):
            return "remove"
        
        return None
    
    def _parse_time_from_text(self, text: str) -> Optional[str]:
        """Parse time from natural language text."""
        import re
        
        # Pattern for times like "6 AM", "06:00", "6:30 PM", etc.
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)?',  # 6:00, 6:30 PM
            r'(\d{1,2})\s*(am|pm)',            # 6 AM, 12 PM
        ]
        
        text_lower = text.lower()
        
        for pattern in time_patterns:
            match = re.search(pattern, text_lower)
            if match:
                if ':' in match.group(0):
                    # Format: HH:MM
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    am_pm = match.group(3) if len(match.groups()) >= 3 else None
                else:
                    # Format: H AM/PM
                    hour = int(match.group(1))
                    minute = 0
                    am_pm = match.group(2)
                
                # Convert to 24-hour format
                if am_pm:
                    if am_pm == 'pm' and hour != 12:
                        hour += 12
                    elif am_pm == 'am' and hour == 12:
                        hour = 0
                
                return f"{hour:02d}:{minute:02d}"
        
        return None
    
    def _parse_message_from_text(self, text: str, time_str: str = None) -> str:
        """Extract the message content from schedule command."""
        import re
        
        # Remove time portion
        if time_str:
            text = re.sub(r'\d{1,2}:\d{2}\s*(am|pm)?', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\d{1,2}\s*(am|pm)', '', text, flags=re.IGNORECASE)
        
        # Remove command keywords
        keywords = ["add reminder", "create reminder", "remind me", "set reminder", 
                   "schedule reminder", "new reminder", "saying", "say", "to", "at"]
        
        for kw in keywords:
            text = re.sub(r'\b' + kw + r'\b', '', text, flags=re.IGNORECASE)
        
        # Clean up
        text = text.strip()
        
        # Default message if nothing specified
        if not text or len(text) < 3:
            text = "you up?"
        
        return text
    
    def _handle_add_schedule(self, text: str):
        """Handle adding a new schedule from voice command."""
        if not self.schedule_manager:
            self.voice.speak("Schedule manager is not available.")
            return
        
        # Parse time
        time_str = self._parse_time_from_text(text)
        if not time_str:
            self.voice.speak("I couldn't understand the time. Please say it like '6 AM' or '2:30 PM'.")
            return
        
        # Parse message
        message = self._parse_message_from_text(text, time_str)
        
        # Add schedule
        try:
            schedule_id = self.schedule_manager.add_schedule(time_str, message)
            
            # Convert time to 12-hour format for speaking
            hour, minute = map(int, time_str.split(':'))
            am_pm = "AM" if hour < 12 else "PM"
            display_hour = hour if hour <= 12 else hour - 12
            if display_hour == 0:
                display_hour = 12
            
            time_spoken = f"{display_hour}:{minute:02d} {am_pm}" if minute > 0 else f"{display_hour} {am_pm}"
            
            response = f"Got it! I'll message you at {time_spoken} every day saying '{message}'."
            self.voice.speak(response)
            logger.info(f"Added schedule via voice: {time_str} - {message}")
            
        except Exception as e:
            logger.error(f"Error adding schedule: {e}")
            self.voice.speak("Sorry, I had trouble adding that reminder.")
    
    def _handle_list_schedules(self):
        """Handle listing current schedules."""
        if not self.schedule_manager:
            self.voice.speak("Schedule manager is not available.")
            return
        
        schedules = self.schedule_manager.list_schedules(enabled_only=True)
        
        if not schedules:
            self.voice.speak("You don't have any active reminders set up.")
            return
        
        # Build response
        if len(schedules) == 1:
            s = schedules[0]
            hour, minute = map(int, s.time.split(':'))
            am_pm = "AM" if hour < 12 else "PM"
            display_hour = hour if hour <= 12 else hour - 12
            if display_hour == 0:
                display_hour = 12
            time_spoken = f"{display_hour}:{minute:02d} {am_pm}" if minute > 0 else f"{display_hour} {am_pm}"
            
            response = f"You have 1 reminder: {time_spoken} - {s.message}"
        else:
            response = f"You have {len(schedules)} reminders: "
            for i, s in enumerate(schedules[:3]):  # Limit to first 3 to avoid long speech
                hour, minute = map(int, s.time.split(':'))
                am_pm = "AM" if hour < 12 else "PM"
                display_hour = hour if hour <= 12 else hour - 12
                if display_hour == 0:
                    display_hour = 12
                time_spoken = f"{display_hour}:{minute:02d} {am_pm}" if minute > 0 else f"{display_hour} {am_pm}"
                
                response += f"{time_spoken} - {s.message}"
                if i < min(len(schedules), 3) - 1:
                    response += ", "
        
        self.voice.speak(response)
    
    def _handle_remove_schedule(self, text: str):
        """Handle removing a schedule."""
        if not self.schedule_manager:
            self.voice.speak("Schedule manager is not available.")
            return
        
        # Try to parse time from text
        time_str = self._parse_time_from_text(text)
        
        if time_str:
            # Remove by time
            success = self.schedule_manager.remove_schedule_by_time(time_str)
            if success:
                hour, minute = map(int, time_str.split(':'))
                am_pm = "AM" if hour < 12 else "PM"
                display_hour = hour if hour <= 12 else hour - 12
                if display_hour == 0:
                    display_hour = 12
                time_spoken = f"{display_hour}:{minute:02d} {am_pm}" if minute > 0 else f"{display_hour} {am_pm}"
                
                self.voice.speak(f"Removed the {time_spoken} reminder.")
            else:
                self.voice.speak("I couldn't find a reminder at that time.")
        else:
            self.voice.speak("I couldn't understand which reminder to remove. Please specify the time.")
    
    def handle_user_speech(self, user_text: str):
        """Handle user speech input and generate a response."""
        try:
            # Check if this is a schedule management command
            schedule_command = self._detect_schedule_command(user_text)
            
            if schedule_command == "add":
                self._handle_add_schedule(user_text)
                return "Schedule added"
            elif schedule_command == "list":
                self._handle_list_schedules()
                return "Listed schedules"
            elif schedule_command == "remove":
                self._handle_remove_schedule(user_text)
                return "Schedule removed"
            
            # Otherwise, handle as normal conversation
            snapshot = self.state.get_snapshot()
            active_plans = self.memory.get_active_plans()
            
            # Build context
            context_parts = [f"Current time: {datetime.now().strftime('%H:%M')}"]
            if active_plans:
                plans_text = "\n".join([f"- {p['plan']}" for p in active_plans[:3]])
                context_parts.append(f"\nUser's active goals:\n{plans_text}")
            
            context = "\n".join(context_parts)
            
            # Generate response using OpenAI
            messages = [
                {"role": "system", "content": self.system_prompt + f"\n\nContext:\n{context}"},
                {"role": "user", "content": user_text}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=100
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Speak the response
            self.voice.speak(response_text)
            self.state.update_interaction("voice")
            self.memory.add_interaction("user_speech", user_text)
            self.memory.add_interaction("voice", response_text)
            logger.info(f"User: {user_text} | Response: {response_text}")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error handling user speech: {e}")
            return "Sorry, I encountered an error processing your request."
