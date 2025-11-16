"""
ElderCare Agent - Observability System
Implements structured logging, distributed tracing, and metrics collection
for comprehensive agent monitoring and debugging.
"""

import logging
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import threading

# Thread-local storage for trace context
_trace_context = threading.local()


@dataclass
class TraceSpan:
    """Represents a trace span in the agent execution."""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    name: str
    start_time: float
    end_time: Optional[float]
    agent_name: Optional[str]
    operation: str
    metadata: Dict[str, Any]
    error: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary."""
        return asdict(self)

    @property
    def duration_ms(self) -> Optional[float]:
        """Get span duration in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None


class ObservabilityLogger:
    """
    Centralized observability system for ElderCare Agent.

    Features:
    - Structured logging with trace context
    - Distributed tracing across agents
    - Performance metrics collection
    - Error tracking and alerting
    """

    def __init__(self, log_level: str = "INFO"):
        self.logger = logging.getLogger("eldercare.observability")
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Configure structured JSON logging
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # Storage for traces and metrics
        self.traces: Dict[str, List[TraceSpan]] = {}
        self.active_spans: Dict[str, TraceSpan] = {}
        self.metrics: Dict[str, List[Dict[str, Any]]] = {
            'agent_calls': [],
            'response_times': [],
            'errors': [],
            'token_usage': [],
            'user_interactions': []
        }

        # Performance thresholds
        self.slow_request_threshold_ms = 2000
        self.error_alert_threshold = 5

    def start_trace(self, operation: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Start a new trace for a user interaction.

        Args:
            operation: Name of the operation (e.g., "process_message")
            metadata: Additional context (user_id, session_id, etc.)

        Returns:
            trace_id: Unique identifier for this trace
        """
        trace_id = str(uuid.uuid4())
        _trace_context.trace_id = trace_id
        _trace_context.span_stack = []

        self.traces[trace_id] = []

        self.logger.info(
            f"TRACE_START: {operation}",
            extra={
                'trace_id': trace_id,
                'operation': operation,
                'metadata': metadata or {}
            }
        )

        return trace_id

    def end_trace(self, trace_id: str, success: bool = True, error: Optional[str] = None):
        """
        End a trace and log summary.

        Args:
            trace_id: The trace identifier
            success: Whether the operation succeeded
            error: Error message if failed
        """
        if trace_id not in self.traces:
            self.logger.warning(f"Trace {trace_id} not found")
            return

        spans = self.traces[trace_id]
        total_duration_ms = sum(span.duration_ms or 0 for span in spans)

        # Log trace summary
        self.logger.info(
            f"TRACE_END: {trace_id}",
            extra={
                'trace_id': trace_id,
                'success': success,
                'total_duration_ms': total_duration_ms,
                'span_count': len(spans),
                'error': error
            }
        )

        # Alert on slow requests
        if total_duration_ms > self.slow_request_threshold_ms:
            self.logger.warning(
                f"SLOW_REQUEST: {total_duration_ms:.2f}ms",
                extra={'trace_id': trace_id}
            )

        # Clean up context
        if hasattr(_trace_context, 'trace_id'):
            delattr(_trace_context, 'trace_id')
        if hasattr(_trace_context, 'span_stack'):
            delattr(_trace_context, 'span_stack')

    @contextmanager
    def span(self, name: str, agent_name: Optional[str] = None,
             operation: str = "unknown", **metadata):
        """
        Context manager for creating a trace span.

        Usage:
            with observability.span("classify_intent", agent_name="orchestrator"):
                result = orchestrator.classify(message)
        """
        # Get current trace context
        trace_id = getattr(_trace_context, 'trace_id', None)
        if not trace_id:
            # Auto-create trace if not exists
            trace_id = self.start_trace(operation)

        # Get parent span
        span_stack = getattr(_trace_context, 'span_stack', [])
        parent_span_id = span_stack[-1] if span_stack else None

        # Create new span
        span_id = str(uuid.uuid4())
        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            start_time=time.time(),
            end_time=None,
            agent_name=agent_name,
            operation=operation,
            metadata=metadata,
            error=None
        )

        # Push to stack
        span_stack.append(span_id)
        _trace_context.span_stack = span_stack
        self.active_spans[span_id] = span

        self.logger.debug(
            f"SPAN_START: {name}",
            extra={
                'trace_id': trace_id,
                'span_id': span_id,
                'parent_span_id': parent_span_id,
                'agent_name': agent_name,
                'operation': operation
            }
        )

        try:
            yield span
        except Exception as e:
            # Capture error in span
            span.error = str(e)
            self.logger.error(
                f"SPAN_ERROR: {name} - {str(e)}",
                extra={
                    'trace_id': trace_id,
                    'span_id': span_id,
                    'error': str(e)
                },
                exc_info=True
            )
            raise
        finally:
            # End span
            span.end_time = time.time()
            duration_ms = span.duration_ms

            # Pop from stack
            span_stack.pop()
            _trace_context.span_stack = span_stack

            # Store span
            if trace_id in self.traces:
                self.traces[trace_id].append(span)

            # Remove from active spans
            del self.active_spans[span_id]

            self.logger.debug(
                f"SPAN_END: {name} ({duration_ms:.2f}ms)",
                extra={
                    'trace_id': trace_id,
                    'span_id': span_id,
                    'duration_ms': duration_ms,
                    'error': span.error
                }
            )

    def log_agent_call(self, agent_name: str, operation: str,
                       input_data: Any, output_data: Any,
                       duration_ms: float, success: bool = True):
        """
        Log an agent function call.

        Args:
            agent_name: Name of the agent
            operation: Operation performed
            input_data: Input to the agent
            output_data: Output from the agent
            duration_ms: Execution time in milliseconds
            success: Whether the call succeeded
        """
        trace_id = getattr(_trace_context, 'trace_id', 'no_trace')

        metric = {
            'timestamp': datetime.now().isoformat(),
            'trace_id': trace_id,
            'agent_name': agent_name,
            'operation': operation,
            'duration_ms': duration_ms,
            'success': success,
            'input_preview': str(input_data)[:100] if input_data else None,
            'output_preview': str(output_data)[:100] if output_data else None
        }

        self.metrics['agent_calls'].append(metric)

        self.logger.info(
            f"AGENT_CALL: {agent_name}.{operation} ({duration_ms:.2f}ms)",
            extra=metric
        )

    def log_llm_call(self, model: str, prompt_tokens: int,
                     completion_tokens: int, duration_ms: float):
        """
        Log an LLM API call for token tracking.

        Args:
            model: Model name (e.g., "gemini-2.0-flash")
            prompt_tokens: Input token count
            completion_tokens: Output token count
            duration_ms: API call duration
        """
        trace_id = getattr(_trace_context, 'trace_id', 'no_trace')

        metric = {
            'timestamp': datetime.now().isoformat(),
            'trace_id': trace_id,
            'model': model,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': prompt_tokens + completion_tokens,
            'duration_ms': duration_ms
        }

        self.metrics['token_usage'].append(metric)

        self.logger.info(
            f"LLM_CALL: {model} ({prompt_tokens + completion_tokens} tokens, {duration_ms:.2f}ms)",
            extra=metric
        )

    def log_error(self, error_type: str, error_message: str,
                  context: Optional[Dict[str, Any]] = None):
        """
        Log an error with context.

        Args:
            error_type: Type of error
            error_message: Error message
            context: Additional context
        """
        trace_id = getattr(_trace_context, 'trace_id', 'no_trace')

        error_record = {
            'timestamp': datetime.now().isoformat(),
            'trace_id': trace_id,
            'error_type': error_type,
            'error_message': error_message,
            'context': context or {}
        }

        self.metrics['errors'].append(error_record)

        self.logger.error(
            f"ERROR: {error_type} - {error_message}",
            extra=error_record
        )

        # Alert if too many errors
        recent_errors = [
            e for e in self.metrics['errors']
            if datetime.fromisoformat(e['timestamp']) >
               datetime.now().replace(hour=datetime.now().hour - 1)
        ]
        if len(recent_errors) >= self.error_alert_threshold:
            self.logger.critical(
                f"HIGH_ERROR_RATE: {len(recent_errors)} errors in last hour"
            )

    def log_user_interaction(self, session_id: str, user_message: str,
                            agent_response: str, intent: str,
                            satisfaction_score: Optional[float] = None):
        """
        Log a user interaction for quality tracking.

        Args:
            session_id: User session ID
            user_message: User's input
            agent_response: Agent's response
            intent: Classified intent
            satisfaction_score: Optional satisfaction score (0-1)
        """
        trace_id = getattr(_trace_context, 'trace_id', 'no_trace')

        interaction = {
            'timestamp': datetime.now().isoformat(),
            'trace_id': trace_id,
            'session_id': session_id,
            'user_message': user_message,
            'agent_response': agent_response,
            'intent': intent,
            'satisfaction_score': satisfaction_score
        }

        self.metrics['user_interactions'].append(interaction)

        self.logger.info(
            f"USER_INTERACTION: {intent}",
            extra=interaction
        )

    def get_trace(self, trace_id: str) -> Optional[List[TraceSpan]]:
        """Get all spans for a trace."""
        return self.traces.get(trace_id)

    def get_trace_graph(self, trace_id: str) -> Dict[str, Any]:
        """
        Generate a visual representation of the trace graph.

        Returns:
            Dictionary suitable for visualization (e.g., with D3.js)
        """
        spans = self.get_trace(trace_id)
        if not spans:
            return {}

        nodes = []
        edges = []

        for span in spans:
            nodes.append({
                'id': span.span_id,
                'name': span.name,
                'agent': span.agent_name,
                'duration_ms': span.duration_ms,
                'error': span.error
            })

            if span.parent_span_id:
                edges.append({
                    'source': span.parent_span_id,
                    'target': span.span_id
                })

        return {
            'trace_id': trace_id,
            'nodes': nodes,
            'edges': edges
        }

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get summary of all metrics.

        Returns:
            Dictionary with key metrics and statistics
        """
        agent_calls = self.metrics['agent_calls']
        token_usage = self.metrics['token_usage']
        errors = self.metrics['errors']
        interactions = self.metrics['user_interactions']

        return {
            'agent_calls': {
                'total': len(agent_calls),
                'avg_duration_ms': sum(c['duration_ms'] for c in agent_calls) / len(agent_calls) if agent_calls else 0,
                'success_rate': sum(1 for c in agent_calls if c['success']) / len(agent_calls) if agent_calls else 0,
                'by_agent': self._group_by(agent_calls, 'agent_name')
            },
            'token_usage': {
                'total_tokens': sum(t['total_tokens'] for t in token_usage),
                'total_calls': len(token_usage),
                'avg_tokens_per_call': sum(t['total_tokens'] for t in token_usage) / len(token_usage) if token_usage else 0
            },
            'errors': {
                'total': len(errors),
                'by_type': self._group_by(errors, 'error_type')
            },
            'user_interactions': {
                'total': len(interactions),
                'by_intent': self._group_by(interactions, 'intent'),
                'avg_satisfaction': sum(i.get('satisfaction_score', 0) for i in interactions) / len(interactions) if interactions else 0
            },
            'traces': {
                'total': len(self.traces),
                'active_spans': len(self.active_spans)
            }
        }

    def _group_by(self, items: List[Dict], key: str) -> Dict[str, int]:
        """Group items by a key and count."""
        result = {}
        for item in items:
            value = item.get(key, 'unknown')
            result[value] = result.get(value, 0) + 1
        return result

    def export_metrics(self, format: str = 'json') -> str:
        """
        Export all metrics in specified format.

        Args:
            format: Export format ('json', 'csv')

        Returns:
            Formatted metrics string
        """
        if format == 'json':
            return json.dumps({
                'summary': self.get_metrics_summary(),
                'raw_metrics': self.metrics,
                'traces': {
                    tid: [span.to_dict() for span in spans]
                    for tid, spans in self.traces.items()
                }
            }, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported format: {format}")


# Global observability instance
observability = ObservabilityLogger()


# Convenience functions
def start_trace(operation: str, **metadata) -> str:
    """Start a new trace."""
    return observability.start_trace(operation, metadata)


def end_trace(trace_id: str, success: bool = True, error: Optional[str] = None):
    """End a trace."""
    observability.end_trace(trace_id, success, error)


def span(name: str, **kwargs):
    """Create a trace span context manager."""
    return observability.span(name, **kwargs)


def log_agent_call(agent_name: str, operation: str, input_data: Any,
                   output_data: Any, duration_ms: float, success: bool = True):
    """Log an agent call."""
    observability.log_agent_call(agent_name, operation, input_data,
                                 output_data, duration_ms, success)


def log_llm_call(model: str, prompt_tokens: int, completion_tokens: int, duration_ms: float):
    """Log an LLM call."""
    observability.log_llm_call(model, prompt_tokens, completion_tokens, duration_ms)


def log_error(error_type: str, error_message: str, **context):
    """Log an error."""
    observability.log_error(error_type, error_message, context)


def log_user_interaction(session_id: str, user_message: str, agent_response: str,
                         intent: str, satisfaction_score: Optional[float] = None):
    """Log a user interaction."""
    observability.log_user_interaction(session_id, user_message, agent_response,
                                       intent, satisfaction_score)


def get_metrics_summary() -> Dict[str, Any]:
    """Get metrics summary."""
    return observability.get_metrics_summary()
