"""
ElderCare Agent - Communication Agent
Handles video calls, phone calls, and messaging with family/friends.
"""

import logging
import json
import sqlite3
from typing import Dict, Any, Optional, List
import google.generativeai as genai

from ..core.config_loader import get_config, load_user_profile
from ..core.database import Database
from ..tools.deeplink import DeepLinkGenerator

logger = logging.getLogger(__name__)


class CommunicationAgent:
    """
    Communication Agent powered by Gemini.
    Retrieves contacts and generates deep links for calls.
    """

    def __init__(self, user_id: str, api_key: str, db: Database):
        self.user_id = user_id
        self.db = db
        self.config = get_config().get_agent_config("communication")
        self.deeplink_generator = DeepLinkGenerator()

        # Load user profile
        try:
            self.user_profile = load_user_profile(user_id)
        except FileNotFoundError:
            logger.warning(f"User profile not found for {user_id}")
            self.user_profile = {}

        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=self.config.model,
            generation_config={
                "temperature": self.config.temperature,
                "max_output_tokens": self.config.max_tokens,
            }
        )

        logger.info(f"Communication Agent initialized for user: {user_id}")

    def get_contacts(self) -> List[Dict[str, Any]]:
        """Get all contacts for the user."""
        conn = self.db.get_connection("contacts")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT contact_name, phone, email, relationship, preferred_platform, photo_url
            FROM contacts
            WHERE user_id = ?
            ORDER BY relationship, contact_name
        """, (self.user_id,))

        contacts = []
        for row in cursor.fetchall():
            contacts.append({
                "contact_name": row[0],
                "phone": row[1],
                "email": row[2],
                "relationship": row[3],
                "preferred_platform": row[4],
                "photo_url": row[5]
            })

        conn.close()
        return contacts

    def find_contact(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Find a contact by name or relationship.

        Args:
            query: Name or relationship (e.g., "John", "my son", "daughter")

        Returns:
            Contact dict or None if not found
        """
        # Get all contacts
        all_contacts = self.get_contacts()

        # Use Gemini to match the query to a contact
        prompt = get_config().get_prompt(
            "communication",
            "contact_retrieval",
            user_message=query,
            contacts_json=json.dumps(all_contacts, indent=2)
        )

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            # Parse JSON response
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            result = json.loads(result_text.strip())

            if result.get("confidence", 0) > 0.7:
                logger.info(f"Found contact: {result['contact_name']} for query '{query}'")
                return result
            else:
                logger.warning(f"Low confidence match for query '{query}': {result.get('confidence')}")
                return None

        except Exception as e:
            logger.error(f"Error finding contact: {e}")
            return None

    async def handle_call_request(
        self,
        user_message: str,
        contact_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle a request to call someone.

        Args:
            user_message: User's original message
            contact_name: Optional pre-extracted contact name

        Returns:
            Dict with contact info and deep link
        """
        # If contact name not provided, extract from message
        if not contact_name:
            # Use Gemini to extract who they want to call
            contact_result = self.find_contact(user_message)
            if not contact_result:
                return {
                    "success": False,
                    "error": "contact_not_found",
                    "message": "I couldn't find that person in your contacts. Could you tell me their name?"
                }
        else:
            contact_result = self.find_contact(contact_name)
            if not contact_result:
                return {
                    "success": False,
                    "error": "contact_not_found",
                    "message": f"I couldn't find {contact_name} in your contacts."
                }

        # Get full contact details from database
        conn = self.db.get_connection("contacts")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT contact_name, phone, email, relationship, preferred_platform, photo_url, notes
            FROM contacts
            WHERE user_id = ? AND contact_name = ?
        """, (self.user_id, contact_result["contact_name"]))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return {
                "success": False,
                "error": "contact_not_found",
                "message": f"I couldn't find {contact_result['contact_name']} in your contacts."
            }

        contact = {
            "contact_name": row[0],
            "phone": row[1],
            "email": row[2],
            "relationship": row[3],
            "preferred_platform": row[4],
            "photo_url": row[5],
            "notes": row[6]
        }

        # Generate deep link based on preferred platform
        platform = contact["preferred_platform"] or "phone"

        try:
            if platform == "whatsapp":
                deep_link = self.deeplink_generator.generate_whatsapp_link(contact["phone"])
            elif platform == "facetime":
                deep_link = self.deeplink_generator.generate_facetime_link(contact["phone"])
            elif platform == "phone":
                deep_link = self.deeplink_generator.generate_phone_link(contact["phone"])
            elif platform == "zoom":
                # Would need meeting ID from somewhere
                deep_link = None
            else:
                deep_link = self.deeplink_generator.generate_phone_link(contact["phone"])

            # Generate confirmation message
            confirmation_prompt = get_config().get_prompt(
                "communication",
                "confirmation",
                contact_name=contact["contact_name"],
                relationship=contact["relationship"],
                phone=contact["phone"]
            )

            confirmation_response = self.model.generate_content(confirmation_prompt)
            confirmation_message = confirmation_response.text.strip()

            return {
                "success": True,
                "contact": contact,
                "deep_link": deep_link,
                "platform": platform,
                "confirmation_message": confirmation_message,
                "ui_template": "call_ui"
            }

        except Exception as e:
            logger.error(f"Error generating deep link: {e}")
            return {
                "success": False,
                "error": "link_generation_failed",
                "message": f"I found {contact['contact_name']} but couldn't create the call link. Please try again."
            }

    def list_contacts(self) -> List[Dict[str, Any]]:
        """List all contacts in a friendly format."""
        contacts = self.get_contacts()

        # Group by relationship
        grouped = {}
        for contact in contacts:
            rel = contact.get("relationship", "other")
            if rel not in grouped:
                grouped[rel] = []
            grouped[rel].append(contact)

        return grouped


