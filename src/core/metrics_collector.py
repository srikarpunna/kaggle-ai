"""
ElderCare Agent - Metrics Collector
Real-time metrics collection and aggregation for monitoring agent performance.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from collections import defaultdict, deque
import threading


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: datetime
    value: float
    labels: Dict[str, str]


class MetricsCollector:
    """
    Collects and aggregates metrics for real-time monitoring.

    Metrics Categories:
    - Performance: Response time, latency, throughput
    - Quality: Success rate, error rate, satisfaction scores
    - Usage: API calls, token consumption, cache hits
    - Business: Task completion rate, user engagement
    """

    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)

        self.lock = threading.Lock()

        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_old_metrics, daemon=True)
        self.cleanup_thread.start()

    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a metric value."""
        with self.lock:
            metric = MetricPoint(
                timestamp=datetime.now(),
                value=value,
                labels=labels or {}
            )
            self.metrics[name].append(metric)

    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        key = self._make_key(name, labels)
        with self.lock:
            self.counters[key] += value

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        key = self._make_key(name, labels)
        with self.lock:
            self.gauges[key] = value

    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a value in a histogram."""
        key = self._make_key(name, labels)
        with self.lock:
            self.histograms[key].append(value)
            # Keep only last 1000 values per histogram
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get counter value."""
        key = self._make_key(name, labels)
        return self.counters.get(key, 0.0)

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get gauge value."""
        key = self._make_key(name, labels)
        return self.gauges.get(key, 0.0)

    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get histogram statistics."""
        key = self._make_key(name, labels)
        values = self.histograms.get(key, [])

        if not values:
            return {'count': 0, 'min': 0, 'max': 0, 'avg': 0, 'p50': 0, 'p95': 0, 'p99': 0}

        sorted_values = sorted(values)
        count = len(sorted_values)

        return {
            'count': count,
            'min': sorted_values[0],
            'max': sorted_values[-1],
            'avg': sum(sorted_values) / count,
            'p50': self._percentile(sorted_values, 50),
            'p95': self._percentile(sorted_values, 95),
            'p99': self._percentile(sorted_values, 99)
        }

    def get_time_series(self, name: str, duration_minutes: int = 60) -> List[Dict[str, Any]]:
        """
        Get time series data for a metric.

        Args:
            name: Metric name
            duration_minutes: How far back to look

        Returns:
            List of {timestamp, value} dictionaries
        """
        cutoff = datetime.now() - timedelta(minutes=duration_minutes)

        with self.lock:
            points = self.metrics.get(name, [])
            filtered = [
                {'timestamp': p.timestamp.isoformat(), 'value': p.value, 'labels': p.labels}
                for p in points
                if p.timestamp > cutoff
            ]

        return filtered

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data.

        Returns:
            Dictionary with all key metrics for visualization
        """
        now = datetime.now()

        # Response time stats
        response_time_stats = self.get_histogram_stats('response_time_ms')

        # Success/error rates
        total_requests = self.get_counter('requests_total')
        successful_requests = self.get_counter('requests_successful')
        failed_requests = self.get_counter('requests_failed')

        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0

        # Agent-specific metrics
        agent_metrics = {}
        for agent in ['conversational_agent', 'memory', 'ui_generator']:
            agent_metrics[agent] = {
                'calls': self.get_counter('agent_calls', {'agent': agent}),
                'avg_duration_ms': self.get_histogram_stats('agent_duration_ms', {'agent': agent}).get('avg', 0),
                'errors': self.get_counter('agent_errors', {'agent': agent})
            }

        # Intent classification metrics
        intents = ['CALL', 'MEDICATION', 'APPOINTMENT', 'UNCLEAR', 'CONFIRMATION']
        intent_distribution = {
            intent: self.get_counter('intent_classified', {'intent': intent})
            for intent in intents
        }

        # Token usage
        total_tokens = self.get_counter('tokens_total')
        prompt_tokens = self.get_counter('tokens_prompt')
        completion_tokens = self.get_counter('tokens_completion')

        # Task completion metrics
        tasks_started = self.get_counter('tasks_started')
        tasks_completed = self.get_counter('tasks_completed')
        task_completion_rate = (tasks_completed / tasks_started * 100) if tasks_started > 0 else 0

        # User satisfaction
        satisfaction_stats = self.get_histogram_stats('user_satisfaction')

        # Cache metrics
        cache_hits = self.get_counter('cache_hits')
        cache_misses = self.get_counter('cache_misses')
        cache_hit_rate = (cache_hits / (cache_hits + cache_misses) * 100) if (cache_hits + cache_misses) > 0 else 0

        return {
            'timestamp': now.isoformat(),
            'overview': {
                'total_requests': total_requests,
                'success_rate': round(success_rate, 2),
                'error_rate': round(error_rate, 2),
                'avg_response_time_ms': round(response_time_stats.get('avg', 0), 2),
                'p95_response_time_ms': round(response_time_stats.get('p95', 0), 2),
                'p99_response_time_ms': round(response_time_stats.get('p99', 0), 2)
            },
            'agent_performance': agent_metrics,
            'intent_distribution': intent_distribution,
            'token_usage': {
                'total': total_tokens,
                'prompt': prompt_tokens,
                'completion': completion_tokens,
                'avg_per_request': round(total_tokens / total_requests, 2) if total_requests > 0 else 0
            },
            'task_metrics': {
                'started': tasks_started,
                'completed': tasks_completed,
                'completion_rate': round(task_completion_rate, 2)
            },
            'user_satisfaction': {
                'avg_score': round(satisfaction_stats.get('avg', 0), 2),
                'min_score': satisfaction_stats.get('min', 0),
                'max_score': satisfaction_stats.get('max', 0),
                'total_ratings': satisfaction_stats.get('count', 0)
            },
            'cache_performance': {
                'hits': cache_hits,
                'misses': cache_misses,
                'hit_rate': round(cache_hit_rate, 2)
            },
            'response_time_distribution': response_time_stats,
            'time_series': {
                'response_time': self.get_time_series('response_time_ms', 60),
                'requests_per_minute': self._get_requests_per_minute(60)
            }
        }

    def _get_requests_per_minute(self, duration_minutes: int) -> List[Dict[str, Any]]:
        """Calculate requests per minute over time."""
        now = datetime.now()
        cutoff = now - timedelta(minutes=duration_minutes)

        # Get all request metrics
        with self.lock:
            points = self.metrics.get('request', [])
            recent_points = [p for p in points if p.timestamp > cutoff]

        # Group by minute
        requests_by_minute = defaultdict(int)
        for point in recent_points:
            minute_key = point.timestamp.replace(second=0, microsecond=0)
            requests_by_minute[minute_key] += 1

        # Convert to sorted list
        result = [
            {'timestamp': ts.isoformat(), 'count': count}
            for ts, count in sorted(requests_by_minute.items())
        ]

        return result

    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0

        index = int(len(sorted_values) * percentile / 100)
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]

    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create a unique key from name and labels."""
        if not labels:
            return name

        label_str = ','.join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def _cleanup_old_metrics(self):
        """Background thread to clean up old metrics."""
        while True:
            time.sleep(3600)  # Run every hour

            cutoff = datetime.now() - timedelta(hours=self.retention_hours)

            with self.lock:
                for name, points in self.metrics.items():
                    # Remove old points
                    while points and points[0].timestamp < cutoff:
                        points.popleft()

    def reset_all(self):
        """Reset all metrics (useful for testing)."""
        with self.lock:
            self.metrics.clear()
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()


