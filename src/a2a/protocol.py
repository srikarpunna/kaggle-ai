"""
ElderCare Agent - Agent-to-Agent (A2A) Protocol Implementation
Enables communication between ElderCare Agent and external agents
(pharmacy, doctor's office, emergency services, etc.)

Based on Google's A2A Protocol specification from Day 5.
"""

import os
import json
import uuid
import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """A2A message types."""
    DISCOVER = "discover"
    HANDSHAKE = "handshake"
    REQUEST = "request"
    RESPONSE = "response"
    CALLBACK = "callback"
    ERROR = "error"


class AgentCapability(Enum):
    """Standard agent capabilities."""
    MEDICATION_REFILL = "medication_refill"
    MEDICATION_PRICE_CHECK = "medication_price_check"
    MEDICATION_DELIVERY = "medication_delivery"
    APPOINTMENT_SCHEDULE = "appointment_schedule"
    APPOINTMENT_RESCHEDULE = "appointment_reschedule"
    APPOINTMENT_CANCEL = "appointment_cancel"
    MEDICAL_RECORDS = "medical_records"
    EMERGENCY_CALL = "emergency_call"
    FAMILY_NOTIFICATION = "family_notification"


@dataclass
class A2AMessage:
    """Standard A2A Protocol message."""
    message_id: str
    message_type: MessageType
    sender_id: str
    receiver_id: str
    timestamp: str
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None  # For request-response correlation
    callback_url: Optional[str] = None  # For async responses

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message_id': self.message_id,
            'message_type': self.message_type.value,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'timestamp': self.timestamp,
            'payload': self.payload,
            'correlation_id': self.correlation_id,
            'callback_url': self.callback_url
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'A2AMessage':
        """Create from dictionary."""
        return cls(
            message_id=data['message_id'],
            message_type=MessageType(data['message_type']),
            sender_id=data['sender_id'],
            receiver_id=data['receiver_id'],
            timestamp=data['timestamp'],
            payload=data['payload'],
            correlation_id=data.get('correlation_id'),
            callback_url=data.get('callback_url')
        )


@dataclass
class ExternalAgent:
    """Represents an external agent in the A2A network."""
    agent_id: str
    agent_name: str
    agent_type: str  # pharmacy, doctor, emergency, etc.
    capabilities: List[AgentCapability]
    endpoint_url: str
    api_key: Optional[str] = None
    timeout_seconds: int = 30
    active: bool = True


class A2AProtocol:
    """
    Agent-to-Agent Protocol implementation.

    Handles:
    - Agent discovery
    - Secure handshakes
    - Message exchange (request/response)
    - Asynchronous callbacks
    - Error handling
    """

    def __init__(self, agent_id: str, agent_name: str):
        self.agent_id = agent_id
        self.agent_name = agent_name

        # Registry of known external agents
        self.agent_registry: Dict[str, ExternalAgent] = {}

        # Pending requests (waiting for responses)
        self.pending_requests: Dict[str, A2AMessage] = {}

        # Received callbacks
        self.received_callbacks: List[A2AMessage] = []

        # Load agents from registry
        self.load_agent_registry()

    def load_agent_registry(self):
        """Load external agents from registry file."""
        registry_file = os.path.join(
            os.path.dirname(__file__), 'agents_registry.yaml'
        )

        if not os.path.exists(registry_file):
            logger.warning(f"Agent registry not found: {registry_file}")
            return

        try:
            import yaml
            with open(registry_file, 'r') as f:
                registry_data = yaml.safe_load(f)

            for agent_id, agent_config in registry_data.get('agents', {}).items():
                capabilities = [
                    AgentCapability(cap) for cap in agent_config.get('capabilities', [])
                ]

                agent = ExternalAgent(
                    agent_id=agent_id,
                    agent_name=agent_config.get('name', agent_id),
                    agent_type=agent_config.get('type', 'unknown'),
                    capabilities=capabilities,
                    endpoint_url=agent_config.get('url', ''),
                    api_key=agent_config.get('api_key'),
                    active=agent_config.get('active', True)
                )

                self.agent_registry[agent_id] = agent

            logger.info(f"Loaded {len(self.agent_registry)} external agents")

        except Exception as e:
            logger.error(f"Failed to load agent registry: {e}")

    def discover_agents(self, capability: AgentCapability) -> List[ExternalAgent]:
        """
        Discover agents with a specific capability.

        Args:
            capability: Required capability

        Returns:
            List of agents that support the capability
        """
        matching_agents = [
            agent for agent in self.agent_registry.values()
            if capability in agent.capabilities and agent.active
        ]

        logger.info(f"Discovered {len(matching_agents)} agents for {capability.value}")
        return matching_agents

    async def send_request(
        self,
        receiver_id: str,
        action: str,
        parameters: Dict[str, Any],
        callback_url: Optional[str] = None
    ) -> Optional[A2AMessage]:
        """
        Send a request to an external agent.

        Args:
            receiver_id: Target agent ID
            action: Action to perform
            parameters: Action parameters
            callback_url: Optional callback URL for async response

        Returns:
            Response message (if synchronous) or None (if async)
        """
        # Check if agent exists
        agent = self.agent_registry.get(receiver_id)
        if not agent:
            logger.error(f"Agent not found: {receiver_id}")
            return None

        # Create request message
        message_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())

        request = A2AMessage(
            message_id=message_id,
            message_type=MessageType.REQUEST,
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            timestamp=datetime.now().isoformat(),
            payload={
                'action': action,
                'parameters': parameters
            },
            correlation_id=correlation_id,
            callback_url=callback_url
        )

        # Store pending request
        self.pending_requests[correlation_id] = request

        logger.info(f"Sending A2A request to {receiver_id}: {action}")

        try:
            # Send request to external agent
            response = await self._send_http_request(agent, request)

            if response:
                logger.info(f"Received response from {receiver_id}")
                # Remove from pending
                del self.pending_requests[correlation_id]
                return response
            else:
                logger.info(f"Request sent to {receiver_id}, waiting for callback")
                return None

        except Exception as e:
            logger.error(f"A2A request failed: {e}")
            # Clean up pending request
            if correlation_id in self.pending_requests:
                del self.pending_requests[correlation_id]
            return None

    async def _send_http_request(
        self,
        agent: ExternalAgent,
        message: A2AMessage
    ) -> Optional[A2AMessage]:
        """
        Send HTTP request to external agent.

        NOTE: For this demo, we're using mock agents that return
        simulated responses instead of real HTTP calls.
        """
        # For demo purposes, use mock agents
        from .mock_agents import get_mock_agent_response

        try:
            response_payload = await get_mock_agent_response(
                agent.agent_id,
                message.payload
            )

            if response_payload:
                # Create response message
                response = A2AMessage(
                    message_id=str(uuid.uuid4()),
                    message_type=MessageType.RESPONSE,
                    sender_id=agent.agent_id,
                    receiver_id=self.agent_id,
                    timestamp=datetime.now().isoformat(),
                    payload=response_payload,
                    correlation_id=message.correlation_id
                )

                return response

        except Exception as e:
            logger.error(f"HTTP request to {agent.agent_id} failed: {e}")

        return None

    async def handle_callback(self, message: A2AMessage):
        """
        Handle asynchronous callback from external agent.

        Args:
            message: Callback message
        """
        logger.info(f"Received callback from {message.sender_id}")

        # Store callback
        self.received_callbacks.append(message)

        # Find original request
        original_request = self.pending_requests.get(message.correlation_id)

        if original_request:
            logger.info(f"Matched callback to request {message.correlation_id}")
            # Remove from pending
            del self.pending_requests[message.correlation_id]
        else:
            logger.warning(f"No matching request for callback {message.correlation_id}")

    def get_agent_info(self, agent_id: str) -> Optional[ExternalAgent]:
        """Get information about an external agent."""
        return self.agent_registry.get(agent_id)

    def list_agents(self, agent_type: Optional[str] = None) -> List[ExternalAgent]:
        """
        List all registered agents.

        Args:
            agent_type: Optional filter by type (pharmacy, doctor, etc.)

        Returns:
            List of agents
        """
        agents = list(self.agent_registry.values())

        if agent_type:
            agents = [a for a in agents if a.agent_type == agent_type]

        return agents


