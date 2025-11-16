"""
ElderCare Agent - Health Agent
Manages medications, reminders, and doctor appointments.
"""

import logging
import json
import sqlite3
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import google.generativeai as genai

from ..core.config_loader import get_config, load_user_profile
from ..core.database import Database

logger = logging.getLogger(__name__)


class HealthAgent:
    """
    Health Agent powered by Gemini.
    Manages medication schedules and doctor appointments.
    """

    def __init__(self, user_id: str, api_key: str, db: Database):
        self.user_id = user_id
        self.db = db
        self.config = get_config().get_agent_config("health")

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

        logger.info(f"Health Agent initialized for user: {user_id}")

    def get_medications(self) -> List[Dict[str, Any]]:
        """Get all active medications for the user."""
        conn = self.db.get_connection("health")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, medication_name, dosage, frequency, times, instructions, image_url
            FROM medications
            WHERE user_id = ? AND active = 1
            ORDER BY medication_name
        """, (self.user_id,))

        medications = []
        for row in cursor.fetchall():
            medications.append({
                "medication_id": row[0],
                "medication_name": row[1],
                "dosage": row[2],
                "frequency": row[3],
                "times": json.loads(row[4]),  # Parse JSON array
                "instructions": row[5],
                "image_url": row[6]
            })

        conn.close()
        return medications

    def check_due_medications(self, current_time: Optional[datetime] = None, lookahead_minutes: int = 15) -> List[Dict[str, Any]]:
        """
        Check which medications are due now or soon.

        Args:
            current_time: Current time (defaults to now)
            lookahead_minutes: How many minutes ahead to check

        Returns:
            List of medications that are due
        """
        if current_time is None:
            current_time = datetime.now()

        medications = self.get_medications()
        due_medications = []

        current_time_str = current_time.strftime("%H:%M")
        current_hour = current_time.hour
        current_minute = current_time.minute

        for med in medications:
            for scheduled_time in med["times"]:
                # Parse scheduled time (format: "HH:MM")
                sched_hour, sched_minute = map(int, scheduled_time.split(":"))

                # Calculate time difference in minutes
                sched_total_minutes = sched_hour * 60 + sched_minute
                current_total_minutes = current_hour * 60 + current_minute

                diff_minutes = sched_total_minutes - current_total_minutes

                # Check if due (within lookahead window or overdue)
                if -5 <= diff_minutes <= lookahead_minutes:  # 5 min grace period
                    due_medications.append({
                        **med,
                        "scheduled_time": scheduled_time,
                        "minutes_until_due": diff_minutes,
                        "is_overdue": diff_minutes < 0
                    })

        return due_medications

    async def generate_medication_reminder(self, medication: Dict[str, Any]) -> str:
        """
        Generate a friendly medication reminder message.

        Args:
            medication: Medication dict with name, dosage, instructions

        Returns:
            Reminder message
        """
        prompt = get_config().get_prompt(
            "system",
            "health",
            "medication_reminder_message",
            medication_name=medication["medication_name"],
            dosage=medication["dosage"],
            instructions=medication.get("instructions", "")
        )

        response = self.model.generate_content(prompt)
        return response.text.strip()

    def log_medication_taken(self, medication_id: int, taken_at: Optional[datetime] = None, notes: Optional[str] = None) -> bool:
        """
        Log that a medication was taken.

        Args:
            medication_id: ID of the medication
            taken_at: When it was taken (defaults to now)
            notes: Optional notes

        Returns:
            True if successful
        """
        if taken_at is None:
            taken_at = datetime.now()

        conn = self.db.get_connection("health")
        cursor = conn.cursor()

        # Find the scheduled time for today
        cursor.execute("""
            SELECT times FROM medications WHERE id = ?
        """, (medication_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return False

        times = json.loads(row[0])
        # Use the closest scheduled time
        scheduled_time = taken_at.replace(
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
            self.user_id,
            medication_id,
            scheduled_time.isoformat(),
            taken_at.isoformat(),
            "taken",
            notes
        ))

        conn.commit()
        conn.close()

        logger.info(f"Logged medication {medication_id} as taken at {taken_at}")
        return True

    def get_adherence_rate(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Calculate medication adherence rate.

        Args:
            start_date: Start date (defaults to 7 days ago)
            end_date: End date (defaults to today)

        Returns:
            Dict with adherence statistics
        """
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=7)

        conn = self.db.get_connection("health")
        cursor = conn.cursor()

        # Count total scheduled doses
        medications = self.get_medications()
        days = (end_date - start_date).days + 1
        total_scheduled = sum(len(med["times"]) for med in medications) * days

        # Count taken doses
        cursor.execute("""
            SELECT COUNT(*) FROM medication_logs
            WHERE user_id = ?
            AND status = 'taken'
            AND scheduled_time BETWEEN ? AND ?
        """, (
            self.user_id,
            start_date.isoformat(),
            end_date.isoformat()
        ))

        total_taken = cursor.fetchone()[0]

        # Count missed doses
        cursor.execute("""
            SELECT COUNT(*) FROM medication_logs
            WHERE user_id = ?
            AND status = 'missed'
            AND scheduled_time BETWEEN ? AND ?
        """, (
            self.user_id,
            start_date.isoformat(),
            end_date.isoformat()
        ))

        total_missed = cursor.fetchone()[0]

        conn.close()

        adherence_rate = (total_taken / total_scheduled * 100) if total_scheduled > 0 else 0

        return {
            "adherence_rate": round(adherence_rate, 1),
            "total_scheduled": total_scheduled,
            "total_taken": total_taken,
            "total_missed": total_missed,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }

    async def handle_medication_request(self, user_message: str) -> Dict[str, Any]:
        """
        Handle a medication-related request.

        Args:
            user_message: User's message

        Returns:
            Response dict with action and data
        """
        # Get medication schedule
        medications = self.get_medications()

        # Use Gemini to determine what the user wants
        prompt = get_config().get_prompt(
            "system",
            "health",
            "medication_check",
            user_message=user_message,
            medication_schedule_json=json.dumps(medications, indent=2),
            current_time=datetime.now().strftime("%H:%M")
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

            action = result.get("action")

            if action == "CHECK":
                # User asking if they took medication
                # Check today's logs
                conn = self.db.get_connection("health")
                cursor = conn.cursor()

                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

                cursor.execute("""
                    SELECT m.medication_name, ml.status, ml.taken_at
                    FROM medication_logs ml
                    JOIN medications m ON ml.medication_id = m.id
                    WHERE ml.user_id = ?
                    AND ml.scheduled_time >= ?
                    ORDER BY ml.scheduled_time DESC
                """, (self.user_id, today_start.isoformat()))

                today_logs = cursor.fetchall()
                conn.close()

                return {
                    "action": "CHECK",
                    "today_logs": [
                        {"medication": row[0], "status": row[1], "taken_at": row[2]}
                        for row in today_logs
                    ],
                    "response": result.get("response_to_user")
                }

            elif action == "INFO":
                # User asking what medications they take
                return {
                    "action": "INFO",
                    "medications": medications,
                    "response": result.get("response_to_user")
                }

            elif action == "TAKE_NOW":
                # It's time to take medication
                due_meds = self.check_due_medications()
                return {
                    "action": "TAKE_NOW",
                    "due_medications": due_meds,
                    "response": result.get("response_to_user"),
                    "ui_template": "medication_ui"
                }

            else:
                return {
                    "action": "UNCLEAR",
                    "response": result.get("response_to_user", "I'm not sure what you need help with regarding your medications.")
                }

        except Exception as e:
            logger.error(f"Error handling medication request: {e}")
            return {
                "action": "ERROR",
                "error": str(e),
                "response": "I'm having trouble understanding your medication request. Could you please try again?"
            }

    def get_appointments(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get upcoming appointments."""
        if start_date is None:
            start_date = datetime.now()
        if end_date is None:
            end_date = start_date + timedelta(days=30)

        conn = self.db.get_connection("calendar")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, doctor_name, date, time, duration_minutes, location, notes, status
            FROM appointments
            WHERE user_id = ?
            AND date BETWEEN ? AND ?
            AND status = 'scheduled'
            ORDER BY date, time
        """, (
            self.user_id,
            start_date.date().isoformat(),
            end_date.date().isoformat()
        ))

        appointments = []
        for row in cursor.fetchall():
            appointments.append({
                "appointment_id": row[0],
                "title": row[1],
                "doctor_name": row[2],
                "date": row[3],
                "time": row[4],
                "duration_minutes": row[5],
                "location": row[6],
                "notes": row[7],
                "status": row[8]
            })

        conn.close()
        return appointments


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

    async def test_health_agent():
        """Test the Health Agent."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not found in environment")
            return

        # Initialize database
        db = init_databases(seed_demo=True)

        # Create agent
        agent = HealthAgent(
            user_id="margaret_thompson",
            api_key=api_key,
            db=db
        )

        print("Testing Health Agent...\n")

        # Test 1: Get all medications
        print("="*60)
        print("TEST 1: Get all medications")
        print("="*60)
        medications = agent.get_medications()
        for med in medications:
            print(f"  - {med['medication_name']} ({med['dosage']})")
            print(f"    Times: {', '.join(med['times'])}")
            print(f"    Instructions: {med['instructions']}")
        print()

        # Test 2: Check due medications
        print("="*60)
        print("TEST 2: Check medications due at 9:00 AM")
        print("="*60)
        test_time = datetime.now().replace(hour=9, minute=0)
        due_meds = agent.check_due_medications(test_time, lookahead_minutes=15)
        if due_meds:
            for med in due_meds:
                print(f"  - {med['medication_name']} due at {med['scheduled_time']}")
                print(f"    {med['minutes_until_due']} minutes until due")
        else:
            print("  No medications due")
        print()

        # Test 3: Log medication taken
        print("="*60)
        print("TEST 3: Log medication taken")
        print("="*60)
        if medications:
            success = agent.log_medication_taken(medications[0]["medication_id"])
            print(f"  Log medication: {'✓ Success' if success else '✗ Failed'}")
        print()

        # Test 4: Get adherence rate
        print("="*60)
        print("TEST 4: Get adherence rate (last 7 days)")
        print("="*60)
        adherence = agent.get_adherence_rate()
        print(f"  Adherence Rate: {adherence['adherence_rate']}%")
        print(f"  Scheduled: {adherence['total_scheduled']}")
        print(f"  Taken: {adherence['total_taken']}")
        print(f"  Missed: {adherence['total_missed']}")
        print()

        # Test 5: Handle medication request
        print("="*60)
        print("TEST 5: Handle 'What medications do I take?'")
        print("="*60)
        result = await agent.handle_medication_request("What medications do I take?")
        print(f"  Action: {result['action']}")
        print(f"  Response: {result['response']}")
        print()

    print("Starting Health Agent tests...")
    asyncio.run(test_health_agent())
    print("\n✓ Health Agent tests complete!")
