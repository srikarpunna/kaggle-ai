"""
ElderCare Agent - Human-in-the-Loop (HITL) System
Flags interactions that require human review for safety and quality.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ReviewPriority(Enum):
    """Priority levels for human review."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewStatus(Enum):
    """Status of a review request."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


@dataclass
class ReviewRequest:
    """Represents a request for human review."""
    request_id: str
    timestamp: str
    session_id: str
    user_message: str
    agent_response: str
    intent: str
    priority: ReviewPriority
    reason: str
    context: Dict[str, Any]
    status: ReviewStatus
    reviewer_id: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[str] = None
    action_taken: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            **asdict(self),
            'priority': self.priority.value,
            'status': self.status.value
        }


class HITLSystem:
    """
    Human-in-the-Loop system for ElderCare Agent.

    Automatically flags interactions that need human review:
    1. Low confidence intent classification (<0.7)
    2. Emergency situations (medical, fall, etc.)
    3. Medication changes or concerns
    4. Calendar conflicts
    5. Unusual user behavior
    6. System errors or failures
    """

    def __init__(self):
        # Queue of pending reviews
        self.pending_reviews: List[ReviewRequest] = []

        # Completed reviews (for audit trail)
        self.completed_reviews: List[ReviewRequest] = []

        # Review thresholds
        self.low_confidence_threshold = 0.7
        self.emergency_keywords = [
            'emergency', 'help', 'pain', 'chest', 'fall', 'fell',
            'dizzy', 'bleeding', 'cant breathe', 'ambulance'
        ]

        logger.info("HITL System initialized")

    def should_flag_for_review(
        self,
        user_message: str,
        agent_response: str,
        intent: str,
        confidence: float = 1.0,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ReviewRequest]:
        """
        Determine if interaction should be flagged for human review.

        Args:
            user_message: User's input
            agent_response: Agent's response
            intent: Classified intent
            confidence: Confidence score (0-1)
            context: Additional context

        Returns:
            ReviewRequest if should be reviewed, None otherwise
        """
        review_reason = None
        priority = ReviewPriority.MEDIUM

        # Check 1: Low confidence intent
        if confidence < self.low_confidence_threshold:
            review_reason = f"Low confidence intent classification: {confidence:.2f}"
            priority = ReviewPriority.MEDIUM

        # Check 2: Emergency keywords
        message_lower = user_message.lower()
        for keyword in self.emergency_keywords:
            if keyword in message_lower:
                review_reason = f"Emergency keyword detected: '{keyword}'"
                priority = ReviewPriority.CRITICAL
                break

        # Check 3: Medication side effects or concerns
        if any(word in message_lower for word in ['side effect', 'dizzy', 'nausea', 'pain after']):
            if context and context.get('intent') == 'MEDICATION':
                review_reason = "Potential medication side effect reported"
                priority = ReviewPriority.HIGH

        # Check 4: Medical advice (should NEVER happen)
        medical_advice_keywords = [
            'you should take', 'i recommend taking', 'this will cure',
            'stop taking', 'increase your dose'
        ]
        response_lower = agent_response.lower()
        for keyword in medical_advice_keywords:
            if keyword in response_lower:
                review_reason = "CRITICAL: Agent may have given medical advice"
                priority = ReviewPriority.CRITICAL
                break

        # Check 5: Failed task completion
        if context and context.get('success') == False:
            review_reason = "Task failed to complete"
            priority = ReviewPriority.MEDIUM

        # Check 6: UNCLEAR intent (user is confused)
        if intent == 'UNCLEAR' and confidence < 0.5:
            review_reason = "User appears confused or frustrated"
            priority = ReviewPriority.LOW

        # Check 7: Repeated failed attempts
        if context and context.get('retry_count', 0) >= 3:
            review_reason = "Multiple failed attempts on same task"
            priority = ReviewPriority.HIGH

        # If any trigger, create review request
        if review_reason:
            return self.create_review_request(
                user_message=user_message,
                agent_response=agent_response,
                intent=intent,
                priority=priority,
                reason=review_reason,
                context=context or {}
            )

        return None

    def create_review_request(
        self,
        user_message: str,
        agent_response: str,
        intent: str,
        priority: ReviewPriority,
        reason: str,
        session_id: str = "unknown",
        context: Optional[Dict[str, Any]] = None
    ) -> ReviewRequest:
        """Create a new review request."""
        request = ReviewRequest(
            request_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            user_message=user_message,
            agent_response=agent_response,
            intent=intent,
            priority=priority,
            reason=reason,
            context=context or {},
            status=ReviewStatus.PENDING
        )

        # Add to pending queue
        self.pending_reviews.append(request)

        # Sort by priority (critical first)
        self.pending_reviews.sort(
            key=lambda r: ['critical', 'high', 'medium', 'low'].index(r.priority.value)
        )

        logger.warning(
            f"Flagged for review ({priority.value}): {reason}",
            extra={
                'request_id': request.request_id,
                'priority': priority.value,
                'intent': intent
            }
        )

        # If critical, also send notification (in production)
        if priority == ReviewPriority.CRITICAL:
            self._send_critical_alert(request)

        return request

    def get_pending_reviews(
        self,
        priority: Optional[ReviewPriority] = None
    ) -> List[ReviewRequest]:
        """
        Get pending review requests.

        Args:
            priority: Optional filter by priority

        Returns:
            List of pending ReviewRequests
        """
        if priority:
            return [r for r in self.pending_reviews if r.priority == priority]
        return self.pending_reviews

    def approve_request(
        self,
        request_id: str,
        reviewer_id: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Approve a review request.

        Args:
            request_id: ID of the request
            reviewer_id: ID of the reviewer
            notes: Optional reviewer notes

        Returns:
            True if approved, False if not found
        """
        request = self._find_request(request_id)

        if not request:
            logger.error(f"Review request not found: {request_id}")
            return False

        request.status = ReviewStatus.APPROVED
        request.reviewer_id = reviewer_id
        request.review_notes = notes
        request.reviewed_at = datetime.now().isoformat()
        request.action_taken = "approved"

        # Move to completed
        self._complete_review(request)

        logger.info(f"Review request approved: {request_id} by {reviewer_id}")
        return True

    def reject_request(
        self,
        request_id: str,
        reviewer_id: str,
        notes: str,
        corrective_action: Optional[str] = None
    ) -> bool:
        """
        Reject a review request.

        Args:
            request_id: ID of the request
            reviewer_id: ID of the reviewer
            notes: Reviewer notes explaining rejection
            corrective_action: What action should be taken

        Returns:
            True if rejected, False if not found
        """
        request = self._find_request(request_id)

        if not request:
            logger.error(f"Review request not found: {request_id}")
            return False

        request.status = ReviewStatus.REJECTED
        request.reviewer_id = reviewer_id
        request.review_notes = notes
        request.reviewed_at = datetime.now().isoformat()
        request.action_taken = corrective_action or "rejected"

        # Move to completed
        self._complete_review(request)

        logger.warning(f"Review request rejected: {request_id} by {reviewer_id}")
        return True

    def escalate_request(
        self,
        request_id: str,
        escalation_reason: str
    ) -> bool:
        """
        Escalate a review request to higher priority/authority.

        Args:
            request_id: ID of the request
            escalation_reason: Why it's being escalated

        Returns:
            True if escalated, False if not found
        """
        request = self._find_request(request_id)

        if not request:
            return False

        request.status = ReviewStatus.ESCALATED
        request.priority = ReviewPriority.CRITICAL
        request.context['escalation_reason'] = escalation_reason
        request.context['escalated_at'] = datetime.now().isoformat()

        logger.critical(f"Review request escalated: {request_id} - {escalation_reason}")

        # Send alert
        self._send_critical_alert(request)

        return True

    def get_statistics(self) -> Dict[str, Any]:
        """Get HITL system statistics."""
        total_reviews = len(self.pending_reviews) + len(self.completed_reviews)

        if not total_reviews:
            return {
                'total_reviews': 0,
                'pending': 0,
                'completed': 0,
                'approval_rate': 0
            }

        approved = sum(1 for r in self.completed_reviews if r.status == ReviewStatus.APPROVED)
        rejected = sum(1 for r in self.completed_reviews if r.status == ReviewStatus.REJECTED)
        escalated = sum(
            1 for r in self.pending_reviews
            if r.status == ReviewStatus.ESCALATED
        )

        by_priority = {
            'critical': len([r for r in self.pending_reviews if r.priority == ReviewPriority.CRITICAL]),
            'high': len([r for r in self.pending_reviews if r.priority == ReviewPriority.HIGH]),
            'medium': len([r for r in self.pending_reviews if r.priority == ReviewPriority.MEDIUM]),
            'low': len([r for r in self.pending_reviews if r.priority == ReviewPriority.LOW])
        }

        return {
            'total_reviews': total_reviews,
            'pending': len(self.pending_reviews),
            'completed': len(self.completed_reviews),
            'approved': approved,
            'rejected': rejected,
            'escalated': escalated,
            'approval_rate': (approved / len(self.completed_reviews) * 100) if self.completed_reviews else 0,
            'by_priority': by_priority,
            'avg_review_time_minutes': self._calculate_avg_review_time()
        }

    def _find_request(self, request_id: str) -> Optional[ReviewRequest]:
        """Find a review request by ID."""
        for request in self.pending_reviews:
            if request.request_id == request_id:
                return request
        return None

    def _complete_review(self, request: ReviewRequest):
        """Move request from pending to completed."""
        if request in self.pending_reviews:
            self.pending_reviews.remove(request)
        self.completed_reviews.append(request)

    def _send_critical_alert(self, request: ReviewRequest):
        """Send alert for critical review requests."""
        logger.critical(
            f"CRITICAL REVIEW REQUIRED: {request.reason}",
            extra={
                'request_id': request.request_id,
                'priority': request.priority.value,
                'user_message': request.user_message
            }
        )

        # In production, this would:
        # - Send email/SMS to on-call reviewer
        # - Post to Slack/Teams channel
        # - Trigger PagerDuty alert
        # - Notify family members if emergency

    def _calculate_avg_review_time(self) -> float:
        """Calculate average review time in minutes."""
        if not self.completed_reviews:
            return 0.0

        total_time = 0
        count = 0

        for review in self.completed_reviews:
            if review.timestamp and review.reviewed_at:
                start = datetime.fromisoformat(review.timestamp)
                end = datetime.fromisoformat(review.reviewed_at)
                total_time += (end - start).total_seconds() / 60
                count += 1

        return total_time / count if count > 0 else 0.0


# Global HITL instance
hitl_system = HITLSystem()


# Convenience functions
def flag_for_review(user_message: str, agent_response: str, intent: str,
                   confidence: float = 1.0, **context) -> Optional[ReviewRequest]:
    """Flag an interaction for human review if needed."""
    return hitl_system.should_flag_for_review(
        user_message, agent_response, intent, confidence, context
    )


def get_pending_reviews(priority: Optional[ReviewPriority] = None) -> List[ReviewRequest]:
    """Get pending review requests."""
    return hitl_system.get_pending_reviews(priority)


def approve_review(request_id: str, reviewer_id: str, notes: Optional[str] = None) -> bool:
    """Approve a review request."""
    return hitl_system.approve_request(request_id, reviewer_id, notes)


def reject_review(request_id: str, reviewer_id: str, notes: str, corrective_action: Optional[str] = None) -> bool:
    """Reject a review request."""
    return hitl_system.reject_request(request_id, reviewer_id, notes, corrective_action)
