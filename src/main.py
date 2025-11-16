"""
ElderCare Agent - Main Application
Integrates all agents into a cohesive system.
"""

import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from .core.database import init_databases, Database
from .core.session_manager import SessionManager
from .agents.orchestrator import OrchestratorAgent
from .agents.communication import CommunicationAgent
from .agents.health import HealthAgent
from .agents.memory import MemoryAgent
from .agents.ui_generator import UIGeneratorAgent

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class ElderCareAgent:
    """
    Main ElderCare Agent application.
    Coordinates all specialist agents to help elderly users.
    """

    def __init__(self, user_id: str):
        """
        Initialize the ElderCare Agent system.

        Args:
            user_id: User identifier
        """
        self.user_id = user_id

        # Get API key
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        # Initialize database
        logger.info("Initializing database...")
        self.db = init_databases(seed_demo=True)

        # Initialize session manager
        logger.info("Initializing session manager...")
        self.session_manager = SessionManager()

        # Initialize all agents
        logger.info("Initializing agents...")

        self.orchestrator = OrchestratorAgent(
            user_id=user_id,
            api_key=self.api_key
        )

        self.communication_agent = CommunicationAgent(
            user_id=user_id,
            api_key=self.api_key,
            db=self.db
        )

        self.health_agent = HealthAgent(
            user_id=user_id,
            api_key=self.api_key,
            db=self.db
        )

        self.memory_agent = MemoryAgent(
            user_id=user_id,
            api_key=self.api_key,
            db=self.db
        )

        self.ui_generator = UIGeneratorAgent(
            api_key=self.api_key
        )

        # Create initial session
        self.current_session_id = self.session_manager.create_session(user_id)

        # Store session in memory agent's database
        self.memory_agent.create_session(context={"initial": "system_start"})

        logger.info(f"✅ ElderCare Agent initialized for user: {user_id}")
        logger.info(f"   Session ID: {self.current_session_id}")

    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user message through the agent system.

        Args:
            user_message: User's input message

        Returns:
            Response dict with agent response and UI
        """
        logger.info(f"Processing message: '{user_message}'")

        # Add to conversation history
        self.session_manager.add_to_conversation(
            self.current_session_id,
            "user",
            user_message
        )

        try:
            # CRITICAL: Check if we have a pending action awaiting confirmation
            pending_action = self.session_manager.get_pending_action(self.current_session_id)

            if pending_action:
                logger.info(f"Found pending action: {pending_action.get('type')}")
                # Check if user is confirming or canceling
                is_confirmation = self._is_confirmation(user_message)
                is_cancellation = self._is_cancellation(user_message)

                if is_confirmation:
                    logger.info("User confirmed pending action")
                    # Execute the pending action
                    response = await self._execute_pending_action(pending_action)
                    # Clear pending action
                    self.session_manager.clear_pending_action(self.current_session_id)
                    # Add to conversation and log
                    self.session_manager.add_to_conversation(
                        self.current_session_id,
                        "agent",
                        response.get("message", ""),
                        metadata={"confirmed_action": pending_action.get('type')}
                    )
                    return response

                elif is_cancellation:
                    logger.info("User canceled pending action")
                    # Clear pending action
                    self.session_manager.clear_pending_action(self.current_session_id)
                    return {
                        "success": True,
                        "message": "Okay, I've canceled that. What else can I help you with?",
                        "ui": None,
                        "task_type": "cancellation"
                    }
                else:
                    # User said something else - ask for clarification
                    logger.info("User response unclear for pending action")
                    return {
                        "success": False,
                        "message": pending_action.get('confirmation_prompt',
                                   "I didn't catch that. Could you please say yes or no?"),
                        "ui": None,
                        "task_type": "clarification_needed"
                    }

            # No pending action - proceed with normal orchestrator flow
            # Step 1: Orchestrator classifies intent
            logger.info("Step 1: Classifying intent...")
            intent_result = await self.orchestrator.process_message(user_message)

            intent = intent_result.get("intent")
            entities = intent_result.get("entities", {})
            confidence = intent_result.get("confidence", 0.0)
            
            # Log full intent result for debugging
            logger.info(f"  Intent: {intent} (confidence: {confidence})")
            if "error" in intent_result:
                logger.error(f"  Intent classification error: {intent_result['error']}")
            logger.debug(f"  Full intent result: {intent_result}")

            # Step 2: Route to appropriate agent
            logger.info("Step 2: Routing to specialist agent...")

            if intent == "VIDEO_CALL":
                response = await self._handle_video_call(user_message, entities)

            elif intent == "MEDICATION":
                response = await self._handle_medication(user_message, entities)

            elif intent == "APPOINTMENT":
                response = await self._handle_appointment(user_message, entities)

            elif intent == "GENERAL_HELP":
                response = await self._handle_general_help(user_message)

            elif intent == "UNCLEAR":
                response = await self._handle_unclear(user_message)

            else:
                response = {
                    "success": False,
                    "message": "I'm not sure how to help with that. Could you try rephrasing?",
                    "ui": None
                }

            # Step 3: Log interaction
            logger.info("Step 3: Logging interaction...")
            self.memory_agent.log_interaction(
                session_id=self.current_session_id,
                intent=intent,
                task_type=response.get("task_type", "unknown"),
                input_text=user_message,
                agent_response=response.get("message", ""),
                task_completed=response.get("success", False),
                metadata=response.get("metadata")
            )

            # Add to conversation history
            self.session_manager.add_to_conversation(
                self.current_session_id,
                "agent",
                response.get("message", ""),
                metadata={"intent": intent, "success": response.get("success")}
            )

            logger.info(f"✅ Message processed successfully")
            return response

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return {
                "success": False,
                "message": "I'm sorry, I encountered an error. Please try again.",
                "ui": None,
                "error": str(e)
            }

    async def _handle_video_call(self, user_message: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Handle video call request."""
        logger.info("Handling video call request...")

        # Use communication agent
        call_result = await self.communication_agent.handle_call_request(user_message)

        if not call_result["success"]:
            return {
                "success": False,
                "message": call_result.get("message", "I couldn't complete that call."),
                "ui": None,
                "task_type": "video_call"
            }

        # Check if this needs confirmation
        contact = call_result["contact"]
        contact_name = contact["contact_name"]
        relationship = contact.get("relationship", "contact")

        # Create friendly confirmation message
        confirmation_prompt = f"Is this {contact_name}"
        if relationship and relationship != "friend":
            confirmation_prompt += f" (your {relationship})"
        confirmation_prompt += f"? Phone: {contact.get('phone', 'N/A')}"

        # Set pending action for user to confirm
        self.session_manager.set_pending_action(
            self.current_session_id,
            {
                "type": "VIDEO_CALL",
                "data": {
                    "contact": contact,
                    "deep_link": call_result["deep_link"],
                    "platform": call_result["platform"],
                    "success_message": f"Perfect! Here's the button to call {contact_name}."
                },
                "confirmation_prompt": confirmation_prompt
            }
        )

        return {
            "success": True,
            "message": confirmation_prompt,
            "ui": None,  # UI will be shown after confirmation
            "task_type": "video_call_confirmation",
            "metadata": {
                "awaiting_confirmation": True,
                "contact": contact_name
            }
        }

    async def _handle_medication(self, user_message: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Handle medication request."""
        logger.info("Handling medication request...")

        # Use health agent
        med_result = await self.health_agent.handle_medication_request(user_message)

        action = med_result.get("action")

        if action == "TAKE_NOW":
            # Generate medication reminder UI
            due_meds = med_result.get("due_medications", [])

            if due_meds:
                # Show UI for first due medication
                ui = self.ui_generator.generate_medication_ui(due_meds[0])

                return {
                    "success": True,
                    "message": med_result.get("response", "Time for your medication!"),
                    "ui": ui,
                    "task_type": "medication_reminder",
                    "metadata": {"medication": due_meds[0]["medication_name"]}
                }
            else:
                return {
                    "success": True,
                    "message": "You don't have any medications due right now.",
                    "ui": None,
                    "task_type": "medication_info"
                }

        elif action == "INFO":
            # User asking what medications they take
            medications = med_result.get("medications", [])

            if medications:
                # Build a medication list message
                med_list = "\n".join([
                    f"• {med['medication_name']} - {med['dosage']} at {', '.join(med['times'])}"
                    for med in medications
                ])
                message = f"Here are your medications:\n\n{med_list}"
            else:
                message = "You don't have any medications scheduled."

            return {
                "success": True,
                "message": message,
                "ui": None,
                "task_type": "medication_info",
                "metadata": {"medication_count": len(medications)}
            }

        elif action == "CHECK":
            # User asking if they took medication today
            today_logs = med_result.get("today_logs", [])

            if today_logs:
                log_messages = []
                for log in today_logs:
                    status = "✅ Taken" if log['status'] == 'taken' else "⏭️ Skipped" if log['status'] == 'skipped' else "❌ Missed"
                    log_messages.append(f"{status} - {log['medication']}")

                message = f"Today's medications:\n\n{chr(10).join(log_messages)}"
            else:
                message = "I don't have any medication records for today yet."

            return {
                "success": True,
                "message": message,
                "ui": None,
                "task_type": "medication_check",
                "metadata": {"logs_count": len(today_logs)}
            }

        # For other actions or errors, return the response
        return {
            "success": action != "ERROR",
            "message": med_result.get("response", "I'm not sure what you need help with regarding your medications."),
            "ui": None,
            "task_type": "medication_info"
        }

    async def _handle_appointment(self, user_message: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Handle appointment request."""
        logger.info("Handling appointment request...")

        # Use Gemini to extract appointment details from the message
        import re
        from datetime import datetime, timedelta

        # Simple date/time extraction (you can enhance this with Gemini)
        message_lower = user_message.lower()

        # Try to extract date
        date = None
        time_str = None

        # Check for specific date formats
        if "november 25" in message_lower or "nov 25" in message_lower:
            date = datetime(2024, 11, 25)
        elif "tomorrow" in message_lower:
            date = datetime.now() + timedelta(days=1)
        elif "next week" in message_lower:
            date = datetime.now() + timedelta(days=7)

        # Check for time
        if "10:00" in message_lower or "10 am" in message_lower or "10am" in message_lower:
            time_str = "10:00"
        elif "morning" in message_lower:
            time_str = "10:00"  # Default morning time
        elif "afternoon" in message_lower:
            time_str = "14:00"  # Default afternoon time

        if date and time_str:
            # We have both date and time - create the appointment
            conn = self.db.get_connection("calendar")
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO appointments (user_id, title, doctor_name, date, time, duration_minutes, location, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.user_id,
                "Doctor Appointment",
                "Dr. Robert Smith",
                date.strftime("%Y-%m-%d"),
                time_str,
                30,
                "Smith Medical Center, 123 Main St",
                "scheduled"
            ))

            appointment_id = cursor.lastrowid
            conn.commit()
            conn.close()

            # Create appointment dict for UI
            appointment = {
                "appointment_id": appointment_id,
                "title": "Doctor Appointment",
                "doctor_name": "Dr. Robert Smith",
                "date": date.strftime("%B %d, %Y"),
                "time": time_str,
                "location": "Smith Medical Center, 123 Main St"
            }

            # Generate confirmation UI
            ui = self.ui_generator.generate_appointment_ui(appointment)

            return {
                "success": True,
                "message": f"Perfect! I've scheduled your appointment with Dr. Smith on {date.strftime('%B %d')} at {time_str}.",
                "ui": ui,
                "task_type": "appointment",
                "metadata": {"doctor": "Dr. Smith", "date": date.strftime("%Y-%m-%d")}
            }

        else:
            # Don't have enough info - ask for date/time
            if not date:
                return {
                    "success": True,
                    "message": "I can help you schedule a doctor appointment. When would you like to see Dr. Smith? For example, you can say 'November 25th' or 'tomorrow'.",
                    "ui": None,
                    "task_type": "appointment_scheduling"
                }
            elif not time_str:
                return {
                    "success": True,
                    "message": f"Great! What time would you like the appointment on {date.strftime('%B %d')}? For example, '10:00 AM' or 'morning'.",
                    "ui": None,
                    "task_type": "appointment_scheduling"
                }


    async def _handle_general_help(self, user_message: str) -> Dict[str, Any]:
        """Handle general help request."""
        logger.info("Handling general help...")

        if "hello" in user_message.lower() or "hi" in user_message.lower():
            response = await self.orchestrator.handle_greeting("day")
        else:
            response = "I can help you with: calling family, medication reminders, and doctor appointments. What would you like to do?"

        return {
            "success": True,
            "message": response,
            "ui": None,
            "task_type": "general_help"
        }

    async def _handle_unclear(self, user_message: str) -> Dict[str, Any]:
        """Handle unclear intent."""
        logger.info("Handling unclear intent...")

        response = await self.orchestrator.handle_confusion(user_message)

        return {
            "success": False,
            "message": response,
            "ui": None,
            "task_type": "unclear"
        }

    def _is_confirmation(self, user_message: str) -> bool:
        """
        Check if user message is a confirmation.

        Args:
            user_message: User's message

        Returns:
            True if message is a confirmation
        """
        message_lower = user_message.lower().strip()

        # Common confirmation patterns for elderly users
        confirmations = [
            "yes", "yeah", "yep", "yup", "sure", "ok", "okay",
            "correct", "right", "that's right", "that's correct",
            "he is", "she is", "that's him", "that's her",
            "go ahead", "do it", "please", "proceed"
        ]

        return any(conf in message_lower for conf in confirmations)

    def _is_cancellation(self, user_message: str) -> bool:
        """
        Check if user message is a cancellation.

        Args:
            user_message: User's message

        Returns:
            True if message is a cancellation
        """
        message_lower = user_message.lower().strip()

        # Common cancellation patterns
        cancellations = [
            "no", "nope", "nah", "cancel", "stop", "never mind",
            "not now", "later", "wrong", "that's wrong",
            "not him", "not her", "no thanks"
        ]

        return any(canc in message_lower for canc in cancellations)

    async def _execute_pending_action(self, pending_action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a pending action after user confirmation.

        Args:
            pending_action: The pending action dict

        Returns:
            Response dict with action result
        """
        action_type = pending_action.get("type")
        data = pending_action.get("data", {})

        logger.info(f"Executing pending action: {action_type}")

        if action_type == "VIDEO_CALL":
            # Generate UI for the confirmed call
            ui = self.ui_generator.generate_call_ui(
                contact=data.get("contact"),
                deep_link=data.get("deep_link")
            )

            return {
                "success": True,
                "message": data.get("success_message", "Great! Tap the button below to start the call."),
                "ui": ui,
                "task_type": "video_call",
                "metadata": {
                    "contact": data["contact"]["contact_name"],
                    "platform": data.get("platform", "whatsapp")
                }
            }

        elif action_type == "MEDICATION":
            # Generate medication UI
            medication = data.get("medication")
            ui = self.ui_generator.generate_medication_ui(medication)

            return {
                "success": True,
                "message": data.get("success_message", "Here's your medication reminder."),
                "ui": ui,
                "task_type": "medication_reminder",
                "metadata": {"medication": medication["medication_name"]}
            }

        elif action_type == "APPOINTMENT":
            # Generate appointment UI
            appointment = data.get("appointment")
            ui = self.ui_generator.generate_appointment_ui(appointment)

            return {
                "success": True,
                "message": data.get("success_message", "I've scheduled your appointment."),
                "ui": ui,
                "task_type": "appointment",
                "metadata": {"doctor": appointment.get("doctor_name")}
            }

        else:
            logger.warning(f"Unknown pending action type: {action_type}")
            return {
                "success": False,
                "message": "I'm sorry, something went wrong. Please try again.",
                "ui": None
            }

    def get_session_history(self) -> list:
        """Get conversation history for current session."""
        return self.session_manager.get_conversation_history(self.current_session_id)

    def end_session(self):
        """End the current session."""
        self.session_manager.end_session(self.current_session_id)
        self.memory_agent.end_session(self.current_session_id)
        logger.info("Session ended")


async def main():
    """Main function for testing."""
    import asyncio

    print("="*70)
    print(" ElderCare Agent - Full System Test")
    print("="*70)
    print()

    # Initialize the system
    print("🚀 Initializing ElderCare Agent...")
    agent = ElderCareAgent(user_id="margaret_thompson")
    print()

    # Test messages
    test_messages = [
        "Hello!",
        "Call my son",
        "Did I take my medication?",
        "I need to see the doctor"
    ]

    for message in test_messages:
        print("="*70)
        print(f"👤 USER: {message}")
        print("="*70)

        response = await agent.process_message(message)

        print(f"🤖 AGENT: {response['message']}")
        print(f"   Success: {response['success']}")
        print(f"   Task Type: {response.get('task_type')}")

        if response.get('ui'):
            print(f"   UI Template: {response['ui']['template_name']}")

        print()

    print("="*70)
    print("📊 Session Summary")
    print("="*70)
    history = agent.get_session_history()
    print(f"Total messages: {len(history)}")
    print()

    # End session
    agent.end_session()
    print("✅ Session ended")
    print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
