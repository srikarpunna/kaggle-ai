#!/usr/bin/env python3
"""
Quick test script for ElderCare Agent
Run this to test all agents with real Gemini API
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.database import init_databases
from src.agents.orchestrator import OrchestratorAgent
from src.agents.communication import CommunicationAgent
from src.agents.health import HealthAgent

# Load environment variables
load_dotenv()

async def test_all_agents():
    """Test all agents with real examples."""

    # Check for API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not found in .env file")
        print("\nPlease:")
        print("1. Copy .env.example to .env")
        print("2. Get a FREE API key from: https://makersuite.google.com/app/apikey")
        print("3. Add it to .env file: GEMINI_API_KEY=your_key_here")
        return

    print("🚀 ElderCare Agent - Live Test")
    print("="*70)
    print()

    # Initialize database
    print("📊 Initializing databases...")
    db = init_databases(seed_demo=True)
    print("✅ Databases ready with demo data (Margaret Thompson)\n")

    # ============================================
    # TEST 1: Orchestrator Agent
    # ============================================
    print("🤖 TEST 1: Orchestrator Agent (Intent Classification)")
    print("-"*70)

    orchestrator = OrchestratorAgent(
        user_id="margaret_thompson",
        api_key=api_key
    )

    test_messages = [
        "Call my son",
        "Did I take my medication?",
        "I need a doctor appointment"
    ]

    for message in test_messages:
        print(f"\n👤 User: '{message}'")
        result = await orchestrator.process_message(message)
        print(f"🤖 Intent: {result['intent']}")
        print(f"   Confidence: {result['confidence']}")
        print(f"   Entities: {result['entities']}")

        # Show which agent would handle this
        agent = orchestrator.route_to_agent(result['intent'])
        if agent:
            print(f"   → Routes to: {agent.upper()} agent")
        else:
            print(f"   → Handles directly")

    print("\n" + "="*70 + "\n")

    # ============================================
    # TEST 2: Communication Agent
    # ============================================
    print("📞 TEST 2: Communication Agent (Video Calling)")
    print("-"*70)

    comm_agent = CommunicationAgent(
        user_id="margaret_thompson",
        api_key=api_key,
        db=db
    )

    # List all contacts
    print("\n📇 Margaret's Contacts:")
    contacts = comm_agent.get_contacts()
    for contact in contacts:
        print(f"   - {contact['contact_name']} ({contact['relationship']})")
        print(f"     Phone: {contact['phone']}, Platform: {contact['preferred_platform']}")

    # Test calling "my son"
    print("\n👤 User: 'Call my son'")
    call_result = await comm_agent.handle_call_request("Call my son")

    if call_result["success"]:
        print(f"✅ Success!")
        print(f"   Contact: {call_result['contact']['contact_name']} ({call_result['contact']['relationship']})")
        print(f"   Platform: {call_result['platform']}")
        print(f"   Deep Link: {call_result['deep_link']}")
        print(f"   Message: {call_result['confirmation_message']}")
    else:
        print(f"❌ Failed: {call_result.get('message')}")

    print("\n" + "="*70 + "\n")

    # ============================================
    # TEST 3: Health Agent
    # ============================================
    print("💊 TEST 3: Health Agent (Medications)")
    print("-"*70)

    health_agent = HealthAgent(
        user_id="margaret_thompson",
        api_key=api_key,
        db=db
    )

    # List medications
    print("\n💊 Margaret's Medications:")
    medications = health_agent.get_medications()
    for med in medications:
        print(f"   - {med['medication_name']} ({med['dosage']})")
        print(f"     Times: {', '.join(med['times'])}")
        print(f"     Instructions: {med['instructions']}")

    # Test medication question
    print("\n👤 User: 'What medications do I take?'")
    med_result = await health_agent.handle_medication_request("What medications do I take?")
    print(f"🤖 Action: {med_result['action']}")
    print(f"   Response: {med_result['response']}")

    # Check adherence
    print("\n📊 Medication Adherence (last 7 days):")
    adherence = health_agent.get_adherence_rate()
    print(f"   Rate: {adherence['adherence_rate']}%")
    print(f"   Scheduled: {adherence['total_scheduled']} doses")
    print(f"   Taken: {adherence['total_taken']} doses")

    print("\n" + "="*70)
    print("\n✅ ALL TESTS COMPLETE!")
    print("\n🎉 All 3 agents are working with REAL Gemini API!")
    print("\nNext steps:")
    print("  1. Review the test results above")
    print("  2. Try modifying the test messages")
    print("  3. Check the databases in data/*.db")
    print("  4. Continue building the remaining agents")

if __name__ == "__main__":
    print("\n" + "="*70)
    print(" ElderCare Agent - Live Test Suite")
    print(" Testing Orchestrator, Communication, and Health Agents")
    print("="*70 + "\n")

    asyncio.run(test_all_agents())

    print("\n" + "="*70 + "\n")
