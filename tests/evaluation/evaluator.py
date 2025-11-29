"""
ElderCare Agent - Automated Evaluator
Runs comprehensive test scenarios and generates evaluation reports.
"""

import sys
import os
import asyncio
import yaml
import json
import time
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.main import ElderCareAgent
from src.core.llm_judge import LLMJudge, EvaluationResult


class AgentEvaluator:
    """
    Automated evaluation system for ElderCare Agent.

    Runs test scenarios and evaluates:
    - Intent classification accuracy
    - Task completion rate
    - Response quality (via LLM-as-a-Judge)
    - Response time performance
    - Accessibility compliance
    """

    def __init__(self, scenarios_file: str = None):
        self.scenarios_file = scenarios_file or os.path.join(
            os.path.dirname(__file__), 'test_scenarios.yaml'
        )

        # Load test scenarios
        with open(self.scenarios_file, 'r') as f:
            data = yaml.safe_load(f)
            self.scenarios = data['test_scenarios']
            self.criteria = data['evaluation_criteria']

        # Initialize LLM judge
        self.judge = LLMJudge()

        # Results storage
        self.results = []

    async def run_evaluation(self) -> Dict[str, Any]:
        """
        Run full evaluation suite.

        Returns:
            Dictionary with comprehensive evaluation results
        """
        print("=" * 80)
        print("ELDERCARE AGENT - COMPREHENSIVE EVALUATION")
        print("=" * 80)
        print(f"Total scenarios: {len(self.scenarios)}")
        print(f"Starting evaluation at: {datetime.now().isoformat()}")
        print()

        start_time = time.time()

        # Run each scenario
        for i, scenario in enumerate(self.scenarios, 1):
            print(f"[{i}/{len(self.scenarios)}] Running: {scenario['name']}...")

            result = await self.run_scenario(scenario)
            self.results.append(result)

            # Print quick result
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            print(f"  {status} - Intent: {result['detected_intent']}, "
                  f"Time: {result['response_time_ms']:.0f}ms")

        total_time = time.time() - start_time

        # Generate summary
        summary = self.generate_summary(total_time)

        print()
        print("=" * 80)
        print("EVALUATION COMPLETE")
        print("=" * 80)
        self.print_summary(summary)

        return summary

    async def run_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test scenario."""
        scenario_id = scenario['id']
        user_message = scenario['user_message']
        expected_intent = scenario.get('expected_intent', 'UNKNOWN')
        user_context = scenario.get('user_context', {})

        # Create agent instance
        user_id = user_context.get('user_id', 'margaret_thompson') if user_context else 'margaret_thompson'
        agent = ElderCareAgent(user_id=user_id)

        # Set user context if provided
        if user_context:
            session_data = agent.session_manager.get_session(agent.current_session_id)
            if session_data:
                session_data['context']['user_name'] = user_context.get('name', 'Margaret')
                session_data['context']['user_age'] = user_context.get('age', 72)

        # Measure response time
        start_time = time.time()

        try:
            # Process message
            response = await agent.process_message(user_message)
            response_time_ms = (time.time() - start_time) * 1000

            # Extract response data
            agent_response = response.get('message', '')
            detected_intent = response.get('intent', 'UNKNOWN')
            success = response.get('success', False)

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            agent_response = f"ERROR: {str(e)}"
            detected_intent = "ERROR"
            success = False

        # Evaluate with LLM judge
        judge_result = self.judge.evaluate_response(
            user_message=user_message,
            agent_response=agent_response,
            intent=detected_intent,
            context=user_context
        )

        # Check success criteria
        passed = self.check_success_criteria(
            scenario=scenario,
            detected_intent=detected_intent,
            response_time_ms=response_time_ms,
            judge_result=judge_result,
            success=success
        )

        return {
            'scenario_id': scenario_id,
            'scenario_name': scenario['name'],
            'user_message': user_message,
            'agent_response': agent_response,
            'expected_intent': expected_intent,
            'detected_intent': detected_intent,
            'response_time_ms': response_time_ms,
            'success': success,
            'passed': passed,
            'judge_scores': {
                'overall': judge_result.overall_score,
                'clarity': judge_result.clarity_score,
                'empathy': judge_result.empathy_score,
                'accuracy': judge_result.accuracy_score,
                'accessibility': judge_result.accessibility_score,
                'safety': judge_result.safety_score
            },
            'judge_feedback': judge_result.feedback,
            'judge_passed': judge_result.pass_threshold
        }

    def check_success_criteria(
        self,
        scenario: Dict[str, Any],
        detected_intent: str,
        response_time_ms: float,
        judge_result: EvaluationResult,
        success: bool
    ) -> bool:
        """Check if scenario passed all success criteria."""
        expected_intent = scenario.get('expected_intent', 'UNKNOWN')

        # Check intent accuracy
        intent_correct = (detected_intent == expected_intent)

        # Check response time
        max_time = self.criteria['response_time']['max_acceptable_ms']
        time_acceptable = (response_time_ms <= max_time)

        # Check LLM judge scores
        judge_passed = judge_result.pass_threshold

        # Check basic success
        basic_success = success

        # All criteria must pass
        return (intent_correct and time_acceptable and judge_passed and basic_success)

    def generate_summary(self, total_time: float) -> Dict[str, Any]:
        """Generate evaluation summary statistics."""
        total_scenarios = len(self.results)
        passed_scenarios = sum(1 for r in self.results if r['passed'])
        failed_scenarios = total_scenarios - passed_scenarios

        # Intent accuracy
        intent_correct = sum(
            1 for r in self.results
            if r['detected_intent'] == r['expected_intent']
        )
        intent_accuracy = (intent_correct / total_scenarios) * 100

        # Task completion
        task_completed = sum(1 for r in self.results if r['success'])
        task_completion_rate = (task_completed / total_scenarios) * 100

        # Response time stats
        response_times = [r['response_time_ms'] for r in self.results]
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)

        # LLM judge scores
        avg_scores = {
            'overall': sum(r['judge_scores']['overall'] for r in self.results) / total_scenarios,
            'clarity': sum(r['judge_scores']['clarity'] for r in self.results) / total_scenarios,
            'empathy': sum(r['judge_scores']['empathy'] for r in self.results) / total_scenarios,
            'accuracy': sum(r['judge_scores']['accuracy'] for r in self.results) / total_scenarios,
            'accessibility': sum(r['judge_scores']['accessibility'] for r in self.results) / total_scenarios,
            'safety': sum(r['judge_scores']['safety'] for r in self.results) / total_scenarios
        }

        # Judge pass rate
        judge_passed = sum(1 for r in self.results if r['judge_passed'])
        judge_pass_rate = (judge_passed / total_scenarios) * 100

        # Group by category
        by_category = {
            'call': [r for r in self.results if r['scenario_id'].startswith('call_')],
            'medication': [r for r in self.results if r['scenario_id'].startswith('med_')],
            'appointment': [r for r in self.results if r['scenario_id'].startswith('appt_')],
            'confirmation': [r for r in self.results if r['scenario_id'].startswith('confirm_')],
            'error': [r for r in self.results if r['scenario_id'].startswith('error_')],
            'accessibility': [r for r in self.results if r['scenario_id'].startswith('access_')],
            'empathy': [r for r in self.results if r['scenario_id'].startswith('empathy_')]
        }

        category_stats = {}
        for category, results in by_category.items():
            if results:
                category_stats[category] = {
                    'total': len(results),
                    'passed': sum(1 for r in results if r['passed']),
                    'pass_rate': (sum(1 for r in results if r['passed']) / len(results)) * 100,
                    'avg_empathy_score': sum(r['judge_scores']['empathy'] for r in results) / len(results)
                }

        return {
            'timestamp': datetime.now().isoformat(),
            'total_time_seconds': round(total_time, 2),
            'total_scenarios': total_scenarios,
            'passed_scenarios': passed_scenarios,
            'failed_scenarios': failed_scenarios,
            'overall_pass_rate': round((passed_scenarios / total_scenarios) * 100, 2),
            'intent_classification': {
                'correct': intent_correct,
                'total': total_scenarios,
                'accuracy': round(intent_accuracy, 2)
            },
            'task_completion': {
                'completed': task_completed,
                'total': total_scenarios,
                'rate': round(task_completion_rate, 2)
            },
            'response_time': {
                'avg_ms': round(avg_response_time, 2),
                'min_ms': round(min_response_time, 2),
                'max_ms': round(max_response_time, 2),
                'target_ms': self.criteria['response_time']['target_ms'],
                'meets_target': avg_response_time <= self.criteria['response_time']['target_ms']
            },
            'llm_judge_evaluation': {
                'average_scores': {k: round(v, 2) for k, v in avg_scores.items()},
                'passed': judge_passed,
                'total': total_scenarios,
                'pass_rate': round(judge_pass_rate, 2)
            },
            'by_category': category_stats,
            'failed_scenarios': [
                {
                    'id': r['scenario_id'],
                    'name': r['scenario_name'],
                    'reason': f"Intent: {r['detected_intent']} (expected {r['expected_intent']}), "
                              f"Judge: {r['judge_passed']}, Time: {r['response_time_ms']:.0f}ms"
                }
                for r in self.results if not r['passed']
            ]
        }

    def print_summary(self, summary: Dict[str, Any]):
        """Print evaluation summary to console."""
        print()
        print(f"Overall Pass Rate: {summary['overall_pass_rate']}%")
        print(f"  Passed: {summary['passed_scenarios']}/{summary['total_scenarios']}")
        print()

        print("Intent Classification:")
        print(f"  Accuracy: {summary['intent_classification']['accuracy']}%")
        print(f"  Correct: {summary['intent_classification']['correct']}/{summary['intent_classification']['total']}")
        print()

        print("Task Completion:")
        print(f"  Rate: {summary['task_completion']['rate']}%")
        print(f"  Completed: {summary['task_completion']['completed']}/{summary['task_completion']['total']}")
        print()

        print("Response Time:")
        print(f"  Average: {summary['response_time']['avg_ms']:.0f}ms")
        print(f"  Target: {summary['response_time']['target_ms']}ms")
        print(f"  Meets Target: {'✅ YES' if summary['response_time']['meets_target'] else '❌ NO'}")
        print()

        print("LLM Judge Scores (0-10):")
        scores = summary['llm_judge_evaluation']['average_scores']
        print(f"  Overall: {scores['overall']}")
        print(f"  Clarity: {scores['clarity']}")
        print(f"  Empathy: {scores['empathy']} ⭐")
        print(f"  Accuracy: {scores['accuracy']}")
        print(f"  Accessibility: {scores['accessibility']}")
        print(f"  Safety: {scores['safety']}")
        print(f"  Judge Pass Rate: {summary['llm_judge_evaluation']['pass_rate']}%")
        print()

        print("By Category:")
        for category, stats in summary['by_category'].items():
            print(f"  {category.capitalize()}: {stats['pass_rate']:.0f}% "
                  f"({stats['passed']}/{stats['total']}) "
                  f"- Empathy: {stats['avg_empathy_score']:.1f}/10")
        print()

        if summary['failed_scenarios']:
            print(f"Failed Scenarios ({len(summary['failed_scenarios'])}):")
            for fail in summary['failed_scenarios'][:5]:  # Show first 5
                print(f"  - {fail['name']}: {fail['reason']}")
            if len(summary['failed_scenarios']) > 5:
                print(f"  ... and {len(summary['failed_scenarios']) - 5} more")
        print()

    def save_report(self, output_file: str = None):
        """Save evaluation report to JSON file."""
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f'evaluation_report_{timestamp}.json'

        report = {
            'summary': self.generate_summary(0),  # Time not important for saved report
            'detailed_results': self.results
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📄 Detailed report saved to: {output_file}")


async def main():
    """Run evaluation."""
    evaluator = AgentEvaluator()

    # Run evaluation
    summary = await evaluator.run_evaluation()

    # Save report
    evaluator.save_report()

    # Print final score
    print()
    print("=" * 80)
    print("FINAL EVALUATION SCORE")
    print("=" * 80)
    print(f"Overall Pass Rate: {summary['overall_pass_rate']}% (Target: >90%)")
    print(f"Intent Accuracy: {summary['intent_classification']['accuracy']}% (Target: >95%)")
    print(f"Task Completion: {summary['task_completion']['rate']}% (Target: >90%)")
    print(f"Avg Response Time: {summary['response_time']['avg_ms']:.0f}ms (Target: <2000ms)")
    print(f"LLM Judge Empathy Score: {summary['llm_judge_evaluation']['average_scores']['empathy']}/10 (Target: >7.0)")
    print()

    # Determine if production-ready
    production_ready = (
        summary['overall_pass_rate'] >= 90 and
        summary['intent_classification']['accuracy'] >= 95 and
        summary['response_time']['meets_target'] and
        summary['llm_judge_evaluation']['average_scores']['empathy'] >= 7.0
    )

    if production_ready:
        print("✅ AGENT IS PRODUCTION-READY!")
    else:
        print("⚠️  Agent needs improvement before production deployment")

    print("=" * 80)


if __name__ == '__main__':
    asyncio.run(main())
