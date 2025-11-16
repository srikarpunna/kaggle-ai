/**
 * ElderCare Agent - Voice Mode UI
 * ChatGPT-style voice interface with animated circle visualizer
 */

class VoiceModeUI {
    constructor() {
        // Elements
        this.elements = {
            mainCircle: document.getElementById('main-circle'),
            pulseCircle: document.getElementById('pulse-circle'),
            frequencyBars: document.getElementById('frequency-bars'),
            userMessage: document.getElementById('user-message'),
            agentMessage: document.getElementById('agent-message'),
            micButton: document.getElementById('mic-button'),
            statusText: document.getElementById('status-text'),
            uiOverlay: document.getElementById('ui-overlay'),
            uiContent: document.getElementById('ui-content'),
            closeUIBtn: document.getElementById('close-ui'),
            onboardingOverlay: document.getElementById('onboarding-overlay'),
            onboardingCircle: document.getElementById('onboarding-main-circle'),
            onboardingPulse: document.getElementById('onboarding-pulse'),
            onboardingBars: document.getElementById('onboarding-bars'),
            onboardingMessage: document.getElementById('onboarding-message'),
            toast: document.getElementById('toast')
        };

        // State
        this.state = {
            mode: 'idle', // idle, listening, speaking, thinking
            isRecording: false,
            currentTranscript: '',
            isTyping: false,
            onboardingComplete: false,
            userName: null,
            userAge: null,
            audioContext: null,
            analyser: null,
            frequencyData: null,
            animationFrame: null
        };

        // Speech recognition
        this.recognition = null;
        this.synthesis = window.speechSynthesis;

        // Typing effect
        this.typingSpeed = 50; // ms per character

        // Initialize
        this.init();
    }

    async init() {
        console.log('Initializing Voice Mode UI...');

        // Generate frequency bars
        this.generateFrequencyBars();
        this.generateFrequencyBars(true); // For onboarding

        // Set up event listeners
        this.setupEventListeners();

        // Initialize Speech Recognition
        this.initSpeechRecognition();

        // Check if user needs onboarding
        await this.checkOnboarding();

        console.log('Voice Mode UI initialized');
    }

    generateFrequencyBars(isOnboarding = false) {
        const barsContainer = isOnboarding ? this.elements.onboardingBars : this.elements.frequencyBars;
        const numBars = 40;
        const centerX = 150;
        const centerY = 150;
        const radius = 145;

        barsContainer.innerHTML = '';

        for (let i = 0; i < numBars; i++) {
            const angle = (i / numBars) * Math.PI * 2;
            const x1 = centerX + Math.cos(angle) * radius;
            const y1 = centerY + Math.sin(angle) * radius;
            const x2 = centerX + Math.cos(angle) * (radius + 10);
            const y2 = centerY + Math.sin(angle) * (radius + 10);

            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('class', 'frequency-bar');
            line.setAttribute('x1', x1);
            line.setAttribute('y1', y1);
            line.setAttribute('x2', x2);
            line.setAttribute('y2', y2);
            line.setAttribute('data-index', i);

            barsContainer.appendChild(line);
        }
    }

