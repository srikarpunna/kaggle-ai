"""
ElderCare Agent - A2A Protocol Module
Agent-to-Agent communication protocol implementation.
"""

from .protocol import (
    A2AProtocol,
    A2AMessage,
    MessageType,
    AgentCapability,
    ExternalAgent,
    request_medication_refill,
    schedule_doctor_appointment,
    notify_family_emergency
)

__all__ = [
    'A2AProtocol',
    'A2AMessage',
    'MessageType',
    'AgentCapability',
    'ExternalAgent',
    'request_medication_refill',
    'schedule_doctor_appointment',
    'notify_family_emergency'
]
