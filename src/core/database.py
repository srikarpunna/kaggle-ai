"""
ElderCare Agent - Database Schema and Initialization
Handles SQLite database setup for contacts, health data, calendar, and memory.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class Database:
    """Manages SQLite databases for the ElderCare Agent system."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.contacts_db = self.data_dir / "contacts.db"
        self.health_db = self.data_dir / "health.db"
        self.calendar_db = self.data_dir / "calendar.db"
        self.memory_db = self.data_dir / "memory_bank.db"

    def initialize_all(self):
        """Initialize all databases with proper schemas."""
        logger.info("Initializing all databases...")
        self.initialize_contacts_db()
        self.initialize_health_db()
        self.initialize_calendar_db()
        self.initialize_memory_db()
        logger.info("All databases initialized successfully")

    def initialize_contacts_db(self):
        """Initialize the contacts database."""
        logger.info(f"Initializing contacts database: {self.contacts_db}")

        conn = sqlite3.connect(self.contacts_db)
        cursor = conn.cursor()

        # Contacts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                contact_name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                relationship TEXT,
                preferred_platform TEXT,
                photo_url TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id
            ON contacts(user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_relationship
            ON contacts(user_id, relationship)
        """)

        conn.commit()
        conn.close()
        logger.info("Contacts database initialized")

    def initialize_health_db(self):
        """Initialize the health database."""
        logger.info(f"Initializing health database: {self.health_db}")

        conn = sqlite3.connect(self.health_db)
        cursor = conn.cursor()

        # Medications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                medication_name TEXT NOT NULL,
                dosage TEXT NOT NULL,
                frequency TEXT NOT NULL,
                times TEXT NOT NULL,
                instructions TEXT,
                image_url TEXT,
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Medication logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medication_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                medication_id INTEGER NOT NULL,
                scheduled_time TIMESTAMP NOT NULL,
                taken_at TIMESTAMP,
                status TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (medication_id) REFERENCES medications(id)
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_medication
            ON medication_logs(user_id, medication_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scheduled_time
            ON medication_logs(scheduled_time)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_active_meds
            ON medications(user_id, active)
        """)

        conn.commit()
        conn.close()
        logger.info("Health database initialized")

    def initialize_calendar_db(self):
        """Initialize the calendar database."""
        logger.info(f"Initializing calendar database: {self.calendar_db}")

        conn = sqlite3.connect(self.calendar_db)
        cursor = conn.cursor()

        # Appointments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                doctor_name TEXT,
                date DATE NOT NULL,
                time TIME NOT NULL,
                duration_minutes INTEGER DEFAULT 30,
                location TEXT,
                notes TEXT,
                google_event_id TEXT,
                status TEXT DEFAULT 'scheduled',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Doctors table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS doctors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                specialty TEXT,
                clinic TEXT,
                address TEXT,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_date
            ON appointments(user_id, date)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status
            ON appointments(status)
        """)

        conn.commit()
        conn.close()
        logger.info("Calendar database initialized")

    def initialize_memory_db(self):
        """Initialize the memory bank database."""
        logger.info(f"Initializing memory database: {self.memory_db}")

        conn = sqlite3.connect(self.memory_db)
        cursor = conn.cursor()

        # User sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                context TEXT,
                active BOOLEAN DEFAULT 1
            )
        """)

        # Interaction history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                intent TEXT,
                task_type TEXT,
                input_text TEXT,
                agent_response TEXT,
                task_completed BOOLEAN,
                user_satisfied BOOLEAN,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)

        # Long-term memory table (for learned preferences)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS long_term_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                UNIQUE(user_id, memory_type, key)
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_user
            ON sessions(user_id, active)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_interaction_session
            ON interactions(session_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_lookup
            ON long_term_memory(user_id, memory_type, key)
        """)

        conn.commit()
        conn.close()
        logger.info("Memory database initialized")

    def seed_demo_data(self, user_id: str = "margaret_thompson"):
        """Seed demo data for Margaret Thompson and other common users."""
        logger.info(f"Seeding demo data for user: {user_id}")

        self._seed_contacts(user_id)
        self._seed_medications(user_id)
        self._seed_doctors()
        
        # Also seed for common web session user IDs
        if user_id != "alex":
            self._seed_contacts("alex")
            self._seed_medications("alex")

        logger.info("Demo data seeded successfully")

    def _seed_contacts(self, user_id: str):
        """Seed contact data."""
        conn = sqlite3.connect(self.contacts_db)
        cursor = conn.cursor()

        contacts = [
            {
                "user_id": user_id,
                "contact_name": "John Thompson",
                "phone": "+1-555-0101",
                "email": "john.thompson@email.com",
                "relationship": "son",
                "preferred_platform": "whatsapp",
                "photo_url": "/images/contacts/john.jpg",
                "notes": "Calls every Sunday. Works in finance."
            },
            {
                "user_id": user_id,
                "contact_name": "Sarah Chen",
                "phone": "+1-555-0102",
                "email": "sarah.chen@email.com",
                "relationship": "daughter",
                "preferred_platform": "facetime",
                "photo_url": "/images/contacts/sarah.jpg",
                "notes": "Teacher. Has two kids (Tim and Emma)."
            },
            {
                "user_id": user_id,
                "contact_name": "Tim Chen",
                "phone": "+1-555-0103",
                "email": "tim.chen@email.com",
                "relationship": "grandson",
                "preferred_platform": "facetime",
                "photo_url": "/images/contacts/tim.jpg",
                "notes": "High school student. Loves video games."
            },
            {
                "user_id": user_id,
                "contact_name": "Dr. James Smith",
                "phone": "+1-555-0200",
                "email": "dr.smith@cityhealthclinic.com",
                "relationship": "doctor",
                "preferred_platform": "phone",
                "photo_url": "/images/contacts/dr_smith.jpg",
                "notes": "Primary care physician at City Health Clinic."
            }
        ]

        for contact in contacts:
            cursor.execute("""
                INSERT OR IGNORE INTO contacts
                (user_id, contact_name, phone, email, relationship, preferred_platform, photo_url, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contact["user_id"],
                contact["contact_name"],
                contact["phone"],
                contact["email"],
                contact["relationship"],
                contact["preferred_platform"],
                contact["photo_url"],
                contact["notes"]
            ))

        conn.commit()
        conn.close()
        logger.info(f"Seeded {len(contacts)} contacts")

    def _seed_medications(self, user_id: str):
        """Seed medication data."""
        conn = sqlite3.connect(self.health_db)
        cursor = conn.cursor()

        medications = [
            {
                "user_id": user_id,
                "medication_name": "Lisinopril",
                "dosage": "10 mg",
                "frequency": "once_daily",
                "times": json.dumps(["09:00"]),
                "instructions": "Take with water, with or without food. For blood pressure.",
                "image_url": "/images/medications/lisinopril.png",
                "active": 1
            },
            {
                "user_id": user_id,
                "medication_name": "Metformin",
                "dosage": "500 mg",
                "frequency": "twice_daily",
                "times": json.dumps(["08:00", "18:00"]),
                "instructions": "Take with meals. For blood sugar control.",
                "image_url": "/images/medications/metformin.png",
                "active": 1
            },
            {
                "user_id": user_id,
                "medication_name": "Aspirin",
                "dosage": "81 mg",
                "frequency": "once_daily",
                "times": json.dumps(["09:00"]),
                "instructions": "Take with food to prevent stomach upset.",
                "image_url": "/images/medications/aspirin.png",
                "active": 1
            },
            {
                "user_id": user_id,
                "medication_name": "Vitamin D3",
                "dosage": "2000 IU",
                "frequency": "once_daily",
                "times": json.dumps(["12:00"]),
                "instructions": "Take with a meal containing fat for best absorption.",
                "image_url": "/images/medications/vitamin_d.png",
                "active": 1
            }
        ]

        for med in medications:
            cursor.execute("""
                INSERT OR IGNORE INTO medications
                (user_id, medication_name, dosage, frequency, times, instructions, image_url, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                med["user_id"],
                med["medication_name"],
                med["dosage"],
                med["frequency"],
                med["times"],
                med["instructions"],
                med["image_url"],
                med["active"]
            ))

        conn.commit()
        conn.close()
        logger.info(f"Seeded {len(medications)} medications")

    def _seed_doctors(self):
        """Seed doctor data."""
        conn = sqlite3.connect(self.calendar_db)
        cursor = conn.cursor()

        doctors = [
            {
                "name": "Dr. James Smith",
                "specialty": "Primary Care",
                "clinic": "City Health Clinic",
                "address": "123 Main Street, Suite 204, Springfield, MA 01101",
                "phone": "+1-555-0200"
            }
        ]

        for doctor in doctors:
            cursor.execute("""
                INSERT OR IGNORE INTO doctors
                (name, specialty, clinic, address, phone)
                VALUES (?, ?, ?, ?, ?)
            """, (
                doctor["name"],
                doctor["specialty"],
                doctor["clinic"],
                doctor["address"],
                doctor["phone"]
            ))

        conn.commit()
        conn.close()
        logger.info(f"Seeded {len(doctors)} doctors")

    def get_contacts(self, user_id: str) -> list:
        """Get all contacts for a user."""
        conn = sqlite3.connect(self.contacts_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT contact_name, phone, email, relationship, preferred_platform, notes
            FROM contacts WHERE user_id = ?
        """, (user_id,))
        
        contacts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return contacts
    
    def find_contact_by_relationship(self, user_id: str, relationship: str) -> dict:
        """Find a contact by relationship (son, daughter, doctor, etc.)."""
        conn = sqlite3.connect(self.contacts_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT contact_name, phone, email, relationship, preferred_platform, notes
            FROM contacts WHERE user_id = ? AND LOWER(relationship) = LOWER(?)
        """, (user_id, relationship))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def find_contact_by_name(self, user_id: str, name: str) -> dict:
        """Find a contact by name (partial match)."""
        conn = sqlite3.connect(self.contacts_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT contact_name, phone, email, relationship, preferred_platform, notes
            FROM contacts WHERE user_id = ? AND LOWER(contact_name) LIKE LOWER(?)
        """, (user_id, f"%{name}%"))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None

    def get_connection(self, db_name: str) -> sqlite3.Connection:
        """Get a connection to a specific database."""
        db_map = {
            "contacts": self.contacts_db,
            "health": self.health_db,
            "calendar": self.calendar_db,
            "memory": self.memory_db
        }

        if db_name not in db_map:
            raise ValueError(f"Unknown database: {db_name}")

        return sqlite3.connect(db_map[db_name])


def init_databases(seed_demo: bool = True):
    """Initialize all databases and optionally seed demo data."""
    db = Database()
    db.initialize_all()

    if seed_demo:
        db.seed_demo_data()

    return db


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize databases
    print("Initializing ElderCare Agent databases...")
    db = init_databases(seed_demo=True)
    print("✓ Databases initialized and seeded successfully!")
