/**
 * ElderCare Agent - Main Application JavaScript
 * Handles user interaction, agent communication, and UI updates
 */

class ElderCareApp {
    constructor() {
        this.apiBase = window.location.origin;
        this.speechManager = null;
        this.userId = 'margaret_thompson';  // Default demo user

        // DOM elements
        this.elements = {
            voiceButton: document.getElementById('voiceButton'),
            textInput: document.getElementById('textInput'),
            sendButton: document.getElementById('sendButton'),
            conversation: document.getElementById('conversation'),
            uiContainer: document.getElementById('uiContainer'),
            loadingOverlay: document.getElementById('loadingOverlay'),
            historyButton: document.getElementById('historyButton'),
            endSessionButton: document.getElementById('endSessionButton')
        };

        this.initialize();
    }

    /**
     * Initialize the application
     */
    initialize() {
        console.log('Initializing ElderCare Agent...');

        // Initialize speech manager
        this.initializeSpeech();

        // Set up event listeners
        this.setupEventListeners();

        // Show welcome message
        this.showWelcomeMessage();

        console.log('✅ ElderCare Agent ready');
    }

    /**
     * Initialize speech functionality
     */
    initializeSpeech() {
        const support = SpeechManager.isSupported();

        if (!support.full) {
            console.warn('Speech features not fully supported:', support);
            this.addMessage('system', '⚠️ Voice features may not work in your browser. Please use text input.');
        }

        this.speechManager = new SpeechManager();

        // Set up speech event handlers
        this.speechManager.onListeningStart = () => {
            this.elements.voiceButton.classList.add('listening');
            this.elements.voiceButton.innerHTML = '<span class="voice-icon">🔴</span><span class="voice-text">Listening...</span>';
        };

        this.speechManager.onListeningEnd = () => {
            this.elements.voiceButton.classList.remove('listening');
            this.elements.voiceButton.innerHTML = '<span class="voice-icon">🎤</span><span class="voice-text">Tap to Speak</span>';
        };

        this.speechManager.onListeningError = (error) => {
            this.elements.voiceButton.classList.remove('listening');
            this.elements.voiceButton.innerHTML = '<span class="voice-icon">🎤</span><span class="voice-text">Tap to Speak</span>';

            if (error === 'not-allowed') {
                this.addMessage('error', 'Please allow microphone access to use voice input.');
            } else if (error === 'no-speech') {
                this.addMessage('error', 'No speech detected. Please try again.');
            }
        };

        this.speechManager.onSpeechResult = (transcript, confidence) => {
            console.log(`User said: "${transcript}" (${confidence})`);

            // Add user message to conversation
            this.addMessage('user', transcript);

            // Send to agent
            this.sendMessage(transcript);
        };
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Voice button
        this.elements.voiceButton.addEventListener('click', () => {
            this.speechManager.startListening();
        });

        // Text input
        this.elements.textInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleTextInput();
            }
        });

        // Send button
        if (this.elements.sendButton) {
            this.elements.sendButton.addEventListener('click', () => {
                this.handleTextInput();
            });
        }

        // History button
        if (this.elements.historyButton) {
            this.elements.historyButton.addEventListener('click', () => {
                this.showHistory();
            });
        }

        // End session button
        if (this.elements.endSessionButton) {
            this.elements.endSessionButton.addEventListener('click', () => {
                this.endSession();
            });
        }
    }

    /**
     * Handle text input submission
     */
    handleTextInput() {
        const message = this.elements.textInput.value.trim();

        if (!message) {
            return;
        }

        // Add to conversation
        this.addMessage('user', message);

        // Clear input
        this.elements.textInput.value = '';

        // Send to agent
        this.sendMessage(message);
    }

    /**
     * Send message to agent API
     */
    async sendMessage(message) {
        this.showLoading(true);

        try {
            const response = await fetch(`${this.apiBase}/api/message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    user_id: this.userId
                })
            });

            const data = await response.json();

            if (data.success) {
                // Add agent response
                this.addMessage('agent', data.message);

                // Speak response
                this.speechManager.speak(data.message);

                // Handle UI if present
                if (data.ui) {
                    this.renderDynamicUI(data.ui);
                }
            } else {
                // Error response
                this.addMessage('error', data.message || 'Sorry, I encountered an error.');
            }

        } catch (error) {
            console.error('Error sending message:', error);
            this.addMessage('error', 'Connection error. Please check your internet and try again.');
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * Add message to conversation
     */
    addMessage(type, text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        textDiv.textContent = text;

        contentDiv.appendChild(textDiv);
        messageDiv.appendChild(contentDiv);

        this.elements.conversation.appendChild(messageDiv);

        // Scroll to bottom
        this.elements.conversation.scrollTop = this.elements.conversation.scrollHeight;
    }

    /**
     * Render dynamic UI from agent response
     */
    renderDynamicUI(uiConfig) {
        console.log('Rendering dynamic UI:', uiConfig);

        // Clear existing UI
        this.elements.uiContainer.innerHTML = '';

        // Use template_id (not template_name)
        const templateId = uiConfig.template_id;

        if (templateId === 'call_ui') {
            this.renderCallUI(uiConfig);
        } else if (templateId === 'medication_ui') {
            this.renderMedicationUI(uiConfig);
        } else if (templateId === 'appointment_ui') {
            this.renderAppointmentUI(uiConfig);
        } else {
            console.error('Unknown template ID:', templateId);
        }
    }

    /**
     * Render call UI
     */
    renderCallUI(uiConfig) {
        const card = document.createElement('div');
        card.className = 'ui-card';

        // Extract elements from ui_config
        const elements = uiConfig.ui_config.elements;

        // Find the data we need from elements
        const contactName = elements.find(e => e.id === 'contact_name')?.content || 'Contact';
        const relationship = elements.find(e => e.id === 'relationship')?.content || '';
        const photoSrc = elements.find(e => e.id === 'contact_photo')?.src || '';
        const callButton = elements.find(e => e.id === 'call_button');

        card.innerHTML = `
            ${photoSrc ? `<img src="${photoSrc}" alt="${contactName}" style="width: 120px; height: 120px; border-radius: 50%; margin-bottom: 16px;">` : ''}
            <h2 style="font-size: 32px; font-weight: bold; margin-bottom: 8px;">${contactName}</h2>
            <p style="font-size: 24px; color: #666; margin-bottom: 32px;">${relationship}</p>
            <button class="action-button action-button-success" onclick="window.open('${callButton.url}', '_blank')" style="width: 100%; height: 80px; font-size: 28px; background: #4CAF50; color: white; border: none; border-radius: 12px; cursor: pointer;">
                📞 Video Call
            </button>
        `;

        this.elements.uiContainer.appendChild(card);
    }

    /**
     * Render medication reminder UI
     */
    renderMedicationUI(uiConfig) {
        const card = document.createElement('div');
        card.className = 'ui-card';

        // Extract elements from ui_config
        const elements = uiConfig.ui_config.elements;

        // Find the data we need
        const medName = elements.find(e => e.id === 'medication_name')?.content || 'Medication';
        const dosage = elements.find(e => e.id === 'dosage')?.content || '';
        const instructions = elements.find(e => e.id === 'instructions')?.content || '';
        const photoSrc = elements.find(e => e.id === 'medication_image')?.src || '';
        const takeButton = elements.find(e => e.id === 'take_button');

        card.innerHTML = `
            ${photoSrc ? `<img src="${photoSrc}" alt="${medName}" style="width: 100px; height: 100px; margin-bottom: 16px;">` : ''}
            <h2 style="font-size: 32px; font-weight: bold; margin-bottom: 8px;">${medName}</h2>
            <p style="font-size: 24px; color: #666; margin-bottom: 8px;">${dosage}</p>
            <p style="font-size: 20px; color: #666; margin-bottom: 32px;">${instructions}</p>
            <button class="action-button action-button-success" onclick="alert('Medication logged!')" style="width: 100%; height: 80px; font-size: 28px; background: #4CAF50; color: white; border: none; border-radius: 12px; cursor: pointer; margin-bottom: 12px;">
                ✅ I Took It
            </button>
            <button class="action-button action-button-secondary" onclick="alert('Skipped')" style="width: 100%; height: 60px; font-size: 24px; background: #F5F5F5; color: #666; border: none; border-radius: 8px; cursor: pointer;">
                ⏭️ Skip
            </button>
        `;

        this.elements.uiContainer.appendChild(card);
    }

    /**
     * Render appointment UI
     */
    renderAppointmentUI(uiConfig) {
        const card = document.createElement('div');
        card.className = 'ui-card';

        // Extract elements from ui_config
        const elements = uiConfig.ui_config.elements;

        // Find the data we need
        const title = elements.find(e => e.id === 'title')?.content || 'Appointment';
        const doctorName = elements.find(e => e.id === 'doctor_name')?.content || '';
        const date = elements.find(e => e.id === 'date')?.content || '';
        const time = elements.find(e => e.id === 'time')?.content || '';
        const location = elements.find(e => e.id === 'location')?.content || '';

        card.innerHTML = `
            <h2 style="font-size: 32px; font-weight: bold; margin-bottom: 16px;">📅 ${title}</h2>
            <p style="font-size: 24px; margin-bottom: 8px;"><strong>Doctor:</strong> ${doctorName}</p>
            <p style="font-size: 24px; margin-bottom: 8px;"><strong>Date:</strong> ${date}</p>
            <p style="font-size: 24px; margin-bottom: 8px;"><strong>Time:</strong> ${time}</p>
            <p style="font-size: 24px; margin-bottom: 32px;"><strong>Location:</strong> ${location}</p>
            <button class="action-button action-button-primary" onclick="alert('Appointment confirmed!')" style="width: 100%; height: 80px; font-size: 28px; background: #2196F3; color: white; border: none; border-radius: 12px; cursor: pointer;">
                ✅ Confirm
            </button>
        `;

        this.elements.uiContainer.appendChild(card);
    }

    /**
     * Log medication taken
     */
    async logMedicationTaken(medicationId) {
        this.showLoading(true);

        try {
            await this.sendMessage(`I took my medication (ID: ${medicationId})`);

            // Clear UI
            this.elements.uiContainer.innerHTML = '';

            this.addMessage('system', '✅ Medication logged!');
        } catch (error) {
            console.error('Error logging medication:', error);
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * Skip medication
     */
    skipMedication(medicationId) {
        // Clear UI
        this.elements.uiContainer.innerHTML = '';
        this.addMessage('system', 'Medication reminder dismissed.');
    }

    /**
     * Confirm appointment
     */
    async confirmAppointment(appointmentId) {
        this.showLoading(true);

        try {
            await this.sendMessage(`Confirm appointment ${appointmentId}`);

            // Clear UI
            this.elements.uiContainer.innerHTML = '';

            this.addMessage('system', '✅ Appointment confirmed!');
        } catch (error) {
            console.error('Error confirming appointment:', error);
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * Show session history
     */
    async showHistory() {
        this.showLoading(true);

        try {
            const response = await fetch(`${this.apiBase}/api/session/history`);
            const data = await response.json();

            if (data.success) {
                this.elements.conversation.innerHTML = '';

                data.history.forEach(entry => {
                    this.addMessage(entry.role, entry.content);
                });
            }
        } catch (error) {
            console.error('Error fetching history:', error);
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * End session
     */
    async endSession() {
        if (!confirm('Are you sure you want to end this session?')) {
            return;
        }

        this.showLoading(true);

        try {
            const response = await fetch(`${this.apiBase}/api/session/end`, {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                this.addMessage('system', 'Session ended. Goodbye!');

                // Clear conversation after 2 seconds
                setTimeout(() => {
                    this.elements.conversation.innerHTML = '';
                    this.showWelcomeMessage();
                }, 2000);
            }
        } catch (error) {
            console.error('Error ending session:', error);
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * Show loading overlay
     */
    showLoading(show) {
        if (this.elements.loadingOverlay) {
            this.elements.loadingOverlay.classList.toggle('show', show);
        }
    }

    /**
     * Show welcome message
     */
    showWelcomeMessage() {
        this.addMessage('agent', 'Hello! I\'m your ElderCare assistant. I can help you call family, manage medications, and schedule doctor appointments. How can I help you today?');

        // Speak welcome message
        if (this.speechManager) {
            this.speechManager.speak('Hello! I\'m your ElderCare assistant. How can I help you today?');
        }
    }
}

// Initialize app when page loads
let app;

document.addEventListener('DOMContentLoaded', () => {
    app = new ElderCareApp();
});
