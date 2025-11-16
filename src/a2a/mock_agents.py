"""
ElderCare Agent - Mock External Agents
Simulates responses from external agents for demonstration purposes.

In production, these would be replaced with real HTTP calls to actual
pharmacy APIs, doctor office systems, etc.
"""

import asyncio
import random
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


async def get_mock_agent_response(
    agent_id: str,
    request_payload: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Generate mock response from external agent.

    Args:
        agent_id: ID of the external agent
        request_payload: Request payload with action and parameters

    Returns:
        Response payload or None
    """
    action = request_payload.get('action')
    parameters = request_payload.get('parameters', {})

    # Simulate network delay
    await asyncio.sleep(random.uniform(0.1, 0.5))

    # Route to appropriate handler
    if 'pharmacy' in agent_id:
        return await handle_pharmacy_request(agent_id, action, parameters)
    elif 'doctor_office' in agent_id:
        return await handle_doctor_office_request(agent_id, action, parameters)
    elif 'emergency' in agent_id:
        return await handle_emergency_request(agent_id, action, parameters)
    elif 'family_notification' in agent_id:
        return await handle_family_notification_request(agent_id, action, parameters)
    else:
        return {
            'success': False,
            'error': f'Unknown agent: {agent_id}'
        }


async def handle_pharmacy_request(
    agent_id: str,
    action: str,
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle pharmacy agent requests."""

    if action == 'refill_medication':
        medication_name = parameters.get('medication_name', '')
        patient_name = parameters.get('patient_name', '')

        # Simulate medication database lookup
        medications_db = {
            'lisinopril': {
                'name': 'Lisinopril',
                'dosage': '10mg',
                'refills_available': 3,
                'cost': 12.50,
                'insurance_covered': True
            },
            'metformin': {
                'name': 'Metformin',
                'dosage': '500mg',
                'refills_available': 2,
                'cost': 8.99,
                'insurance_covered': True
            },
            'atorvastatin': {
                'name': 'Atorvastatin',
                'dosage': '20mg',
                'refills_available': 1,
                'cost': 15.00,
                'insurance_covered': True
            },
            'vitamin d': {
                'name': 'Vitamin D3',
                'dosage': '1000 IU',
                'refills_available': 0,  # Over-the-counter
                'cost': 6.99,
                'insurance_covered': False
            }
        }

        # Search for medication (case-insensitive)
        medication_key = medication_name.lower().replace(' ', '')
        for key, med_info in medications_db.items():
            if medication_key in key.replace(' ', ''):
                # Generate pickup time (2-3 hours from now)
                pickup_time = datetime.now() + timedelta(hours=random.randint(2, 3))

                return {
                    'success': True,
                    'data': {
                        'medication': med_info['name'],
                        'dosage': med_info['dosage'],
                        'refills_available': med_info['refills_available'],
                        'cost': med_info['cost'],
                        'insurance_covered': med_info['insurance_covered'],
                        'final_cost': 0 if med_info['insurance_covered'] else med_info['cost'],
                        'status': 'approved',
                        'ready_time': pickup_time.strftime('%I:%M %p'),
                        'pickup_location': 'CVS Pharmacy - 123 Main St',
                        'order_id': f'RX{random.randint(100000, 999999)}'
                    },
                    'message': f"Your {med_info['name']} refill is approved and will be ready for pickup at {pickup_time.strftime('%I:%M %p')}."
                }

        # Medication not found
        return {
            'success': False,
            'error': f'Medication "{medication_name}" not found in our system',
            'message': f"I couldn't find {medication_name} in your prescription history. Please contact your doctor to get a new prescription."
        }

    elif action == 'price_check':
        medication_name = parameters.get('medication_name', '')

        # Return mock pricing
        base_price = random.uniform(5.0, 50.0)
        insurance_price = base_price * 0.1  # 90% covered

        return {
            'success': True,
            'data': {
                'medication': medication_name,
                'retail_price': round(base_price, 2),
                'insurance_price': round(insurance_price, 2),
                'savings': round(base_price - insurance_price, 2)
            }
        }

    elif action == 'delivery':
        return {
            'success': True,
            'data': {
                'delivery_available': True,
                'delivery_fee': 4.99,
                'estimated_delivery': '2-3 hours',
                'delivery_address': parameters.get('address', '123 Main St')
            }
        }

    else:
        return {
            'success': False,
            'error': f'Unknown pharmacy action: {action}'
        }


async def handle_doctor_office_request(
    agent_id: str,
    action: str,
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle doctor's office agent requests."""

    if action == 'schedule_appointment':
        doctor_name = parameters.get('doctor_name', 'Dr. Smith')
        patient_name = parameters.get('patient_name', '')
        preferred_date = parameters.get('preferred_date', '')
        preferred_time = parameters.get('preferred_time', '')

        # Simulate availability check
        available_slots = [
            {'date': preferred_date, 'time': '10:00 AM', 'available': True},
            {'date': preferred_date, 'time': '2:00 PM', 'available': True},
            {'date': preferred_date, 'time': '4:30 PM', 'available': False}
        ]

        # Check if preferred time is available
        time_available = any(
            slot['time'].lower().replace(' ', '') == preferred_time.lower().replace(' ', '')
            and slot['available']
            for slot in available_slots
        )

        if time_available or not preferred_time:
            # Confirm appointment
            confirmed_time = preferred_time if time_available else '10:00 AM'

            return {
                'success': True,
                'data': {
                    'appointment_id': f'APT{random.randint(10000, 99999)}',
                    'doctor': doctor_name,
                    'patient': patient_name,
                    'date': preferred_date,
                    'time': confirmed_time,
                    'duration_minutes': 30,
                    'location': 'Medical Center - Room 204',
                    'address': '456 Healthcare Blvd, Suite 100',
                    'phone': '(555) 123-4567',
                    'status': 'confirmed',
                    'instructions': 'Please arrive 15 minutes early for check-in'
                },
                'message': f"Your appointment with {doctor_name} is confirmed for {preferred_date} at {confirmed_time}."
            }
        else:
            # Suggest alternative times
            alternatives = [slot for slot in available_slots if slot['available']]

            return {
                'success': False,
                'error': f'{preferred_time} is not available',
                'data': {
                    'available_slots': alternatives
                },
                'message': f"Sorry, {preferred_time} is not available. Here are some alternative times: {', '.join(s['time'] for s in alternatives)}"
            }

    elif action == 'reschedule':
        appointment_id = parameters.get('appointment_id', '')

        return {
            'success': True,
            'data': {
                'appointment_id': appointment_id,
                'status': 'rescheduled',
                'new_date': parameters.get('new_date'),
                'new_time': parameters.get('new_time')
            },
            'message': 'Your appointment has been rescheduled successfully.'
        }

    elif action == 'cancel':
        appointment_id = parameters.get('appointment_id', '')

        return {
            'success': True,
            'data': {
                'appointment_id': appointment_id,
                'status': 'cancelled'
            },
            'message': 'Your appointment has been cancelled.'
        }

    else:
        return {
            'success': False,
            'error': f'Unknown doctor office action: {action}'
        }


async def handle_emergency_request(
    agent_id: str,
    action: str,
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle emergency services agent requests."""

    if action == 'emergency_call':
        emergency_type = parameters.get('emergency_type', 'general')
        location = parameters.get('location', 'unknown')

        return {
            'success': True,
            'data': {
                'call_initiated': True,
                'emergency_type': emergency_type,
                'location': location,
                'response_time_minutes': random.randint(5, 15),
                'incident_id': f'EMG{random.randint(100000, 999999)}',
                'dispatcher_message': 'Help is on the way. Stay calm.'
            },
            'message': f'Emergency services have been notified. Help is on the way to {location}.'
        }

    else:
        return {
            'success': False,
            'error': f'Unknown emergency action: {action}'
        }


async def handle_family_notification_request(
    agent_id: str,
    action: str,
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle family notification agent requests."""

    if action == 'notify_family':
        patient_name = parameters.get('patient_name', '')
        emergency_type = parameters.get('emergency_type', '')
        location = parameters.get('location', '')
        contacts = parameters.get('contacts', [])

        # Simulate sending notifications
        notifications_sent = []

        for contact in contacts:
            notifications_sent.append({
                'name': contact.get('name', ''),
                'phone': contact.get('phone', ''),
                'method': 'SMS',
                'status': 'delivered',
                'timestamp': datetime.now().isoformat()
            })

        return {
            'success': True,
            'data': {
                'patient': patient_name,
                'emergency_type': emergency_type,
                'location': location,
                'notifications_sent': len(notifications_sent),
                'delivery_status': notifications_sent
            },
            'message': f'Notified {len(notifications_sent)} family members about {emergency_type}.'
        }

    else:
        return {
            'success': False,
            'error': f'Unknown notification action: {action}'
        }


# Example usage and testing
if __name__ == '__main__':
    async def test_mock_agents():
        """Test mock agents."""
        print("Testing Mock Agents\n")

        # Test pharmacy refill
        print("1. Testing Pharmacy Refill...")
        pharmacy_response = await get_mock_agent_response(
            'pharmacy_cvs',
            {
                'action': 'refill_medication',
                'parameters': {
                    'medication_name': 'Lisinopril',
                    'patient_name': 'Margaret Thompson'
                }
            }
        )
        print(f"   Result: {pharmacy_response.get('message')}")
        print(f"   Cost: ${pharmacy_response['data']['cost']}")
        print()

        # Test doctor appointment
        print("2. Testing Doctor Appointment...")
        doctor_response = await get_mock_agent_response(
            'doctor_office_primary',
            {
                'action': 'schedule_appointment',
                'parameters': {
                    'doctor_name': 'Dr. Smith',
                    'patient_name': 'Margaret Thompson',
                    'preferred_date': 'November 25, 2024',
                    'preferred_time': '10:00 AM'
                }
            }
        )
        print(f"   Result: {doctor_response.get('message')}")
        print(f"   Appointment ID: {doctor_response['data']['appointment_id']}")
        print()

        # Test family notification
        print("3. Testing Family Notification...")
        family_response = await get_mock_agent_response(
            'family_notification',
            {
                'action': 'notify_family',
                'parameters': {
                    'patient_name': 'Margaret Thompson',
                    'emergency_type': 'fall',
                    'location': 'Home',
                    'contacts': [
                        {'name': 'John Thompson', 'phone': '+1234567890'},
                        {'name': 'Sarah Thompson', 'phone': '+0987654321'}
                    ]
                }
            }
        )
        print(f"   Result: {family_response.get('message')}")
        print()

    asyncio.run(test_mock_agents())