if __name__ == "__main__":
    import asyncio
    import os
    from dotenv import load_dotenv
    from ..core.database import init_databases

    # Load environment variables
    load_dotenv()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def test_communication_agent():
        """Test the Communication Agent."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not found in environment")
            return

        # Initialize database
        db = init_databases(seed_demo=True)

        # Create agent
        agent = CommunicationAgent(
            user_id="margaret_thompson",
            api_key=api_key,
            db=db
        )

        print("Testing Communication Agent...\n")

        # Test 1: List all contacts
        print("="*60)
        print("TEST 1: List all contacts")
        print("="*60)
        contacts = agent.get_contacts()
        for contact in contacts:
            print(f"  - {contact['contact_name']} ({contact['relationship']})")
            print(f"    Phone: {contact['phone']}")
            print(f"    Platform: {contact['preferred_platform']}")
        print()

        # Test 2: Find contact by relationship
        print("="*60)
        print("TEST 2: Find 'my son'")
        print("="*60)
        result = agent.find_contact("my son")
        if result:
            print(f"  Found: {result['contact_name']} ({result['relationship']})")
            print(f"  Confidence: {result['confidence']}")
        print()

        # Test 3: Handle call request
        print("="*60)
        print("TEST 3: Call my son")
        print("="*60)
        call_result = await agent.handle_call_request("Call my son")
        if call_result["success"]:
            print(f"  ✓ Success!")
            print(f"  Contact: {call_result['contact']['contact_name']}")
            print(f"  Platform: {call_result['platform']}")
            print(f"  Deep Link: {call_result['deep_link']}")
            print(f"  Confirmation: {call_result['confirmation_message']}")
        else:
            print(f"  ✗ Failed: {call_result.get('message')}")
        print()

        # Test 4: Call by name
        print("="*60)
        print("TEST 4: Call Sarah")
        print("="*60)
        call_result = await agent.handle_call_request("I want to talk to Sarah")
        if call_result["success"]:
            print(f"  ✓ Success!")
            print(f"  Contact: {call_result['contact']['contact_name']}")
            print(f"  Platform: {call_result['platform']}")
            print(f"  Deep Link: {call_result['deep_link']}")
        print()

    print("Starting Communication Agent tests...")
    asyncio.run(test_communication_agent())
    print("\n✓ Communication Agent tests complete!")
