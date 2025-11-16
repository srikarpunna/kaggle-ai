"""
ElderCare Agent - Orchestrator Agent
Main coordinator that understands user intent and routes to specialized agents.
"""

import logging
import json
from typing import Dict, Any, Optional, List
import google.generativeai as genai

from ..core.config_loader import get_config, load_user_profile

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Orchestrator Agent powered by Gemini.
    Understands user intent and coordinates with specialized agents.
    """

    def __init__(self, user_id: str, api_key: str):
        self.user_id = user_id
        self.config = get_config().get_agent_config("orchestrator")

        # Load user profile
        try:
            self.user_profile = load_user_profile(user_id)
        except FileNotFoundError:
            logger.warning(f"User profile not found for {user_id}, using defaults")
            self.user_profile = {"personal_info": {"full_name": user_id, "age": 70}}

        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=self.config.model,
            generation_config={
                "temperature": self.config.temperature,
                "max_output_tokens": self.config.max_tokens,
            }
        )

        # System prompt
        self.system_prompt = self._build_system_prompt()

        logger.info(f"Orchestrator Agent initialized for user: {user_id}")

    def _build_system_prompt(self) -> str:
        """Build the system prompt with user context."""
        user_name = self.user_profile.get("personal_info", {}).get("full_name", "User")
        user_age = self.user_profile.get("personal_info", {}).get("age", 70)

        prompt_template = get_config().get_prompt(
            "system",
            "orchestrator",
            "base",
            user_name=user_name,
            user_age=user_age
        )

        return prompt_template

    async def process_message(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message and determine intent.

        Args:
            user_message: The user's input message
            context: Optional conversation context

        Returns:
            Dict containing intent, entities, and routing information
        """
        logger.info(f"Processing message: {user_message}")

        # Classify intent
        intent_result = await self._classify_intent(user_message)

        logger.info(f"Intent classified: {intent_result}")

        return intent_result

    async def _classify_intent(self, user_message: str) -> Dict[str, Any]:
        """
        Classify user intent using Gemini.

        Returns:
            Dict with intent, entities, and confidence
        """
        # Get intent classification prompt
        prompt = get_config().get_prompt(
            "system",
            "orchestrator",
            "intent_classification",
            user_message=user_message
        )

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            # Parse JSON response
            # Remove markdown code blocks if present
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            result = json.loads(result_text.strip())

            return {
                "intent": result.get("intent", "UNCLEAR"),
                "entities": result.get("entities", {}),
                "confidence": result.get("confidence", 0.0),
                "original_message": user_message
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse intent classification response: {e}")
            logger.error(f"Response text: {response.text}")
            return {
                "intent": "UNCLEAR",
                "entities": {},
                "confidence": 0.0,
                "original_message": user_message,
                "error": "Failed to parse response"
            }
        except Exception as e:
            logger.error(f"Error in intent classification: {e}")
            return {
                "intent": "ERROR",
                "entities": {},
                "confidence": 0.0,
                "original_message": user_message,
                "error": str(e)
            }

    async def generate_response(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a response using Gemini.

        Args:
            prompt: The prompt to send to Gemini
            context: Optional context to include

        Returns:
            Generated response text
        """
        try:
            full_prompt = f"{self.system_prompt}\n\n{prompt}"

            if context:
                full_prompt += f"\n\nContext: {json.dumps(context)}"

            response = self.model.generate_content(full_prompt)
            return response.text.strip()

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I'm sorry, I'm having trouble understanding. Could you please try again?"

    async def handle_clarification(
        self,
        user_message: str,
        interpreted_intent: str,
        missing_info: List[str]
    ) -> str:
        """
        Generate a clarification question for the user.

        Args:
            user_message: Original user message
            interpreted_intent: What we think the user wants
            missing_info: What information is missing

        Returns:
            Clarification question
        """
        prompt = get_config().get_prompt(
            "system",
            "orchestrator",
            "clarification",
            user_message=user_message,
            interpreted_intent=interpreted_intent,
            missing_info=", ".join(missing_info)
        )

        return await self.generate_response(prompt)

    async def handle_greeting(self, time_of_day: str = "day") -> str:
        """Generate a personalized greeting."""
        user_name = self.user_profile.get("personal_info", {}).get("preferred_name", "there")

        prompt = get_config().get_prompt(
            "conversation",
            "greeting",
            time_of_day=time_of_day,
            user_name=user_name
        )

        return await self.generate_response(prompt)

    async def handle_goodbye(self, tasks_completed: List[str] = None) -> str:
        """Generate a personalized goodbye."""
        if tasks_completed is None:
            tasks_completed = []

        tasks_str = ", ".join(tasks_completed) if tasks_completed else "nothing specific"

        prompt = get_config().get_prompt(
            "conversation",
            "goodbye",
            tasks_completed=tasks_str
        )

        return await self.generate_response(prompt)

    async def handle_confusion(self, user_message: str) -> str:
        """Handle when the agent doesn't understand."""
        prompt = get_config().get_prompt(
            "conversation",
            "confusion",
            user_message=user_message
        )

        return await self.generate_response(prompt)

    def route_to_agent(self, intent: str) -> Optional[str]:
        """
        Determine which specialized agent to route to based on intent.

        Args:
            intent: The classified intent

        Returns:
            Agent ID to route to, or None if unclear
        """
        intent_to_agent = {
            "VIDEO_CALL": "communication",
            "MEDICATION": "health",
            "APPOINTMENT": "health",
            "GENERAL_HELP": None,  # Handle directly
            "UNCLEAR": None
        }

        return intent_to_agent.get(intent)


if __name__ == "__main__":
    import asyncio
    import os
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def test_orchestrator():
        """Test the Orchestrator Agent."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not found in environment")
            return

        agent = OrchestratorAgent(user_id="margaret_thompson", api_key=api_key)

        # Test messages
        test_messages = [
            "Call my son",
            "I need to take my medication",
            "Book a doctor appointment for next Tuesday",
            "Hello!",
            "asdf qwerty"  # Nonsense to test unclear intent
        ]

        for message in test_messages:
            print(f"\n{'='*60}")
            print(f"User: {message}")
            print(f"{'='*60}")

            result = await agent.process_message(message)
            print(f"Intent: {result['intent']}")
            print(f"Confidence: {result['confidence']}")
            print(f"Entities: {result['entities']}")

            routed_agent = agent.route_to_agent(result['intent'])
            if routed_agent:
                print(f"→ Routing to: {routed_agent} agent")
            else:
                print(f"→ Handling directly")

    print("Testing Orchestrator Agent with Gemini...")
    asyncio.run(test_orchestrator())
