"""
ElderCare Agent - Health MCP Server
Provides health and medication management tools via MCP protocol.
"""

import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class HealthMCPServer:
    """
    MCP Server for health and medication management.
    Provides tools for medications, adherence tracking, and appointments.
    """

    def __init__(self, db_path: str = "data/health.db"):
        self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(f"Health database not found: {db_path}")

        logger.info(f"Health MCP Server initialized with database: {db_path}")

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)

    def get_medications(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all active medications for a user.

        Args:
            user_id: User ID

        Returns:
            List of medication dicts
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, medication_name, dosage, frequency, times, instructions, image_url
            FROM medications
            WHERE user_id = ? AND active = 1
            ORDER BY medication_name
        """, (user_id,))

        medications = []
        for row in cursor.fetchall():
            medications.append({
                "medication_id": row[0],
                "medication_name": row[1],
                "dosage": row[2],
                "frequency": row[3],
                "times": json.loads(row[4]),
                "instructions": row[5],
                "image_url": row[6]
            })

        conn.close()
        return medications

    def check_due_medications(
        self,
        user_id: str,
        current_time: Optional[str] = None,
        lookahead_minutes: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Check which medications are due now or soon.

        Args:
            user_id: User ID
            current_time: Current time (ISO format, defaults to now)
            lookahead_minutes: How many minutes ahead to check

        Returns:
            List of due medications
        """
        if current_time:
            try:
                check_time = datetime.fromisoformat(current_time)
            except:
                check_time = datetime.now()
        else:
            check_time = datetime.now()

        medications = self.get_medications(user_id)
        due_medications = []

        current_hour = check_time.hour
        current_minute = check_time.minute
        current_total_minutes = current_hour * 60 + current_minute

        for med in medications:
            for scheduled_time in med["times"]:
                sched_hour, sched_minute = map(int, scheduled_time.split(":"))
                sched_total_minutes = sched_hour * 60 + sched_minute

                diff_minutes = sched_total_minutes - current_total_minutes

                # Check if due (within lookahead window or overdue)
                if -5 <= diff_minutes <= lookahead_minutes:
                    due_medications.append({
                        **med,
                        "scheduled_time": scheduled_time,
                        "minutes_until_due": diff_minutes,
                        "is_overdue": diff_minutes < 0
                    })

        return due_medications

    def log_medication_taken(
        self,
        user_id: str,
        medication_id: int,
        taken_at: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Log that a medication was taken.

        Args:
            user_id: User ID
            medication_id: Medication ID
            taken_at: When taken (ISO format, defaults to now)
            notes: Optional notes

        Returns:
            True if successful
        """
        if taken_at:
            try:
                taken_datetime = datetime.fromisoformat(taken_at)
            except:
                taken_datetime = datetime.now()
        else:
            taken_datetime = datetime.now()

        conn = self.get_connection()
        cursor = conn.cursor()

        # Get medication times
        cursor.execute("""
            SELECT times FROM medications WHERE id = ?
        """, (medication_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return False

        times = json.loads(row[0])
        scheduled_time = taken_datetime.replace(
            hour=int(times[0].split(":")[0]),
            minute=int(times[0].split(":")[1]),
            second=0,
            microsecond=0
        )

        # Insert log
        cursor.execute("""
            INSERT INTO medication_logs
            (user_id, medication_id, scheduled_time, taken_at, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            medication_id,
            scheduled_time.isoformat(),
            taken_datetime.isoformat(),
            "taken",
            notes
        ))

        conn.commit()
        conn.close()

        logger.info(f"Logged medication {medication_id} as taken for user {user_id}")
        return True

    def get_adherence_rate(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate medication adherence rate.

        Args:
            user_id: User ID
            start_date: Start date (ISO format, defaults to 7 days ago)
            end_date: End date (ISO format, defaults to today)

        Returns:
            Dict with adherence statistics
        """
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
            except:
                end_dt = datetime.now()
        else:
            end_dt = datetime.now()

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
            except:
                start_dt = end_dt - timedelta(days=7)
        else:
            start_dt = end_dt - timedelta(days=7)

        # Count total scheduled doses
        medications = self.get_medications(user_id)
        days = (end_dt - start_dt).days + 1
        total_scheduled = sum(len(med["times"]) for med in medications) * days

        # Count taken doses
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM medication_logs
            WHERE user_id = ?
            AND status = 'taken'
            AND scheduled_time BETWEEN ? AND ?
        """, (user_id, start_dt.isoformat(), end_dt.isoformat()))

        total_taken = cursor.fetchone()[0]

        # Count missed doses
        cursor.execute("""
            SELECT COUNT(*) FROM medication_logs
            WHERE user_id = ?
            AND status = 'missed'
            AND scheduled_time BETWEEN ? AND ?
        """, (user_id, start_dt.isoformat(), end_dt.isoformat()))

        total_missed = cursor.fetchone()[0]
        conn.close()

        adherence_rate = (total_taken / total_scheduled * 100) if total_scheduled > 0 else 0

        return {
            "adherence_rate": round(adherence_rate, 1),
            "total_scheduled": total_scheduled,
            "total_taken": total_taken,
            "total_missed": total_missed,
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat()
        }

    def add_medication(
        self,
        user_id: str,
        medication_name: str,
        dosage: str,
        frequency: str,
        times: List[str],
        instructions: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> bool:
        """
        Add a new medication.

        Args:
            user_id: User ID
            medication_name: Medication name
            dosage: Dosage (e.g., "10 mg")
            frequency: Frequency (once_daily, twice_daily, etc.)
            times: List of times (e.g., ["09:00", "21:00"])
            instructions: Instructions for taking
            image_url: URL to medication image

        Returns:
            True if successful
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO medications
                (user_id, medication_name, dosage, frequency, times, instructions, image_url, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                user_id,
                medication_name,
                dosage,
                frequency,
                json.dumps(times),
                instructions,
                image_url
            ))

            conn.commit()
            conn.close()

            logger.info(f"Added medication: {medication_name} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding medication: {e}")
            conn.close()
            return False

    # MCP Tool Definitions
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools."""
        return [
            {
                "name": "get_medications",
                "description": "Get all active medications for a user",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"}
                    },
                    "required": ["user_id"]
                }
            },
            {
                "name": "check_due_medications",
                "description": "Check which medications are due now or soon",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "current_time": {"type": "string"},
                        "lookahead_minutes": {"type": "integer", "default": 15}
                    },
                    "required": ["user_id"]
                }
            },
            {
                "name": "log_medication_taken",
                "description": "Log that a medication was taken",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "medication_id": {"type": "integer"},
                        "taken_at": {"type": "string"},
                        "notes": {"type": "string"}
                    },
                    "required": ["user_id", "medication_id"]
                }
            },
            {
                "name": "get_adherence_rate",
                "description": "Calculate medication adherence rate",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"}
                    },
                    "required": ["user_id"]
                }
            },
            {
                "name": "add_medication",
                "description": "Add a new medication to the schedule",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "medication_name": {"type": "string"},
                        "dosage": {"type": "string"},
                        "frequency": {"type": "string"},
                        "times": {"type": "array", "items": {"type": "string"}},
                        "instructions": {"type": "string"}
                    },
                    "required": ["user_id", "medication_name", "dosage", "frequency", "times"]
                }
            }
        ]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool by name."""
        try:
            if tool_name == "get_medications":
                result = self.get_medications(arguments["user_id"])
                return {"success": True, "medications": result}

            elif tool_name == "check_due_medications":
                result = self.check_due_medications(
                    arguments["user_id"],
                    arguments.get("current_time"),
                    arguments.get("lookahead_minutes", 15)
                )
                return {"success": True, "due_medications": result}

            elif tool_name == "log_medication_taken":
                result = self.log_medication_taken(**arguments)
                return {"success": result}

            elif tool_name == "get_adherence_rate":
                result = self.get_adherence_rate(
                    arguments["user_id"],
                    arguments.get("start_date"),
                    arguments.get("end_date")
                )
                return {"success": True, "adherence": result}

            elif tool_name == "add_medication":
                result = self.add_medication(**arguments)
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
    server = HealthMCPServer()

    print("Testing Health MCP Server...\n")

    # Test 1: Get medications
    print("="*60)
    print("TEST 1: Get all medications")
    print("="*60)
    result = server.call_tool("get_medications", {"user_id": "margaret_thompson"})
    if result["success"]:
        print(f"  Found {len(result['medications'])} medications:")
        for med in result["medications"]:
            print(f"    - {med['medication_name']} ({med['dosage']})")
            print(f"      Times: {', '.join(med['times'])}")
    print()

    # Test 2: Check due medications
    print("="*60)
    print("TEST 2: Check medications due at 9:00 AM")
    print("="*60)
    result = server.call_tool("check_due_medications", {
        "user_id": "margaret_thompson",
        "current_time": datetime.now().replace(hour=9, minute=0).isoformat(),
        "lookahead_minutes": 15
    })
    if result["success"]:
        due = result["due_medications"]
        print(f"  Found {len(due)} due medications:")
        for med in due:
            print(f"    - {med['medication_name']} at {med['scheduled_time']}")
    print()

    # Test 3: Log medication taken
    print("="*60)
    print("TEST 3: Log medication taken")
    print("="*60)
    if result["success"] and result["medications"]:
        med_id = result["medications"][0]["medication_id"]
        log_result = server.call_tool("log_medication_taken", {
            "user_id": "margaret_thompson",
            "medication_id": med_id,
            "notes": "Taken with breakfast"
        })
        print(f"  Log successful: {log_result['success']}")
    print()

    # Test 4: Get adherence rate
    print("="*60)
    print("TEST 4: Get adherence rate (last 7 days)")
    print("="*60)
    result = server.call_tool("get_adherence_rate", {
        "user_id": "margaret_thompson"
    })
    if result["success"]:
        adh = result["adherence"]
        print(f"  Adherence rate: {adh['adherence_rate']}%")
        print(f"  Scheduled: {adh['total_scheduled']}")
        print(f"  Taken: {adh['total_taken']}")
    print()

    print("✓ Health MCP Server tests complete!")
