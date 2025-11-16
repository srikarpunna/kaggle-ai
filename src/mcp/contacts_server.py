"""
ElderCare Agent - Contacts MCP Server
Provides contact management tools via MCP protocol.
"""

import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ContactsMCPServer:
    """
    MCP Server for contact management.
    Provides tools for retrieving and managing user contacts.
    """

    def __init__(self, db_path: str = "data/contacts.db"):
        self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(f"Contacts database not found: {db_path}")

        logger.info(f"Contacts MCP Server initialized with database: {db_path}")

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)

    def get_contact(self, user_id: str, query: str) -> Optional[Dict[str, Any]]:
        """
        Get a contact by name or relationship.

        Args:
            user_id: User ID
            query: Name or relationship (e.g., "John", "my son", "daughter")

        Returns:
            Contact dict or None if not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Try exact name match first
        cursor.execute("""
            SELECT contact_name, phone, email, relationship, preferred_platform, photo_url, notes
            FROM contacts
            WHERE user_id = ? AND LOWER(contact_name) = LOWER(?)
        """, (user_id, query))

        row = cursor.fetchone()

        # If not found, try relationship match
        if not row:
            cursor.execute("""
                SELECT contact_name, phone, email, relationship, preferred_platform, photo_url, notes
                FROM contacts
                WHERE user_id = ? AND LOWER(relationship) LIKE LOWER(?)
            """, (user_id, f"%{query}%"))

            row = cursor.fetchone()

        conn.close()

        if not row:
            return None

        return {
            "contact_name": row[0],
            "phone": row[1],
            "email": row[2],
            "relationship": row[3],
            "preferred_platform": row[4],
            "photo_url": row[5],
            "notes": row[6]
        }

    def list_contacts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all contacts for a user.

        Args:
            user_id: User ID

        Returns:
            List of contact dicts
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT contact_name, phone, email, relationship, preferred_platform, photo_url, notes
            FROM contacts
            WHERE user_id = ?
            ORDER BY relationship, contact_name
        """, (user_id,))

        contacts = []
        for row in cursor.fetchall():
            contacts.append({
                "contact_name": row[0],
                "phone": row[1],
                "email": row[2],
                "relationship": row[3],
                "preferred_platform": row[4],
                "photo_url": row[5],
                "notes": row[6]
            })

        conn.close()
        return contacts

    def add_contact(
        self,
        user_id: str,
        contact_name: str,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        relationship: Optional[str] = None,
        preferred_platform: Optional[str] = None,
        photo_url: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Add a new contact.

        Args:
            user_id: User ID
            contact_name: Contact's full name
            phone: Phone number
            email: Email address
            relationship: Relationship to user
            preferred_platform: Preferred communication platform
            photo_url: URL to contact photo
            notes: Additional notes

        Returns:
            True if successful
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO contacts
                (user_id, contact_name, phone, email, relationship, preferred_platform, photo_url, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, contact_name, phone, email, relationship, preferred_platform, photo_url, notes))

            conn.commit()
            conn.close()

            logger.info(f"Added contact: {contact_name} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding contact: {e}")
            conn.close()
            return False

    def update_contact(
        self,
        user_id: str,
        contact_name: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update contact information.

        Args:
            user_id: User ID
            contact_name: Contact name to update
            updates: Dict of fields to update

        Returns:
            True if successful
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Build UPDATE query dynamically
        valid_fields = ["phone", "email", "relationship", "preferred_platform", "photo_url", "notes"]
        update_fields = {k: v for k, v in updates.items() if k in valid_fields}

        if not update_fields:
            conn.close()
            return False

        set_clause = ", ".join([f"{field} = ?" for field in update_fields.keys()])
        values = list(update_fields.values()) + [user_id, contact_name]

        try:
            cursor.execute(f"""
                UPDATE contacts
                SET {set_clause}
                WHERE user_id = ? AND contact_name = ?
            """, values)

            conn.commit()
            affected = cursor.rowcount
            conn.close()

            logger.info(f"Updated contact: {contact_name} for user {user_id}")
            return affected > 0

        except Exception as e:
            logger.error(f"Error updating contact: {e}")
            conn.close()
            return False

    # MCP Tool Definitions
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools."""
        return [
            {
                "name": "get_contact",
                "description": "Retrieve contact information by name or relationship",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "ID of the user making the request"
                        },
                        "query": {
                            "type": "string",
                            "description": "Name or relationship (e.g., 'John', 'my son', 'daughter')"
                        }
                    },
                    "required": ["user_id", "query"]
                }
            },
            {
                "name": "list_contacts",
                "description": "List all contacts for a user",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "ID of the user"
                        }
                    },
                    "required": ["user_id"]
                }
            },
            {
                "name": "add_contact",
                "description": "Add a new contact",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "contact_name": {"type": "string"},
                        "phone": {"type": "string"},
                        "email": {"type": "string"},
                        "relationship": {"type": "string"},
                        "preferred_platform": {"type": "string"}
                    },
                    "required": ["user_id", "contact_name"]
                }
            },
            {
                "name": "update_contact",
                "description": "Update contact information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "contact_name": {"type": "string"},
                        "updates": {"type": "object"}
                    },
                    "required": ["user_id", "contact_name", "updates"]
                }
            }
        ]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool by name.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Tool result
        """
        try:
            if tool_name == "get_contact":
                result = self.get_contact(
                    arguments["user_id"],
                    arguments["query"]
                )
                return {"success": True, "contact": result}

            elif tool_name == "list_contacts":
                result = self.list_contacts(arguments["user_id"])
                return {"success": True, "contacts": result}

            elif tool_name == "add_contact":
                result = self.add_contact(**arguments)
                return {"success": result}

            elif tool_name == "update_contact":
                result = self.update_contact(
                    arguments["user_id"],
                    arguments["contact_name"],
                    arguments["updates"]
                )
                return {"success": result}

            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test the MCP server
    server = ContactsMCPServer()

    print("Testing Contacts MCP Server...\n")

    # Test 1: List all contacts
    print("="*60)
    print("TEST 1: List all contacts")
    print("="*60)
    result = server.call_tool("list_contacts", {"user_id": "margaret_thompson"})
    if result["success"]:
        print(f"  Found {len(result['contacts'])} contacts:")
        for contact in result["contacts"]:
            print(f"    - {contact['contact_name']} ({contact['relationship']})")
    print()

    # Test 2: Get specific contact
    print("="*60)
    print("TEST 2: Get contact 'John'")
    print("="*60)
    result = server.call_tool("get_contact", {
        "user_id": "margaret_thompson",
        "query": "John"
    })
    if result["success"] and result["contact"]:
        contact = result["contact"]
        print(f"  Name: {contact['contact_name']}")
        print(f"  Relationship: {contact['relationship']}")
        print(f"  Phone: {contact['phone']}")
        print(f"  Platform: {contact['preferred_platform']}")
    print()

    # Test 3: Get contact by relationship
    print("="*60)
    print("TEST 3: Get contact by relationship 'son'")
    print("="*60)
    result = server.call_tool("get_contact", {
        "user_id": "margaret_thompson",
        "query": "son"
    })
    if result["success"] and result["contact"]:
        contact = result["contact"]
        print(f"  Found: {contact['contact_name']} ({contact['relationship']})")
    print()

    # Test 4: Get available tools
    print("="*60)
    print("TEST 4: Available MCP tools")
    print("="*60)
    tools = server.get_tools()
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")
    print()

    print("✓ Contacts MCP Server tests complete!")
