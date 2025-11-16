"""
ElderCare Agent - Flask Web Application
Provides web interface for the ElderCare Agent system.
"""

import os
import logging
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv
import asyncio

from .main import ElderCareAgent

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__,
            template_folder='ui/templates',
            static_folder='ui/static')

app.secret_key = os.getenv('SECRET_KEY', 'eldercare-agent-secret-key-change-in-production')

# Enable CORS
CORS(app)

# Store agent instances per session
agent_instances = {}


def get_or_create_agent(user_id: str = "margaret_thompson") -> ElderCareAgent:
    """Get or create an ElderCare Agent instance for the session."""
    session_id = session.get('session_id')

    if not session_id:
        # Create new session
        session_id = f"web_session_{len(agent_instances)}"
        session['session_id'] = session_id

    if session_id not in agent_instances:
        logger.info(f"Creating new agent instance for session: {session_id}")
        agent_instances[session_id] = ElderCareAgent(user_id=user_id)

    return agent_instances[session_id]


@app.route('/')
def index():
    """Main page - Voice Mode Interface."""
    return render_template('voice_mode.html')

@app.route('/classic')
def classic():
    """Classic UI (for reference/testing)."""
    return render_template('index.html')


@app.route('/api/message', methods=['POST'])
async def process_message():
    """
    Process a user message through the agent system.

    Request JSON:
        {
            "message": "User's message",
            "user_id": "optional_user_id"
        }

    Response JSON:
        {
            "success": true/false,
            "message": "Agent's response",
            "ui": {UI configuration if applicable},
            "task_type": "type of task"
        }
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        user_id = data.get('user_id', 'margaret_thompson')

        if not user_message:
            return jsonify({
                'success': False,
                'error': 'No message provided'
            }), 400

        logger.info(f"Processing message: {user_message}")

        # Get or create agent
        agent = get_or_create_agent(user_id)

        # Process message
        response = await agent.process_message(user_message)
        
        # Add debug info in development
        if os.getenv('FLASK_DEBUG', 'False').lower() == 'true':
            response['_debug'] = {
                'user_message': user_message,
                'response_keys': list(response.keys())
            }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'message': "I'm sorry, I encountered an error. Please try again."
        }), 500


@app.route('/api/session/history', methods=['GET'])
def get_session_history():
    """Get conversation history for current session."""
    try:
        agent = get_or_create_agent()
        history = agent.get_session_history()

        return jsonify({
            'success': True,
            'history': history
        }), 200

    except Exception as e:
        logger.error(f"Error getting session history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/session/end', methods=['POST'])
def end_session():
    """End the current session."""
    try:
        session_id = session.get('session_id')

        if session_id and session_id in agent_instances:
            agent = agent_instances[session_id]
            agent.end_session()
            del agent_instances[session_id]

        session.clear()

        return jsonify({
            'success': True,
            'message': 'Session ended'
        }), 200

    except Exception as e:
        logger.error(f"Error ending session: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'ElderCare Agent',
        'version': '1.0.0'
    }), 200


@app.route('/api/session/profile', methods=['GET'])
def get_profile():
    """Get user profile from session."""
    try:
        profile = session.get('user_profile')

        return jsonify({
            'success': True,
            'profile': profile
        }), 200

    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/session/profile', methods=['POST'])
def save_profile():
    """Save user profile to session."""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        age = data.get('age')

        if not name or not age:
            return jsonify({
                'success': False,
                'error': 'Name and age required'
            }), 400

        # Save to session
        session['user_profile'] = {
            'name': name,
            'age': age
        }

        logger.info(f"Saved user profile: {name}, {age}")

        return jsonify({
            'success': True,
            'profile': session['user_profile']
        }), 200

    except Exception as e:
        logger.error(f"Error saving profile: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/debug', methods=['GET'])
def debug_info():
    """Debug endpoint to check agent initialization."""
    try:
        import os
        api_key = os.getenv("GEMINI_API_KEY")
        return jsonify({
            'api_key_configured': bool(api_key),
            'api_key_length': len(api_key) if api_key else 0,
            'agent_instances': len(agent_instances),
            'status': 'debug_info'
        }), 200
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@app.errorhandler(404)
def not_found(error):
    """404 error handler."""
    return jsonify({
        'success': False,
        'error': 'Not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """500 error handler."""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


# Note: async routes are handled by Flask's native async support in Flask 2.0+


if __name__ == '__main__':
    # Get configuration from environment
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    logger.info(f"Starting ElderCare Agent Web Server on {host}:{port}")
    logger.info(f"Debug mode: {debug}")

    app.run(host=host, port=port, debug=debug)
