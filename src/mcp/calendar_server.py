"""
ElderCare Agent - Calendar MCP Server
Provides appointment management and Google Calendar integration via MCP protocol.
"""

import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class CalendarMCPServer:
    """
    MCP Server for calendar and appointment management.
    Provides tools for appointments and Google Calendar integration.
    """

    def __init__(self, calendar_db_path: str = "data/calendar.db"):
        self.calendar_db_path = Path(calendar_db_path)

        if not self.calendar_db_path.exists():
            raise FileNotFoundError(f"Calendar database not found: {calendar_db_path}")

        self.google_calendar = None  # Will be initialized if credentials available

        logger.info(f"Calendar MCP Server initialized with database: {calendar_db_path}")

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.calendar_db_path)

    def get_appointments(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get appointments for a user.

        Args:
            user_id: User ID
            start_date: Start date (ISO format, defaults to today)
            end_date: End date (ISO format, defaults to 30 days from start)

        Returns:
            List of appointment dicts
        """
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date).date()
            except:
                start_dt = datetime.now().date()
        else:
            start_dt = datetime.now().date()

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date).date()
            except:
                end_dt = start_dt + timedelta(days=30)
        else:
            end_dt = start_dt + timedelta(days=30)

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, doctor_name, date, time, duration_minutes, location, notes, status, google_event_id
            FROM appointments
            WHERE user_id = ?
            AND date BETWEEN ? AND ?
            AND status = 'scheduled'
            ORDER BY date, time
        """, (user_id, start_dt.isoformat(), end_dt.isoformat()))

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
                "status": row[8],
                "google_event_id": row[9]
            })

        conn.close()
        return appointments

    def create_appointment(
        self,
        user_id: str,
        title: str,
        date: str,
        time: str,
        doctor_name: Optional[str] = None,
        duration_minutes: int = 30,
        location: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new appointment.

        Args:
            user_id: User ID
            title: Appointment title
            date: Date (YYYY-MM-DD)
            time: Time (HH:MM)
            doctor_name: Doctor name
            duration_minutes: Duration in minutes
            location: Location
            notes: Additional notes

        Returns:
            Dict with success status and appointment_id
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO appointments
                (user_id, title, doctor_name, date, time, duration_minutes, location, notes, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'scheduled')
            """, (user_id, title, doctor_name, date, time, duration_minutes, location, notes))

            appointment_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"Created appointment {appointment_id} for user {user_id}")

            return {
                "success": True,
                "appointment_id": appointment_id,
                "google_event_id": None  # Would be set after Google Calendar sync
            }

        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            conn.close()
            return {"success": False, "error": str(e)}

    def update_appointment(
        self,
        user_id: str,
        appointment_id: int,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update an appointment.

        Args:
            user_id: User ID
            appointment_id: Appointment ID
            updates: Dict of fields to update

        Returns:
            True if successful
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        valid_fields = ["title", "doctor_name", "date", "time", "duration_minutes", "location", "notes", "status"]
        update_fields = {k: v for k, v in updates.items() if k in valid_fields}

        if not update_fields:
            conn.close()
            return False

        set_clause = ", ".join([f"{field} = ?" for field in update_fields.keys()])
        values = list(update_fields.values()) + [user_id, appointment_id]

        try:
            cursor.execute(f"""
                UPDATE appointments
                SET {set_clause}
                WHERE user_id = ? AND id = ?
            """, values)

            conn.commit()
            affected = cursor.rowcount
            conn.close()

            logger.info(f"Updated appointment {appointment_id} for user {user_id}")
            return affected > 0

        except Exception as e:
            logger.error(f"Error updating appointment: {e}")
            conn.close()
            return False

    def cancel_appointment(self, user_id: str, appointment_id: int) -> bool:
        """Cancel an appointment."""
        return self.update_appointment(user_id, appointment_id, {"status": "cancelled"})

    def sync_to_google_calendar(
        self,
        appointment_id: int,
        user_calendar_id: str = "primary"
    ) -> Dict[str, Any]:
        """
        Sync an appointment to Google Calendar.

        NOTE: This is a placeholder for Google Calendar API integration.
        Full implementation would require:
        1. Google Calendar API credentials
        2. OAuth flow for user authorization
        3. google-api-python-client library

        Args:
            appointment_id: Appointment ID
            user_calendar_id: Google Calendar ID (default: primary)

        Returns:
            Dict with sync status
        """
        # Get appointment details
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT title, doctor_name, date, time, duration_minutes, location, notes
            FROM appointments
            WHERE id = ?
        """, (appointment_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"success": False, "error": "Appointment not found"}

        # This is where Google Calendar API integration would happen
        # For now, return a simulated success
        logger.info(f"Would sync appointment {appointment_id} to Google Calendar")

        # In a real implementation:
        # from googleapiclient.discovery import build
        # service = build('calendar', 'v3', credentials=creds)
        # event = {
        #     'summary': row[0],  # title
        #     'location': row[5],  # location
        #     'description': row[6],  # notes
        #     'start': {
        #         'dateTime': f"{row[2]}T{row[3]}:00",
        #         'timeZone': 'America/New_York',
        #     },
        #     'end': {
        #         'dateTime': ...,  # calculate from duration
        #         'timeZone': 'America/New_York',
        #     },
        #     'reminders': {
        #         'useDefault': False,
        #         'overrides': [
        #             {'method': 'popup', 'minutes': 24 * 60},  # 1 day before
        #             {'method': 'popup', 'minutes': 60},  # 1 hour before
        #         ],
        #     },
        # }
        # result = service.events().insert(calendarId=user_calendar_id, body=event).execute()

        return {
            "success": True,
            "google_event_id": f"simulated_event_{appointment_id}",
            "message": "Google Calendar integration requires OAuth setup. See docs/SETUP_GUIDE.md"
        }

    def check_availability(
        self,
        doctor_id: str,
        start_date: str,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Check available time slots for a doctor.

        NOTE: This is a simplified implementation.
        Real implementation would check against doctor's schedule.

        Args:
            doctor_id: Doctor identifier
            start_date: Start date
            end_date: End date (defaults to 14 days from start)

        Returns:
            List of available slots
        """
        try:
            start_dt = datetime.fromisoformat(start_date).date()
        except:
            start_dt = datetime.now().date()

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date).date()
            except:
                end_dt = start_dt + timedelta(days=14)
        else:
            end_dt = start_dt + timedelta(days=14)

        # Generate sample available slots
        # In real implementation, this would check against actual doctor schedule
        available_slots = []
        current_date = start_dt

        while current_date <= end_dt:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday-Friday
                # Morning slots
                for hour in [9, 10, 11]:
                    for minute in [0, 30]:
                        available_slots.append({
                            "date": current_date.isoformat(),
                            "time": f"{hour:02d}:{minute:02d}",
                            "available": True
                        })

                # Afternoon slots
                for hour in [14, 15, 16]:
                    for minute in [0, 30]:
                        available_slots.append({
                            "date": current_date.isoformat(),
                            "time": f"{hour:02d}:{minute:02d}",
                            "available": True
                        })

            current_date += timedelta(days=1)

        return available_slots[:20]  # Return first 20 slots

    # MCP Tool Definitions
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools."""
        return [
            {
                "name": "get_appointments",
                "description": "Get appointments for a user",
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
                "name": "create_appointment",
                "description": "Create a new appointment",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "title": {"type": "string"},
                        "date": {"type": "string"},
                        "time": {"type": "string"},
                        "doctor_name": {"type": "string"},
                        "duration_minutes": {"type": "integer"},
                        "location": {"type": "string"},
                        "notes": {"type": "string"}
                    },
                    "required": ["user_id", "title", "date", "time"]
                }
            },
            {
                "name": "update_appointment",
                "description": "Update an appointment",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "appointment_id": {"type": "integer"},
                        "updates": {"type": "object"}
                    },
                    "required": ["user_id", "appointment_id", "updates"]
                }
            },
            {
                "name": "cancel_appointment",
                "description": "Cancel an appointment",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "appointment_id": {"type": "integer"}
                    },
                    "required": ["user_id", "appointment_id"]
                }
            },
            {
                "name": "sync_to_google_calendar",
                "description": "Sync an appointment to Google Calendar",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "appointment_id": {"type": "integer"},
                        "user_calendar_id": {"type": "string"}
                    },
                    "required": ["appointment_id"]
                }
            },
            {
                "name": "check_availability",
                "description": "Check available time slots for a doctor",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "doctor_id": {"type": "string"},
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"}
                    },
                    "required": ["doctor_id", "start_date"]
                }
            }
        ]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool by name."""
        try:
            if tool_name == "get_appointments":
                result = self.get_appointments(
                    arguments["user_id"],
                    arguments.get("start_date"),
                    arguments.get("end_date")
                )
                return {"success": True, "appointments": result}

            elif tool_name == "create_appointment":
                result = self.create_appointment(**arguments)
                return result

            elif tool_name == "update_appointment":
                result = self.update_appointment(
                    arguments["user_id"],
                    arguments["appointment_id"],
                    arguments["updates"]
                )
                return {"success": result}

            elif tool_name == "cancel_appointment":
                result = self.cancel_appointment(
                    arguments["user_id"],
                    arguments["appointment_id"]
                )
                return {"success": result}

            elif tool_name == "sync_to_google_calendar":
                result = self.sync_to_google_calendar(
                    arguments["appointment_id"],
                    arguments.get("user_calendar_id", "primary")
                )
                return result

            elif tool_name == "check_availability":
                result = self.check_availability(
                    arguments["doctor_id"],
                    arguments["start_date"],
                    arguments.get("end_date")
                )
                return {"success": True, "available_slots": result}

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
    server = CalendarMCPServer()

    print("Testing Calendar MCP Server...\n")

    # Test 1: Get appointments
    print("="*60)
    print("TEST 1: Get upcoming appointments")
    print("="*60)
    result = server.call_tool("get_appointments", {
        "user_id": "margaret_thompson"
    })
    if result["success"]:
        appointments = result["appointments"]
        print(f"  Found {len(appointments)} appointments")
        for appt in appointments:
            print(f"    - {appt['title']} on {appt['date']} at {appt['time']}")
    print()

    # Test 2: Create appointment
    print("="*60)
    print("TEST 2: Create new appointment")
    print("="*60)
    result = server.call_tool("create_appointment", {
        "user_id": "margaret_thompson",
        "title": "Annual Checkup",
        "doctor_name": "Dr. James Smith",
        "date": (datetime.now() + timedelta(days=7)).date().isoformat(),
        "time": "10:30",
        "location": "City Health Clinic",
        "notes": "Bring medication list"
    })
    if result["success"]:
        print(f"  ✓ Created appointment ID: {result['appointment_id']}")
        new_appt_id = result["appointment_id"]
    print()

    # Test 3: Check availability
    print("="*60)
    print("TEST 3: Check doctor availability")
    print("="*60)
    result = server.call_tool("check_availability", {
        "doctor_id": "dr_smith",
        "start_date": datetime.now().date().isoformat()
    })
    if result["success"]:
        slots = result["available_slots"]
        print(f"  Found {len(slots)} available slots (showing first 5):")
        for slot in slots[:5]:
            print(f"    - {slot['date']} at {slot['time']}")
    print()

    # Test 4: Sync to Google Calendar
    print("="*60)
    print("TEST 4: Sync to Google Calendar")
    print("="*60)
    if 'new_appt_id' in locals():
        result = server.call_tool("sync_to_google_calendar", {
            "appointment_id": new_appt_id
        })
        print(f"  Sync result: {result.get('message', result)}")
    print()

    print("✓ Calendar MCP Server tests complete!")