    setupEventListeners() {
        // Mic button
        this.elements.micButton.addEventListener('click', () => this.toggleRecording());

        // Close UI overlay
        this.elements.closeUIBtn.addEventListener('click', () => this.hideUIOverlay());

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && !this.state.isRecording) {
                e.preventDefault();
                this.startRecording();
            }
        });

        document.addEventListener('keyup', (e) => {
            if (e.code === 'Space' && this.state.isRecording) {
                e.preventDefault();
                this.stopRecording();
            }
        });
    }

    initSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            this.showToast('Speech recognition not supported in this browser', 'error');
            console.error('Speech Recognition API not supported');
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onstart = () => {
            console.log('Speech recognition started');
            this.setMode('listening');
        };

        this.recognition.onresult = (event) => {
            const transcript = Array.from(event.results)
                .map(result => result[0])
                .map(result => result.transcript)
                .join('');

            this.state.currentTranscript = transcript;
            this.displayUserMessage(transcript);

            // If final result, process it
            if (event.results[event.results.length - 1].isFinal) {
                console.log('Final transcript:', transcript);
                this.processUserMessage(transcript);
            }
        };

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.setMode('idle');
            this.state.isRecording = false;
            this.elements.micButton.classList.remove('listening');

            if (event.error !== 'no-speech') {
                this.showToast(`Error: ${event.error}`, 'error');
            }
        };

        this.recognition.onend = () => {
            console.log('Speech recognition ended');
            this.setMode('idle');
            this.state.isRecording = false;
            this.elements.micButton.classList.remove('listening');
        };
    }

    async checkOnboarding() {
        try {
            // Check if user profile exists in session
            const response = await fetch('/api/session/profile');

            if (response.ok) {
                const data = await response.json();
                if (data.profile && data.profile.name && data.profile.age) {
                    this.state.userName = data.profile.name;
                    this.state.userAge = data.profile.age;
                    this.state.onboardingComplete = true;
                    console.log('User profile found:', data.profile);
                    return;
                }
            }

            // No profile found - start onboarding
            await this.startOnboarding();

        } catch (error) {
            console.error('Error checking onboarding:', error);
            // Assume onboarding needed
            await this.startOnboarding();
        }
    }

    async startOnboarding() {
        console.log('Starting onboarding...');

        // Show onboarding overlay
        this.elements.onboardingOverlay.classList.remove('hidden');
        setTimeout(() => {
            this.elements.onboardingOverlay.classList.add('visible');
        }, 100);

        // Step 1: Ask for name
        await this.sleep(1000);
        await this.speakOnboarding("Hello! I'm your ElderCare assistant. What's your name?");

        // Listen for name
        const name = await this.listenOnboarding();
        if (!name) {
            await this.startOnboarding(); // Retry
            return;
        }
        this.state.userName = name;

        // Step 2: Ask for age
        await this.sleep(500);
        await this.speakOnboarding(`Nice to meet you, ${name}! How old are you?`);

        // Listen for age
        const ageText = await this.listenOnboarding();
        if (!ageText) {
            await this.startOnboarding(); // Retry
            return;
        }

        // Extract number from response
        const ageMatch = ageText.match(/\d+/);
        const age = ageMatch ? parseInt(ageMatch[0]) : null;

        if (!age || age < 1 || age > 120) {
            await this.speakOnboarding("I didn't catch that. Let's try again.");
            await this.sleep(1000);
            await this.startOnboarding();
            return;
        }
        this.state.userAge = age;

        // Step 3: Welcome message
        await this.sleep(500);
        await this.speakOnboarding(`Thank you, ${name}! I'm here to help you with calls, medications, and appointments. Just say what you need!`);

        // Save profile to session
        await this.saveProfile(name, age);

        // Hide onboarding overlay
        await this.sleep(1000);
        this.elements.onboardingOverlay.classList.remove('visible');
        setTimeout(() => {
            this.elements.onboardingOverlay.classList.add('hidden');
            this.state.onboardingComplete = true;
        }, 500);
    }

    async speakOnboarding(text) {
        return new Promise((resolve) => {
            // Display text with typing effect
            this.typeTextOnboarding(text);

            // Set circle to speaking state
            this.elements.onboardingCircle.classList.add('speaking');
            this.elements.onboardingPulse.classList.add('active');
            this.animateOnboardingBars();

            // Speak using TTS
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.9;
            utterance.pitch = 1.0;

            utterance.onend = () => {
                this.elements.onboardingCircle.classList.remove('speaking');
                this.elements.onboardingPulse.classList.remove('active');
                this.stopOnboardingBarsAnimation();
                resolve();
            };

            this.synthesis.speak(utterance);
        });
    }

    async listenOnboarding() {
        return new Promise((resolve) => {
            // Clear message
            this.elements.onboardingMessage.textContent = '';

            // Set circle to listening state
            this.elements.onboardingCircle.classList.add('listening');

            // Start recognition
            const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';

            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                this.elements.onboardingCircle.classList.remove('listening');
                resolve(transcript.trim());
            };

            recognition.onerror = () => {
                this.elements.onboardingCircle.classList.remove('listening');
                resolve(null);
            };

            recognition.onend = () => {
                this.elements.onboardingCircle.classList.remove('listening');
            };

            recognition.start();
        });
    }

    typeTextOnboarding(text) {
        this.elements.onboardingMessage.textContent = '';
        let index = 0;

        const typeChar = () => {
            if (index < text.length) {
                this.elements.onboardingMessage.textContent += text[index];
                index++;
                setTimeout(typeChar, this.typingSpeed);
            }
        };

        typeChar();
    }

    animateOnboardingBars() {
        const bars = this.elements.onboardingBars.querySelectorAll('.frequency-bar');
        this.onboardingBarsInterval = setInterval(() => {
            bars.forEach((bar, i) => {
                const height = 10 + Math.random() * 20;
                const angle = (i / bars.length) * Math.PI * 2;
                const centerX = 150;
                const centerY = 150;
                const radius = 145;
                const x1 = centerX + Math.cos(angle) * radius;
                const y1 = centerY + Math.sin(angle) * radius;
                const x2 = centerX + Math.cos(angle) * (radius + height);
                const y2 = centerY + Math.sin(angle) * (radius + height);
                bar.setAttribute('x2', x2);
                bar.setAttribute('y2', y2);
            });
        }, 100);
    }

    stopOnboardingBarsAnimation() {
        if (this.onboardingBarsInterval) {
            clearInterval(this.onboardingBarsInterval);
            this.onboardingBarsInterval = null;
        }
    }

    async saveProfile(name, age) {
        try {
            const response = await fetch('/api/session/profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, age })
            });

            if (!response.ok) {
                console.error('Failed to save profile');
            }
        } catch (error) {
            console.error('Error saving profile:', error);
        }
    }

    toggleRecording() {
        if (this.state.isRecording) {
            this.stopRecording();
        } else {
            this.startRecording();
        }
    }

    startRecording() {
        if (!this.recognition) {
            this.showToast('Speech recognition not available', 'error');
            return;
        }

        if (this.state.isRecording) return;

        this.state.isRecording = true;
        this.state.currentTranscript = '';
        this.elements.micButton.classList.add('listening');
        this.elements.statusText.textContent = 'Listening...';

        try {
            this.recognition.start();
        } catch (error) {
            console.error('Error starting recognition:', error);
            this.state.isRecording = false;
            this.elements.micButton.classList.remove('listening');
        }
    }

    stopRecording() {
        if (!this.state.isRecording) return;

        this.state.isRecording = false;
        this.elements.statusText.textContent = '';

        try {
            this.recognition.stop();
        } catch (error) {
            console.error('Error stopping recognition:', error);
        }
    }

    setMode(mode) {
        this.state.mode = mode;

        // Remove all state classes
        this.elements.mainCircle.classList.remove('idle', 'listening', 'speaking', 'thinking');

        // Add current state class
        this.elements.mainCircle.classList.add(mode);

        // Handle pulse effect
        if (mode === 'listening' || mode === 'speaking') {
            this.elements.pulseCircle.classList.add('active');
        } else {
            this.elements.pulseCircle.classList.remove('active');
        }

        // Animate frequency bars if speaking
        if (mode === 'speaking') {
            this.startFrequencyAnimation();
        } else {
            this.stopFrequencyAnimation();
        }
    }

    startFrequencyAnimation() {
        const bars = this.elements.frequencyBars.querySelectorAll('.frequency-bar');

        this.frequencyInterval = setInterval(() => {
            bars.forEach((bar, i) => {
                const height = 10 + Math.random() * 25;
                const angle = (i / bars.length) * Math.PI * 2;
                const centerX = 150;
                const centerY = 150;
                const radius = 145;
                const x1 = centerX + Math.cos(angle) * radius;
                const y1 = centerY + Math.sin(angle) * radius;
                const x2 = centerX + Math.cos(angle) * (radius + height);
                const y2 = centerY + Math.sin(angle) * (radius + height);
                bar.setAttribute('x2', x2);
                bar.setAttribute('y2', y2);
            });
        }, 100);
    }

    stopFrequencyAnimation() {
        if (this.frequencyInterval) {
            clearInterval(this.frequencyInterval);
            this.frequencyInterval = null;

            // Reset bars to default position
            const bars = this.elements.frequencyBars.querySelectorAll('.frequency-bar');
            bars.forEach((bar, i) => {
                const angle = (i / bars.length) * Math.PI * 2;
                const centerX = 150;
                const centerY = 150;
                const radius = 145;
                const x1 = centerX + Math.cos(angle) * radius;
                const y1 = centerY + Math.sin(angle) * radius;
                const x2 = centerX + Math.cos(angle) * (radius + 10);
                const y2 = centerY + Math.sin(angle) * (radius + 10);
                bar.setAttribute('x2', x2);
                bar.setAttribute('y2', y2);
            });
        }
    }

    displayUserMessage(text) {
        this.elements.userMessage.textContent = text;
        this.elements.userMessage.classList.add('visible');
    }

    async displayAgentMessage(text) {
        // Clear previous message
        this.elements.agentMessage.textContent = '';
        this.elements.agentMessage.classList.add('visible');

        // Type out word by word
        const words = text.split(' ');
        for (let i = 0; i < words.length; i++) {
            if (i > 0) {
                this.elements.agentMessage.textContent += ' ';
            }
            this.elements.agentMessage.textContent += words[i];
            await this.sleep(this.typingSpeed * 2); // Slower for words
        }
    }

    async processUserMessage(message) {
        console.log('Processing user message:', message);

        // Set to thinking mode
        this.setMode('thinking');
        this.elements.statusText.textContent = 'Thinking...';

        try {
            // Send to backend
            const response = await fetch('/api/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });

            const data = await response.json();
            console.log('Response from agent:', data);

            if (!data.success) {
                throw new Error(data.error || 'Unknown error');
            }

            // Display agent response
            this.setMode('speaking');
            this.elements.statusText.textContent = '';
            await this.displayAgentMessage(data.message);

            // Speak the response
            await this.speak(data.message);

            // Show UI if present
            if (data.ui) {
                this.showUIOverlay(data.ui);
            }

            // Return to idle
            this.setMode('idle');

        } catch (error) {
            console.error('Error processing message:', error);
            this.setMode('idle');
            this.elements.statusText.textContent = '';
            this.showToast('Sorry, something went wrong. Please try again.', 'error');
        }
    }

    async speak(text) {
        return new Promise((resolve) => {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.9;
            utterance.pitch = 1.0;

            utterance.onend = () => {
                resolve();
            };

            this.synthesis.speak(utterance);
        });
    }

    showUIOverlay(uiConfig) {
        console.log('Showing UI overlay:', uiConfig);

        // Hide main interface elements
        document.getElementById('voice-interface').style.opacity = '0';

        // Render UI content
        this.renderUIContent(uiConfig);

        // Show overlay
        this.elements.uiOverlay.classList.remove('hidden');
        setTimeout(() => {
            this.elements.uiOverlay.classList.add('visible');
        }, 100);
    }

    hideUIOverlay() {
        // Hide overlay
        this.elements.uiOverlay.classList.remove('visible');

        setTimeout(() => {
            this.elements.uiOverlay.classList.add('hidden');
            // Show main interface
            document.getElementById('voice-interface').style.opacity = '1';
        }, 300);
    }

    renderUIContent(uiConfig) {
        const templateId = uiConfig.template_id;

        if (templateId === 'call_ui') {
            this.renderCallUI(uiConfig);
        } else if (templateId === 'medication_card') {
            this.renderMedicationUI(uiConfig);
        } else if (templateId === 'appointment_card') {
            this.renderAppointmentUI(uiConfig);
        } else {
            // Generic UI
            this.renderGenericUI(uiConfig);
        }
    }

    renderCallUI(uiConfig) {
        const elements = uiConfig.ui_config.elements;
        const contactName = elements.find(e => e.id === 'contact_name')?.content || 'Contact';
        const relationship = elements.find(e => e.id === 'relationship')?.content || '';
        const callButton = elements.find(e => e.id === 'call_button');

        this.elements.uiContent.innerHTML = `
            <h2>📞 ${contactName}</h2>
            <p style="font-size: 22px; color: #666; margin-bottom: 30px;">${relationship}</p>
            <button onclick="window.open('${callButton.url}', '_blank')" style="font-size: 32px;">
                Start Video Call
            </button>
        `;
    }

    renderMedicationUI(uiConfig) {
        const elements = uiConfig.ui_config.elements;
        const medications = elements.filter(e => e.type === 'medication_item');

        let html = '<h2>💊 Your Medications</h2>';

        medications.forEach(med => {
            html += `
                <div class="medication-card">
                    <h3>${med.medication_name}</h3>
                    <p><strong>Dosage:</strong> ${med.dosage}</p>
                    <p><strong>Times:</strong> ${med.times.join(', ')}</p>
                    ${med.instructions ? `<p><strong>Instructions:</strong> ${med.instructions}</p>` : ''}
                </div>
            `;
        });

        this.elements.uiContent.innerHTML = html;
    }

    renderAppointmentUI(uiConfig) {
        const elements = uiConfig.ui_config.elements;
        const title = elements.find(e => e.id === 'title')?.content || 'Appointment';
        const doctor = elements.find(e => e.id === 'doctor')?.content || '';
        const dateTime = elements.find(e => e.id === 'datetime')?.content || '';
        const location = elements.find(e => e.id === 'location')?.content || '';

        this.elements.uiContent.innerHTML = `
            <h2>📅 ${title}</h2>
            <div class="appointment-card">
                <p><strong>Doctor:</strong> ${doctor}</p>
                <p><strong>Date & Time:</strong> ${dateTime}</p>
                <p><strong>Location:</strong> ${location}</p>
            </div>
            <button onclick="alert('Reminder set!')">Set Reminder</button>
        `;
    }

    renderGenericUI(uiConfig) {
        this.elements.uiContent.innerHTML = `
            <h2>${uiConfig.template_name || 'Information'}</h2>
            <p>${JSON.stringify(uiConfig, null, 2)}</p>
        `;
    }

    showToast(message, type = 'info') {
        this.elements.toast.textContent = message;
        this.elements.toast.className = `toast ${type}`;
        this.elements.toast.classList.remove('hidden');
        this.elements.toast.classList.add('visible');

        setTimeout(() => {
            this.elements.toast.classList.remove('visible');
            setTimeout(() => {
                this.elements.toast.classList.add('hidden');
            }, 300);
        }, 3000);
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.voiceUI = new VoiceModeUI();
    });
} else {
    window.voiceUI = new VoiceModeUI();
}
