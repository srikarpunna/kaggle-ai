"""
ElderCare Agent - Memory Agent
Stores and retrieves user information, preferences, and history.
"""

import logging
import json
import sqlite3
from typing import Dict, Any, Optional, List
from datetime import datetime
import google.generativeai as genai

from ..core.config_loader import get_config, load_user_profile
from ..core.database import Database

logger = logging.getLogger(__name__)


class MemoryAgent:
    """
    Memory Agent powered by Gemini.
    Manages sessions, user context, and learned preferences.
    """

    def __init__(self, user_id: str, api_key: str, db: Database):
        self.user_id = user_id
        self.db = db
        self.config = get_config().get_agent_config("memory")

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

        logger.info(f"Memory Agent initialized for user: {user_id}")

    def create_session(self, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session for the user.

        Args:
            context: Optional initial context

        Returns:
            Session ID
        """
        conn = self.db.get_connection("memory")
        cursor = conn.cursor()

        session_id = f"{self.user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        context_json = json.dumps(context) if context else None

        cursor.execute("""
            INSERT INTO sessions (session_id, user_id, context, active)
            VALUES (?, ?, ?, 1)
        """, (session_id, self.user_id, context_json))

        conn.commit()
        conn.close()

        logger.info(f"Created session: {session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        conn = self.db.get_connection("memory")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT session_id, user_id, started_at, ended_at, context, active
            FROM sessions
            WHERE session_id = ?
        """, (session_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "session_id": row[0],
            "user_id": row[1],
            "started_at": row[2],
            "ended_at": row[3],
            "context": json.loads(row[4]) if row[4] else {},
            "active": bool(row[5])
        }

    def update_session_context(self, session_id: str, context: Dict[str, Any]) -> bool:
        """Update session context."""
        conn = self.db.get_connection("memory")
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE sessions
            SET context = ?
            WHERE session_id = ?
        """, (json.dumps(context), session_id))

        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected > 0

    def end_session(self, session_id: str) -> bool:
        """End a session."""
        conn = self.db.get_connection("memory")
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE sessions
            SET ended_at = CURRENT_TIMESTAMP, active = 0
            WHERE session_id = ?
        """, (session_id,))

        conn.commit()
        affected = cursor.rowcount
        conn.close()

        logger.info(f"Ended session: {session_id}")
        return affected > 0

    def log_interaction(
        self,
        session_id: str,
        intent: str,
        task_type: str,
        input_text: str,
        agent_response: str,
        task_completed: bool,
        user_satisfied: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Log an interaction.

        Returns:
            Interaction ID
        """
        conn = self.db.get_connection("memory")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO interactions
            (session_id, user_id, intent, task_type, input_text, agent_response,
             task_completed, user_satisfied, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            self.user_id,
            intent,
            task_type,
            input_text,
            agent_response,
            task_completed,
            user_satisfied,
            json.dumps(metadata) if metadata else None
        ))

        interaction_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Logged interaction {interaction_id} in session {session_id}")
        return interaction_id

    def get_session_interactions(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all interactions for a session."""
        conn = self.db.get_connection("memory")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, timestamp, intent, task_type, input_text, agent_response,
                   task_completed, user_satisfied, metadata
            FROM interactions
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """, (session_id,))

        interactions = []
        for row in cursor.fetchall():
            interactions.append({
                "id": row[0],
                "timestamp": row[1],
                "intent": row[2],
                "task_type": row[3],
                "input_text": row[4],
                "agent_response": row[5],
                "task_completed": row[6],
                "user_satisfied": row[7],
                "metadata": json.loads(row[8]) if row[8] else {}
            })

        conn.close()
        return interactions

    def store_long_term_memory(
        self,
        memory_type: str,
        key: str,
        value: Any,
        confidence: float = 1.0
    ) -> bool:
        """
        Store a piece of long-term memory (learned preference).

        Args:
            memory_type: Type of memory (preference, fact, relationship, etc.)
            key: Memory key
            value: Memory value
            confidence: Confidence level (0.0-1.0)

        Returns:
            True if successful
        """
        conn = self.db.get_connection("memory")
        cursor = conn.cursor()

        value_json = json.dumps(value) if not isinstance(value, str) else value

        cursor.execute("""
            INSERT INTO long_term_memory
            (user_id, memory_type, key, value, confidence, last_accessed, access_count)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 1)
            ON CONFLICT(user_id, memory_type, key) DO UPDATE SET
                value = excluded.value,
                confidence = excluded.confidence,
                last_accessed = CURRENT_TIMESTAMP,
                access_count = access_count + 1
        """, (self.user_id, memory_type, key, value_json, confidence))

        conn.commit()
        conn.close()

        logger.info(f"Stored long-term memory: {memory_type}/{key}")
        return True

    def retrieve_long_term_memory(
        self,
        memory_type: str,
        key: Optional[str] = None
    ) -> Optional[Any]:
        """
        Retrieve long-term memory.

        Args:
            memory_type: Type of memory
            key: Optional specific key (if None, returns all for type)

        Returns:
            Memory value(s) or None
        """
        conn = self.db.get_connection("memory")
        cursor = conn.cursor()

        if key:
            cursor.execute("""
                SELECT value, confidence, last_accessed, access_count
                FROM long_term_memory
                WHERE user_id = ? AND memory_type = ? AND key = ?
            """, (self.user_id, memory_type, key))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            # Update access count
            self._increment_access_count(memory_type, key)

            try:
                value = json.loads(row[0])
            except (json.JSONDecodeError, TypeError):
                value = row[0]

            return {
                "value": value,
                "confidence": row[1],
                "last_accessed": row[2],
                "access_count": row[3]
            }
        else:
            # Get all memories of this type
            cursor.execute("""
                SELECT key, value, confidence
                FROM long_term_memory
                WHERE user_id = ? AND memory_type = ?
                ORDER BY confidence DESC, access_count DESC
            """, (self.user_id, memory_type))

            memories = {}
            for row in cursor.fetchall():
                try:
                    value = json.loads(row[1])
                except (json.JSONDecodeError, TypeError):
                    value = row[1]

                memories[row[0]] = {
                    "value": value,
                    "confidence": row[2]
                }

            conn.close()
            return memories if memories else None

    def _increment_access_count(self, memory_type: str, key: str):
        """Increment access count for a memory."""
        conn = self.db.get_connection("memory")
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE long_term_memory
            SET access_count = access_count + 1,
                last_accessed = CURRENT_TIMESTAMP
            WHERE user_id = ? AND memory_type = ? AND key = ?
        """, (self.user_id, memory_type, key))

        conn.commit()
        conn.close()

    async def resolve_relationship(self, reference: str) -> Optional[Dict[str, Any]]:
        """
        Resolve a relationship reference to a person.

        Args:
            reference: Reference like "my son", "my daughter", "John"

        Returns:
            Person details or None
        """
        # Get family relationships from user profile
        family = self.user_profile.get("family", [])

        # Use Gemini to map the reference
        prompt = get_config().get_prompt(
            "memory",
            "relationship_mapping",
            user_message=reference,
            family_tree_json=json.dumps(family, indent=2)
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
            return result

        except Exception as e:
            logger.error(f"Error resolving relationship: {e}")
            return None

    async def learn_from_interaction(
        self,
        interaction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Learn preferences from an interaction.

        Args:
            interaction: Interaction dict with details

        Returns:
            Dict of learned preferences
        """
        prompt = get_config().get_prompt(
            "memory",
            "preference_learning",
            task_name=interaction.get("task_type", "unknown"),
            interaction_json=json.dumps(interaction, indent=2)
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

            # Store learned preferences
            if result.get("update_profile"):
                learned_prefs = result.get("learned_preferences", {})
                for key, value in learned_prefs.items():
                    self.store_long_term_memory("preference", key, value, confidence=0.8)

            return result

        except Exception as e:
            logger.error(f"Error learning from interaction: {e}")
            return {"learned_preferences": {}, "update_profile": False}

    def get_user_context(self) -> Dict[str, Any]:
        """
        Get comprehensive user context.

        Returns:
            Dict with user profile, preferences, and recent interactions
        """
        # Get user profile
        context = {
            "user_id": self.user_id,
            "profile": self.user_profile,
            "preferences": {}
        }

        # Get learned preferences
        preferences = self.retrieve_long_term_memory("preference")
        if preferences:
            context["preferences"] = preferences

        # Get recent interactions (last 10)
        conn = self.db.get_connection("memory")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT intent, task_type, task_completed, timestamp
            FROM interactions
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 10
        """, (self.user_id,))

        recent_interactions = []
        for row in cursor.fetchall():
            recent_interactions.append({
                "intent": row[0],
                "task_type": row[1],
                "completed": row[2],
                "timestamp": row[3]
            })

        conn.close()
        context["recent_interactions"] = recent_interactions

        return context


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

    async def test_memory_agent():
        """Test the Memory Agent."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not found in environment")
            return

        # Initialize database
        db = init_databases(seed_demo=True)

        # Create agent
        agent = MemoryAgent(
            user_id="margaret_thompson",
            api_key=api_key,
            db=db
        )

        print("Testing Memory Agent...\n")

        # Test 1: Create session
        print("="*60)
        print("TEST 1: Create session")
        print("="*60)
        session_id = agent.create_session(context={"initial": "greeting"})
        print(f"  Created session: {session_id}")
        print()

        # Test 2: Log interaction
        print("="*60)
        print("TEST 2: Log interaction")
        print("="*60)
        interaction_id = agent.log_interaction(
            session_id=session_id,
            intent="VIDEO_CALL",
            task_type="call_son",
            input_text="Call my son",
            agent_response="Calling John Thompson via WhatsApp",
            task_completed=True,
            user_satisfied=True,
            metadata={"contact": "John Thompson", "platform": "whatsapp"}
        )
        print(f"  Logged interaction: {interaction_id}")
        print()

        # Test 3: Store long-term memory
        print("="*60)
        print("TEST 3: Store long-term memory (preferences)")
        print("="*60)
        agent.store_long_term_memory("preference", "preferred_call_platform_john", "whatsapp", confidence=0.9)
        agent.store_long_term_memory("preference", "preferred_call_time", "sunday_afternoon", confidence=0.8)
        print("  ✓ Stored 2 preferences")
        print()

        # Test 4: Retrieve long-term memory
        print("="*60)
        print("TEST 4: Retrieve long-term memory")
        print("="*60)
        prefs = agent.retrieve_long_term_memory("preference")
        if prefs:
            for key, data in prefs.items():
                print(f"  - {key}: {data['value']} (confidence: {data['confidence']})")
        print()

        # Test 5: Resolve relationship
        print("="*60)
        print("TEST 5: Resolve relationship")
        print("="*60)
        result = await agent.resolve_relationship("my son")
        if result:
            print(f"  'my son' → {result.get('actual_person')}")
            print(f"  Relationship: {result.get('relationship')}")
        print()

        # Test 6: Get user context
        print("="*60)
        print("TEST 6: Get comprehensive user context")
        print("="*60)
        context = agent.get_user_context()
        print(f"  User: {context['user_id']}")
        print(f"  Preferences: {len(context['preferences'])} stored")
        print(f"  Recent interactions: {len(context['recent_interactions'])}")
        print()

        # Test 7: End session
        print("="*60)
        print("TEST 7: End session")
        print("="*60)
        agent.end_session(session_id)
        print(f"  ✓ Session ended: {session_id}")
        print()

    print("Starting Memory Agent tests...")
    asyncio.run(test_memory_agent())
    print("\n✓ Memory Agent tests complete!")
