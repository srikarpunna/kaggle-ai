"""
ElderCare Agent - Main Application

Clean, LLM-first architecture that:
1. Uses a single ConversationalAgent for all interactions
2. Lets Gemini manage conversation flow naturally
3. Uses function calling for actions
4. Maintains structured task state across turns
"""

import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from .core.database import init_databases, Database
from .core.session_manager import SessionManager
from .agents.conversational_agent import ConversationalAgent
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
    Uses a clean, LLM-first architecture with ConversationalAgent.
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

        # Get or create user profile
        user_profile = self._get_user_profile(user_id)

        # Initialize the single ConversationalAgent
        logger.info("Initializing conversational agent...")
        self.agent = ConversationalAgent(
            user_id=user_id,
            user_profile=user_profile,
            db_manager=self.db
        )

        # Memory agent for logging (optional)
        self.memory_agent = MemoryAgent(
            user_id=user_id,
            api_key=self.api_key,
            db=self.db
        )

        # UI generator for rich responses
        self.ui_generator = UIGeneratorAgent(
            api_key=self.api_key
        )

        # Create initial session
        self.current_session_id = self.session_manager.create_session(user_id)
        self.memory_agent.create_session(context={"initial": "system_start"})

        logger.info(f"✅ ElderCare Agent initialized for user: {user_id}")
        logger.info(f"   Session ID: {self.current_session_id}")

    def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile from database or return defaults."""
        try:
            if self.db:
                profile = self.db.get_user_profile(user_id)
                if profile:
                    return profile
        except:
            pass
        
        # Default profile
        return {
            "name": "Friend",
            "age": 70,
            "user_id": user_id
        }
    
    def update_user_profile(self, name: str, age: int):
        """Update user profile (called after onboarding)."""
        self.agent.user_profile = {
            "name": name,
            "age": age,
            "user_id": self.user_id
        }
        logger.info(f"Updated user profile: {name}, {age}")

    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user message through the conversational agent.
        
        This is the clean, LLM-first approach:
        1. Send message to ConversationalAgent
        2. Agent maintains context and task state internally
        3. Agent uses function calling when ready to execute actions
        """
        logger.info(f"Processing message: '{user_message}'")

        try:
            # Delegate to the conversational agent - it handles everything
            response = await self.agent.process_message(user_message)

            # Log interaction for memory/analytics
            self.memory_agent.log_interaction(
                session_id=self.current_session_id,
                intent=response.get("task_type", "general"),
                task_type=response.get("task_type", "unknown"),
                input_text=user_message,
                agent_response=response.get("message", ""),
                task_completed=response.get("success", False),
                metadata=response.get("metadata")
            )

            # Compact context if conversation is getting long
            self.agent.compact_context()

            logger.info(f"✅ Message processed successfully")
            return response

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return {
                "success": False,
                "message": "Sorry, I had trouble with that. Could you say it again?",
                "ui": None,
                "error": str(e)
            }

    def get_session_history(self) -> list:
        """Get conversation history for current session."""
        return self.agent.conversation_history

    def get_task_state(self) -> Dict[str, Any]:
        """Get current task state from agent."""
        return self.agent.task_state

    def end_session(self):
        """End the current session."""
        self.session_manager.end_session(self.current_session_id)
        self.memory_agent.end_session(self.current_session_id)
        logger.info("Session ended")


async def main():
    """Main function for testing."""
    import asyncio

    print("="*70)
    print(" ElderCare Agent - Clean Architecture Test")
    print("="*70)
    print()

    # Initialize the system
    print("🚀 Initializing ElderCare Agent...")
    agent = ElderCareAgent(user_id="margaret_thompson")
    
    # Update with test profile
    agent.update_user_profile("Alex", 55)
    print()

    # Test conversation flow - full appointment booking
    test_messages = [
        "Hello!",
        "I need to see a doctor",
        "I have a bad headache and throat pain",
        "general practitioner",
        "December 1st or 2nd",
        "morning works",
        "yes, I need a ride"
    ]

    for message in test_messages:
        print("="*70)
        print(f"👤 USER: {message}")
        print("="*70)

        response = await agent.process_message(message)

        print(f"🤖 AGENT: {response['message']}")
        print(f"   Success: {response['success']}")
        print(f"   Task Type: {response.get('task_type')}")
        print(f"   Task State: {agent.get_task_state()}")

        if response.get('ui'):
            print(f"   UI Template: {response['ui'].get('template_name')}")

        print()

    print("="*70)
    print("✅ Test completed")
    print("="*70)

    # End session
    agent.end_session()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
