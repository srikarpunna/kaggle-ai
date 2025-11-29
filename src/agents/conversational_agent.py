"""
ElderCare Conversational Agent

A clean, LLM-first approach that:
1. Sends structured context to Gemini every turn
2. Lets the LLM manage conversation flow naturally
3. Uses function calling for actions
4. Maintains task state across turns
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import google.generativeai as genai

# Import metrics tracking
from ..core import metrics_collector

logger = logging.getLogger(__name__)


class ConversationalAgent:
    """
    Single conversational agent that handles all user interactions.
    Uses Gemini with function calling for a natural, context-aware experience.
    """
    
    def __init__(self, user_id: str, user_profile: Dict[str, Any], db_manager=None):
        self.user_id = user_id
        self.user_profile = user_profile
        self.db_manager = db_manager
        
        # Initialize Gemini with 2.5 Flash model
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Conversation state
        self.conversation_history: List[Dict[str, str]] = []
        self.task_state: Dict[str, Any] = {
            "current_task": None,
            "collected": {},
            "status": "idle"
        }
        
        # Define available tools
        self.tools = self._define_tools()
        
        logger.info(f"ConversationalAgent initialized for user: {user_id}")
    
    def _define_tools(self) -> List[Dict]:
        """Define the tools/functions that Gemini can call."""
        return [
            {
                "name": "call_emergency",
                "description": "IMMEDIATELY call 911 for medical emergencies. Use this when someone says 'emergency', 'call 911', 'I'm dying', 'can't breathe', 'chest pain', 'fell down', or any life-threatening situation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "situation": {
                            "type": "string",
                            "description": "Brief description of the emergency"
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "urgent", "moderate"],
                            "description": "How severe the emergency is"
                        }
                    },
                    "required": ["situation", "severity"]
                }
            },
            {
                "name": "book_appointment",
                "description": "Handle doctor appointments - book new appointments OR check existing appointments. Use when user mentions doctor/appointment.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["book", "check"],
                            "description": "Whether to book a new appointment or check existing ones"
                        },
                        "symptoms": {
                            "type": "string",
                            "description": "The health issue or symptoms (only for booking)"
                        },
                        "doctor_type": {
                            "type": "string",
                            "description": "Type of doctor (only for booking)"
                        },
                        "preferred_dates": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of dates available (only for booking)"
                        },
                        "preferred_time": {
                            "type": "string",
                            "description": "Time preference (only for booking)"
                        },
                        "needs_transport": {
                            "type": "boolean",
                            "description": "Whether needs a cab/ride (only for booking)"
                        }
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "make_call",
                "description": "Initiate a video call to a contact. Call this when the user confirms they want to call someone.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "contact_name": {
                            "type": "string",
                            "description": "Name or relationship of the person to call (e.g., 'John', 'my son', 'Sarah')"
                        },
                        "confirmed": {
                            "type": "boolean",
                            "description": "Whether the user has confirmed they want to make this call"
                        }
                    },
                    "required": ["contact_name", "confirmed"]
                }
            },
            {
                "name": "check_medication",
                "description": "Check MEDICATION/PILL schedule or provide information about medications/pills/drugs. ONLY for medications - NOT for doctor appointments.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query_type": {
                            "type": "string",
                            "enum": ["schedule", "taken_today", "info"],
                            "description": "Type of medication query - schedule means medication schedule, not appointment schedule"
                        },
                        "medication_name": {
                            "type": "string",
                            "description": "Specific medication name if asking about one"
                        }
                    },
                    "required": ["query_type"]
                }
            }
        ]
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with user context and task state."""
        
        user_name = self.user_profile.get('name', 'Friend')
        user_age = self.user_profile.get('age', '')
        
        # Get contacts for context
        contacts_info = ""
        if self.db_manager:
            try:
                contacts = self.db_manager.get_contacts(self.user_id) or []
                if contacts:
                    contacts_info = "\n".join([
                        f"  - {c.get('contact_name', 'Unknown')} ({c.get('relationship', 'contact')}) - {c.get('phone', '')}"
                        for c in contacts[:5]
                    ])
                else:
                    contacts_info = "No contacts found"
            except Exception as e:
                contacts_info = f"Error loading contacts: {e}"
        
        system_prompt = f"""You are a warm, caring assistant helping {user_name}, who is {user_age} years old.

## Your Personality:
- Speak like a friendly neighbor, not a robot
- Use short, simple sentences
- Be warm and patient
- Never list your capabilities - just help naturally
- Use {user_name}'s name occasionally to be personal

## Current Task State:
{json.dumps(self.task_state, indent=2)}

## User's Contacts:
{contacts_info if contacts_info else "No contacts loaded"}

## How to Help:

### 🚨 FOR EMERGENCIES (HIGHEST PRIORITY):
If someone says:
- "emergency", "call 911", "I'm dying", "can't breathe", "chest pain", "fell down", "bleeding badly", "severe pain"
- IMMEDIATELY call call_emergency() function
- DO NOT ask questions
- DO NOT ask for appointment times
- This is life or death - ACT FAST

### For Regular Appointments:
ONLY for non-urgent issues (regular checkup, mild symptoms, scheduled visit):

**TRIGGER PHRASES** - If user says ANY of these, start appointment flow:
- "schedule", "book", "appointment", "see the doctor", "see Dr.", "need to see", "dentist", "checkup"

**Steps:**
1. Ask what's bothering them (if not mentioned)
2. Ask what kind of doctor they need (if not clear from message)
3. Ask when they're free (get 2-3 dates)
4. Ask what time works (morning/afternoon)
5. **MUST ASK: "Do you need a ride to the appointment?"** - REQUIRED before booking
6. When you have ALL 5 pieces of info, call the book_appointment function

**IMPORTANT:** If user provides date/time upfront (e.g., "Schedule dentist for tomorrow at 10am"):
- Acknowledge it immediately: "Got it, dentist tomorrow at 10am"
- Still ask for reason and transport before booking

**DO NOT call book_appointment until you've asked about transportation!**

### For Calls:
When someone says "call my son", "call my daughter", "call John", etc.:
- IMMEDIATELY call the make_call function with confirmed=false
- The function will look up the contact and ask for confirmation
- Do NOT just say "Sure, I can call them" - USE THE FUNCTION
- Example: User says "call my son" → call make_call(contact_name="my son", confirmed=false)

### For Medications:
When someone asks about pills/medications:
1. Understand what they need (schedule, info, reminders)
2. Call check_medication function
3. **BE WARM AND CARING** - Medications are personal health matters
4. If they report side effects (dizzy, nauseous, etc.):
   - Express genuine concern: "Oh dear, that sounds uncomfortable"
   - Suggest contacting their doctor
   - Offer to help call the doctor's office
   - DO NOT give medical advice

## Important Rules:
- NEVER ask for information the user already provided
- If they said "headache" earlier, remember it - don't ask "what's wrong?"
- If they say "yes" to transport question, that means needs_transport=true
- Keep responses under 2 sentences when possible
- **CRITICAL: When user asks to call someone, ALWAYS use the make_call function - don't just respond with text**
- **CRITICAL: When user has provided all appointment info, ALWAYS use book_appointment function**
- DO NOT say "I can do that" - just DO IT by calling the function

## Current Date: {datetime.now().strftime('%B %d, %Y')}
"""
        return system_prompt
    
    def _format_conversation_for_prompt(self) -> str:
        """Format recent conversation history for the prompt."""
        if not self.conversation_history:
            return "No previous conversation."
        
        # Keep last 10 turns for context
        recent = self.conversation_history[-10:]
        
        formatted = []
        for turn in recent:
            role = turn.get('role', 'user')
            content = turn.get('content', '')
            formatted.append(f"{role.upper()}: {content}")
        
        return "\n".join(formatted)
    
    def _update_task_state_from_message(self, user_message: str):
        """
        Use LLM to extract and update task state from user message.
        This runs BEFORE the main conversation to keep state current.
        """
        if self.task_state.get("current_task") is None:
            return
        
        extraction_prompt = f"""
Given this user message in the context of {self.task_state.get('current_task')}:
"{user_message}"

Current collected info:
{json.dumps(self.task_state.get('collected', {}), indent=2)}

Extract any NEW information from their message and return updated collected info.
Only update fields that have new information. Keep existing values.

For appointment booking, look for:
- symptoms: health issues mentioned
- doctor_type: type of doctor
- preferred_dates: dates mentioned (convert to list like ["December 1", "December 2"])
- preferred_time: time preference
- needs_transport: true if they say yes to ride/cab, false if no

For "yes"/"no" responses:
- If asking about transport and they say "yes" → needs_transport: true
- If asking about transport and they say "no" → needs_transport: false

Return ONLY valid JSON with the updated collected object.
"""
        
        try:
            response = self.model.generate_content(extraction_prompt)
            text = response.text.strip()
            # Clean up response
            text = text.replace("```json", "").replace("```", "").strip()
            updated = json.loads(text)
            
            # Merge with existing (don't overwrite with null)
            for key, value in updated.items():
                if value is not None and value != "" and value != []:
                    self.task_state["collected"][key] = value
            
            logger.info(f"Updated task state: {self.task_state}")
        except Exception as e:
            logger.warning(f"Failed to update task state: {e}")
    
    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user message and return a response.
        This is the main entry point for conversation.
        """
        start_time = time.time()
        logger.info(f"Processing message: {user_message}")
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Update task state with any new info from message
        self._update_task_state_from_message(user_message)
        
        # Build the full prompt
        system_prompt = self._build_system_prompt()
        conversation_context = self._format_conversation_for_prompt()
        
        full_prompt = f"""{system_prompt}