# Convenience functions for common A2A interactions
async def request_medication_refill(
    protocol: A2AProtocol,
    medication_name: str,
    patient_name: str,
    prescription_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Request medication refill from pharmacy agent.

    Returns:
        Dict with refill info (status, cost, pickup_time) or None
    """
    # Find pharmacy agents
    pharmacy_agents = protocol.discover_agents(AgentCapability.MEDICATION_REFILL)

    if not pharmacy_agents:
        logger.error("No pharmacy agents available")
        return None

    # Use first available pharmacy
    pharmacy = pharmacy_agents[0]

    # Send request
    response = await protocol.send_request(
        receiver_id=pharmacy.agent_id,
        action='refill_medication',
        parameters={
            'medication_name': medication_name,
            'patient_name': patient_name,
            'prescription_id': prescription_id
        }
    )

    if response and response.payload.get('success'):
        return response.payload.get('data')

    return None


async def schedule_doctor_appointment(
    protocol: A2AProtocol,
    doctor_name: str,
    patient_name: str,
    preferred_date: str,
    preferred_time: str
) -> Optional[Dict[str, Any]]:
    """
    Schedule appointment with doctor's office agent.

    Returns:
        Dict with appointment info (confirmed_datetime, location) or None
    """
    # Find doctor office agents
    doctor_agents = protocol.discover_agents(AgentCapability.APPOINTMENT_SCHEDULE)

    if not doctor_agents:
        logger.error("No doctor office agents available")
        return None

    # Use first available doctor office
    doctor_office = doctor_agents[0]

    # Send request
    response = await protocol.send_request(
        receiver_id=doctor_office.agent_id,
        action='schedule_appointment',
        parameters={
            'doctor_name': doctor_name,
            'patient_name': patient_name,
            'preferred_date': preferred_date,
            'preferred_time': preferred_time
        }
    )

    if response and response.payload.get('success'):
        return response.payload.get('data')

    return None


async def notify_family_emergency(
    protocol: A2AProtocol,
    patient_name: str,
    emergency_type: str,
    location: str,
    family_contacts: List[Dict[str, str]]
) -> bool:
    """
    Notify family members via emergency notification agent.

    Returns:
        True if notifications sent successfully
    """
    # Find emergency notification agents
    emergency_agents = protocol.discover_agents(AgentCapability.FAMILY_NOTIFICATION)

    if not emergency_agents:
        logger.error("No emergency notification agents available")
        return False

    # Use first available emergency agent
    emergency_agent = emergency_agents[0]

    # Send request
    response = await protocol.send_request(
        receiver_id=emergency_agent.agent_id,
        action='notify_family',
        parameters={
            'patient_name': patient_name,
            'emergency_type': emergency_type,
            'location': location,
            'contacts': family_contacts
        }
    )

    return response is not None and response.payload.get('success', False)