# Global metrics collector instance
metrics = MetricsCollector()


# Convenience functions
def record_response_time(duration_ms: float):
    """Record a request response time."""
    metrics.record_metric('response_time_ms', duration_ms)
    metrics.record_histogram('response_time_ms', duration_ms)
    metrics.increment_counter('requests_total')
    metrics.record_metric('request', 1.0)


def record_agent_call(agent_name: str, duration_ms: float, success: bool = True):
    """Record an agent call."""
    metrics.increment_counter('agent_calls', 1.0, {'agent': agent_name})
    metrics.record_histogram('agent_duration_ms', duration_ms, {'agent': agent_name})

    if not success:
        metrics.increment_counter('agent_errors', 1.0, {'agent': agent_name})


def record_intent(intent: str):
    """Record an intent classification."""
    metrics.increment_counter('intent_classified', 1.0, {'intent': intent})


def record_task(started: bool = False, completed: bool = False):
    """Record task start/completion."""
    if started:
        metrics.increment_counter('tasks_started')
    if completed:
        metrics.increment_counter('tasks_completed')


def record_tokens(prompt_tokens: int, completion_tokens: int):
    """Record token usage."""
    metrics.increment_counter('tokens_total', prompt_tokens + completion_tokens)
    metrics.increment_counter('tokens_prompt', prompt_tokens)
    metrics.increment_counter('tokens_completion', completion_tokens)


def record_success():
    """Record a successful request."""
    metrics.increment_counter('requests_successful')


def record_failure():
    """Record a failed request."""
    metrics.increment_counter('requests_failed')


def record_satisfaction(score: float):
    """Record user satisfaction score (0-10)."""
    metrics.record_metric('user_satisfaction', score)
    metrics.record_histogram('user_satisfaction', score)


def record_cache_hit(hit: bool = True):
    """Record cache hit/miss."""
    if hit:
        metrics.increment_counter('cache_hits')
    else:
        metrics.increment_counter('cache_misses')


def get_dashboard_data() -> Dict[str, Any]:
    """Get dashboard data."""
    return metrics.get_dashboard_data()