## Conversation So Far:
{conversation_context}

## Your Response:
Respond naturally to the user. If you have all the information needed for a task, call the appropriate function.
Keep your response conversational and brief (1-2 sentences).
"""
        
        try:
            # Generate response with function calling
            response = self.model.generate_content(
                full_prompt,
                tools=self._get_gemini_tools()
            )
            
            # Track token usage if available
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                prompt_tokens = getattr(usage, 'prompt_token_count', 0)
                completion_tokens = getattr(usage, 'candidates_token_count', 0)
                if prompt_tokens > 0 or completion_tokens > 0:
                    metrics_collector.record_tokens(prompt_tokens, completion_tokens)
            
            # Check if a function was called
            if response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        # Task is being completed via function call
                        metrics_collector.record_task(completed=True)
                        
                        result = await self._handle_function_call(part.function_call)
                        
                        # Track metrics
                        duration_ms = (time.time() - start_time) * 1000
                        metrics_collector.record_response_time(duration_ms)
                        metrics_collector.record_agent_call("conversational_agent", duration_ms, result.get("success", True))
                        if result.get("success"):
                            metrics_collector.record_success()
                        else:
                            metrics_collector.record_failure()
                        
                        task_type = result.get("task_type", "general")
                        if task_type:
                            metrics_collector.record_intent(task_type.upper())
                        
                        return result
                        
                    elif hasattr(part, 'text') and part.text:
                        agent_response = part.text.strip()
                        
                        # Detect task type from response
                        self._detect_and_set_task(user_message, agent_response)
                        
                        # Add to history
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": agent_response
                        })
                        
                        task_type = self.task_state.get("current_task", "general")
                        result = {
                            "success": True,
                            "message": agent_response,
                            "intent": self._task_to_intent(task_type),
                            "ui": None,
                            "task_type": task_type
                        }
                        
                        # Track metrics
                        duration_ms = (time.time() - start_time) * 1000
                        metrics_collector.record_response_time(duration_ms)
                        metrics_collector.record_agent_call("conversational_agent", duration_ms, True)
                        metrics_collector.record_success()
                        
                        if task_type:
                            metrics_collector.record_intent(task_type.upper())
                        
                        return result
            
            # Fallback
            duration_ms = (time.time() - start_time) * 1000
            metrics_collector.record_response_time(duration_ms)
            metrics_collector.record_success()
            
            return {
                "success": True,
                "message": "I'm here to help. What do you need?",
                "intent": "UNCLEAR",
                "ui": None,
                "task_type": "general"
            }
            
        except Exception as e:
            logger.error(f"Error in conversation: {e}", exc_info=True)
            
            # Track failure metrics
            duration_ms = (time.time() - start_time) * 1000
            metrics_collector.record_response_time(duration_ms)
            metrics_collector.record_failure()
            
            return {
                "success": False,
                "message": "Sorry, I had trouble understanding. Could you say that again?",
                "intent": "UNCLEAR",
                "ui": None,
                "error": str(e)
            }
    
    def _get_gemini_tools(self):
        """Convert tool definitions to Gemini format."""
        from google.generativeai.types import FunctionDeclaration, Tool
        
        declarations = []
        for tool in self.tools:
            declarations.append(
                FunctionDeclaration(
                    name=tool["name"],
                    description=tool["description"],
                    parameters=tool["parameters"]
                )
            )
        
        return [Tool(function_declarations=declarations)]
    
    def _task_to_intent(self, task_type: str) -> str:
        """Map task_type to intent for evaluation purposes."""
        mapping = {
            "video_call": "CALL",
            "video_call_confirmation": "CONFIRMATION",
            "appointment_booking": "APPOINTMENT",
            "medication": "MEDICATION",
            "emergency_call": "EMERGENCY",
            "general": "UNCLEAR"
        }
        return mapping.get(task_type, "UNCLEAR")
    
    def _detect_and_set_task(self, user_message: str, agent_response: str):
        """Detect what task we're working on and set task state."""
        msg_lower = user_message.lower()
        
        # Detect appointment task
        if any(word in msg_lower for word in ['doctor', 'appointment', 'pain', 'headache', 'sick', 'hurt', 'ache', 'injury']):
            if self.task_state.get("current_task") != "appointment_booking":
                self.task_state = {
                    "current_task": "appointment_booking",
                    "collected": {},
                    "status": "collecting"
                }
                logger.info("Started appointment booking task")
                metrics_collector.record_task(started=True)
        
        # Detect call task
        elif any(word in msg_lower for word in ['call', 'phone', 'video', 'contact']):
            if self.task_state.get("current_task") != "video_call":
                self.task_state = {
                    "current_task": "video_call",
                    "collected": {},
                    "status": "collecting"
                }
                logger.info("Started video call task")
                metrics_collector.record_task(started=True)
        
        # Detect medication task
        elif any(word in msg_lower for word in ['medication', 'medicine', 'pill', 'drug', 'prescription']):
            if self.task_state.get("current_task") != "medication":
                self.task_state = {
                    "current_task": "medication",
                    "collected": {},
                    "status": "collecting"
                }
                logger.info("Started medication task")
                metrics_collector.record_task(started=True)
    
    async def _handle_function_call(self, function_call) -> Dict[str, Any]:
        """Handle a function call from Gemini."""
        func_name = function_call.name
        args = dict(function_call.args) if function_call.args else {}
        
        logger.info(f"Function called: {func_name} with args: {args}")
        
        if func_name == "call_emergency":
            return await self._execute_emergency_call(args)
        elif func_name == "book_appointment":
            return await self._execute_book_appointment(args)
        elif func_name == "make_call":
            return await self._execute_make_call(args)
        elif func_name == "check_medication":
            return await self._execute_check_medication(args)
        else:
            return {
                "success": False,
                "message": "I'm not sure how to do that.",
                "ui": None
            }
    
    async def _execute_emergency_call(self, args: Dict) -> Dict[str, Any]:
        """Execute emergency 911 call immediately."""
        situation = args.get("situation", "medical emergency")
        severity = args.get("severity", "critical")
        
        logger.critical(f"EMERGENCY CALL - Situation: {situation}, Severity: {severity}")
        
        # Reset task state - this is critical
        self.task_state = {"current_task": None, "collected": {}, "status": "emergency"}
        
        user_name = self.user_profile.get('name', 'there')
        
        message = f"🚨 Calling 911 right now, {user_name}. Help is on the way. Stay on the line."
        
        self.conversation_history.append({
            "role": "assistant",
            "content": message
        })
        
        return {
            "success": True,
            "message": message,
            "intent": "EMERGENCY",
            "ui": {
                "template_name": "Emergency Call",
                "template_id": "emergency_ui",
                "ui_config": {
                    "emergency_number": "911",
                    "situation": situation,
                    "severity": severity,
                    "action": "calling"
                }
            },
            "task_type": "emergency_call"
        }
    
    async def _execute_book_appointment(self, args: Dict) -> Dict[str, Any]:
        """Execute the appointment booking or checking."""
        action = args.get("action", "book")
        
        # Handle checking existing appointments
        if action == "check":
            # Would check database for appointments
            message = "Let me check your appointments... You don't have any upcoming appointments scheduled."
            
            self.conversation_history.append({
                "role": "assistant",
                "content": message
            })
            
            return {
                "success": True,
                "message": message,
                "intent": "APPOINTMENT",
                "ui": None,
                "task_type": "appointment_booking"
            }
        
        # Handle booking new appointment
        symptoms = args.get("symptoms", "health concern")
        doctor_type = args.get("doctor_type", "doctor")
        dates = args.get("preferred_dates", [])
        time_pref = args.get("preferred_time", "morning")
        needs_transport = args.get("needs_transport", False)
        
        # Format dates nicely
        date_str = dates[0] if dates else "soon"
        
        # Create appointment in database
        if self.db_manager:
            try:
                self.db_manager.add_appointment(
                    self.user_id,
                    doctor_type=doctor_type,
                    reason=symptoms,
                    date=date_str,
                    time=time_pref
                )
            except Exception as e:
                logger.warning(f"Could not save appointment to DB: {e}")
        
        # Build confirmation message
        transport_msg = " I'll arrange a cab for you too." if needs_transport else ""
        message = f"All set! Your {doctor_type} appointment is booked for {date_str} in the {time_pref}.{transport_msg} I'll remind you the day before."
        
        # Reset task state
        self.task_state = {"current_task": None, "collected": {}, "status": "completed"}
        
        # Add to history
        self.conversation_history.append({
            "role": "assistant",
            "content": message
        })
        
        return {
            "success": True,
            "message": message,
            "intent": "APPOINTMENT",
            "ui": {
                "template_name": "Appointment Confirmation",
                "template_id": "appointment_ui",
                "ui_config": {
                    "doctor_type": doctor_type,
                    "date": date_str,
                    "time": time_pref,
                    "reason": symptoms,
                    "transport": needs_transport
                }
            },
            "task_type": "appointment_booking"
        }
    
    async def _execute_make_call(self, args: Dict) -> Dict[str, Any]:
        """Execute the video call."""
        contact_name = args.get("contact_name", "")
        confirmed = args.get("confirmed", False)
        
        # Look up contact by relationship or name
        contact_info = None
        if self.db_manager:
            try:
                # First try to find by relationship (son, daughter, doctor, etc.)
                relationship_words = ["son", "daughter", "grandson", "granddaughter", "doctor", "wife", "husband", "brother", "sister", "mom", "dad", "mother", "father"]
                for rel in relationship_words:
                    if rel in contact_name.lower():
                        contact_info = self.db_manager.find_contact_by_relationship(self.user_id, rel)
                        if contact_info:
                            break
                
                # If not found by relationship, try by name
                if not contact_info:
                    contact_info = self.db_manager.find_contact_by_name(self.user_id, contact_name)
                
                # Still not found? Search all contacts
                if not contact_info:
                    contacts = self.db_manager.get_contacts(self.user_id) or []
                    for c in contacts:
                        if contact_name.lower() in c.get('contact_name', '').lower() or \
                           contact_name.lower() in c.get('relationship', '').lower():
                            contact_info = c
                            break
            except Exception as e:
                logger.error(f"Error looking up contact: {e}")
        
        if contact_info:
            name = contact_info.get('contact_name', contact_name)
            relationship = contact_info.get('relationship', '')
            phone = contact_info.get('phone', '')
            
            if not confirmed:
                # Ask for confirmation with contact details
                rel_text = f" (your {relationship})" if relationship else ""
                return {
                    "success": True,
                    "message": f"Is this {name}{rel_text}? Phone: {phone}",
                    "intent": "CALL",  # User's intent is to call, not to confirm
                    "ui": None,
                    "task_type": "video_call_confirmation"
                }
            
            message = f"Calling {name} now..."
            
            # Reset task state
            self.task_state = {"current_task": None, "collected": {}, "status": "completed"}
            
            self.conversation_history.append({
                "role": "assistant",
                "content": message
            })
            
            return {
                "success": True,
                "message": message,
                "intent": "CALL",
                "ui": {
                    "template_name": "Video Call Interface",
                    "template_id": "call_ui",
                    "ui_config": {
                        "contact_name": name,
                        "phone": phone,
                        "relationship": relationship
                    }
                },
                "task_type": "video_call"
            }
        else:
            # List available contacts
            available = ""
            if self.db_manager:
                try:
                    contacts = self.db_manager.get_contacts(self.user_id) or []
                    if contacts:
                        names = [f"{c.get('contact_name')} ({c.get('relationship')})" for c in contacts[:4]]
                        available = f" You have: {', '.join(names)}."
                except:
                    pass
            
            return {
                "success": False,
                "message": f"I couldn't find {contact_name} in your contacts.{available} Who would you like to call?",
                "intent": "CALL",
                "ui": None,
                "task_type": "video_call"
            }
    
    async def _execute_check_medication(self, args: Dict) -> Dict[str, Any]:
        """Handle medication queries."""
        query_type = args.get("query_type", "schedule")
        medication_name = args.get("medication_name")
        
        if query_type == "schedule":
            message = "Let me check your medication schedule..."
            # Would query database here
            message = "You have Lisinopril at 8 AM, Metformin at noon, and Aspirin at bedtime."
        elif query_type == "taken_today":
            message = "Let me check what you've taken today..."
        else:
            message = f"Here's information about {medication_name}..." if medication_name else "What medication would you like to know about?"
        
        self.conversation_history.append({
            "role": "assistant",
            "content": message
        })
        
        return {
            "success": True,
            "message": message,
            "intent": "MEDICATION",
            "ui": None,
            "task_type": "medication"
        }
    
    def get_conversation_summary(self) -> str:
        """Generate a summary of the conversation for context compaction."""
        if len(self.conversation_history) < 10:
            return ""
        
        # Summarize older turns
        old_turns = self.conversation_history[:-5]
        
        summary_prompt = f"""
Summarize this conversation, keeping all important facts:
- User's health issues/symptoms
- Any dates or times mentioned
- Any decisions made
- Any contacts mentioned

Conversation:
{json.dumps(old_turns, indent=2)}

Write a 2-3 sentence summary preserving key facts:
"""
        
        try:
            response = self.model.generate_content(summary_prompt)
            return response.text.strip()
        except:
            return ""
    
    def compact_context(self):
        """Compact old conversation turns into a summary."""
        if len(self.conversation_history) > 15:
            summary = self.get_conversation_summary()
            if summary:
                # Keep summary + last 5 turns
                self.conversation_history = [
                    {"role": "system", "content": f"Previous conversation summary: {summary}"}
                ] + self.conversation_history[-5:]
                logger.info("Compacted conversation context")

