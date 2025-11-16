"""
ElderCare Agent - Session Manager
Manages user sessions and state across interactions.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user sessions in memory."""

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        logger.info("Session Manager initialized")

    def create_session(self, user_id: str, initial_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session for a user.

        Args:
            user_id: User identifier
            initial_context: Optional initial context

        Returns:
            Session ID
        """
        session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        self.sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "context": initial_context or {},
            "conversation_history": [],
            "current_task": None,
            "pending_action": None,  # For actions awaiting confirmation
            "active": True
        }

        logger.info(f"Created session: {session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        session = self.sessions.get(session_id)

        if session:
            # Update last active time
            session["last_active"] = datetime.now().isoformat()

        return session

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update session data.

        Args:
            session_id: Session ID
            updates: Dict of fields to update

        Returns:
            True if successful
        """
        if session_id not in self.sessions:
            return False

        self.sessions[session_id].update(updates)
        self.sessions[session_id]["last_active"] = datetime.now().isoformat()

        logger.debug(f"Updated session {session_id}")
        return True

    def add_to_conversation(
        self,
        session_id: str,
        role: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a message to conversation history.

        Args:
            session_id: Session ID
            role: Role (user, agent, system)
            message: Message content
            metadata: Optional metadata

        Returns:
            True if successful
        """
        if session_id not in self.sessions:
            return False

        self.sessions[session_id]["conversation_history"].append({
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "message": message,
            "metadata": metadata or {}
        })

        self.sessions[session_id]["last_active"] = datetime.now().isoformat()
        return True

    def get_conversation_history(self, session_id: str, limit: Optional[int] = None) -> list:
        """
        Get conversation history for a session.

        Args:
            session_id: Session ID
            limit: Optional limit on number of messages

        Returns:
            List of conversation messages
        """
        if session_id not in self.sessions:
            return []

        history = self.sessions[session_id]["conversation_history"]

        if limit:
            return history[-limit:]

        return history

    def set_current_task(self, session_id: str, task: Dict[str, Any]) -> bool:
        """Set the current task for a session."""
        if session_id not in self.sessions:
            return False

        self.sessions[session_id]["current_task"] = task
        self.sessions[session_id]["last_active"] = datetime.now().isoformat()
        return True

    def clear_current_task(self, session_id: str) -> bool:
        """Clear the current task for a session."""
        if session_id not in self.sessions:
            return False

        self.sessions[session_id]["current_task"] = None
        self.sessions[session_id]["last_active"] = datetime.now().isoformat()
        return True

    def set_pending_action(self, session_id: str, action: Dict[str, Any]) -> bool:
        """
        Set a pending action awaiting user confirmation.

        Args:
            session_id: Session ID
            action: Action dict with type, data, and confirmation message

        Returns:
            True if successful
        """
        if session_id not in self.sessions:
            return False

        self.sessions[session_id]["pending_action"] = action
        self.sessions[session_id]["last_active"] = datetime.now().isoformat()
        logger.debug(f"Set pending action for session {session_id}: {action.get('type')}")
        return True

    def get_pending_action(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get pending action if one exists.

        Args:
            session_id: Session ID

        Returns:
            Pending action dict or None
        """
        if session_id not in self.sessions:
            return None

        return self.sessions[session_id].get("pending_action")

    def clear_pending_action(self, session_id: str) -> bool:
        """
        Clear pending action after confirmation/cancellation.

        Args:
            session_id: Session ID

        Returns:
            True if successful
        """
        if session_id not in self.sessions:
            return False

        self.sessions[session_id]["pending_action"] = None
        self.sessions[session_id]["last_active"] = datetime.now().isoformat()
        logger.debug(f"Cleared pending action for session {session_id}")
        return True

    def end_session(self, session_id: str) -> bool:
        """End a session."""
        if session_id not in self.sessions:
            return False

        self.sessions[session_id]["active"] = False
        self.sessions[session_id]["ended_at"] = datetime.now().isoformat()

        logger.info(f"Ended session: {session_id}")
        return True

    def cleanup_inactive_sessions(self, max_age_hours: int = 24):
        """
        Remove inactive sessions older than max_age_hours.

        Args:
            max_age_hours: Maximum age in hours
        """
        current_time = datetime.now()
        to_remove = []

        for session_id, session in self.sessions.items():
            if not session.get("active", True):
                last_active = datetime.fromisoformat(session["last_active"])
                age_hours = (current_time - last_active).total_seconds() / 3600

                if age_hours > max_age_hours:
                    to_remove.append(session_id)

        for session_id in to_remove:
            del self.sessions[session_id]
            logger.info(f"Cleaned up inactive session: {session_id}")

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} inactive sessions")

    def get_active_session_count(self) -> int:
        """Get count of active sessions."""
        return sum(1 for s in self.sessions.values() if s.get("active", True))

    def get_user_sessions(self, user_id: str) -> list:
        """Get all sessions for a user."""
        return [
            session
            for session in self.sessions.values()
            if session["user_id"] == user_id
        ]


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test the session manager
    manager = SessionManager()

    print("Testing Session Manager...\n")

    # Test 1: Create session
    print("="*60)
    print("TEST 1: Create session")
    print("="*60)
    session_id = manager.create_session("margaret_thompson", {"greeting": "hello"})
    print(f"  Created session: {session_id}")
    print()

    # Test 2: Get session
    print("="*60)
    print("TEST 2: Get session")
    print("="*60)
    session = manager.get_session(session_id)
    print(f"  User ID: {session['user_id']}")
    print(f"  Created: {session['created_at']}")
    print(f"  Active: {session['active']}")
    print()

    # Test 3: Add to conversation
    print("="*60)
    print("TEST 3: Add to conversation")
    print("="*60)
    manager.add_to_conversation(session_id, "user", "Call my son")
    manager.add_to_conversation(session_id, "agent", "Calling John Thompson via WhatsApp")
    history = manager.get_conversation_history(session_id)
    print(f"  Conversation history: {len(history)} messages")
    for msg in history:
        print(f"    [{msg['role']}] {msg['message']}")
    print()

    # Test 4: Set current task
    print("="*60)
    print("TEST 4: Set current task")
    print("="*60)
    manager.set_current_task(session_id, {
        "type": "video_call",
        "contact": "John Thompson"
    })
    session = manager.get_session(session_id)
    print(f"  Current task: {session['current_task']}")
    print()

    # Test 5: End session
    print("="*60)
    print("TEST 5: End session")
    print("="*60)
    manager.end_session(session_id)
    session = manager.get_session(session_id)
    print(f"  Active: {session['active']}")
    print(f"  Ended at: {session.get('ended_at')}")
    print()

    # Test 6: Session stats
    print("="*60)
    print("TEST 6: Session stats")
    print("="*60)
    print(f"  Total sessions: {len(manager.sessions)}")
    print(f"  Active sessions: {manager.get_active_session_count()}")
    print()

    print("✓ Session Manager tests complete!")
