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

            // FORCE RESTART on 'no-speech' (silence) or 'network' errors
            // This creates the "Always On" experience
            if (event.error === 'no-speech' || event.error === 'network') {
                console.log('Silence detected (no-speech), automatically restarting...');
                if (this.state.onboardingComplete && this.state.mode === 'idle') {
                    // Small delay to prevent CPU spinning, but fast enough to feel continuous
                    setTimeout(() => {
                        this.startRecording();
                    }, 100);
                    return;
                }
            }

            if (event.error !== 'no-speech') {
                this.showToast(`Error: ${event.error}`, 'error');
            }
        };

        this.recognition.onend = () => {
            console.log('Speech recognition ended');
            this.setMode('idle');
            this.state.isRecording = false;
            this.elements.micButton.classList.remove('listening');
            
            // AUTO-RESTART LOOP
            // Unless the user explicitly stopped it (we don't have a stop button logic here, so assume always on)
            if (this.state.onboardingComplete && this.state.mode === 'idle') {
                console.log('Microphone disconnected, restarting loop...');
                setTimeout(() => {
                    this.startRecording();
                }, 200);
            }
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

    async waitForUserInteraction() {
        return new Promise((resolve) => {
            const startBtn = document.getElementById('start-voice-btn');

            // Show the button
            if (startBtn) {
                startBtn.style.display = 'block';

                startBtn.onclick = () => {
                    console.log('User clicked to enable voice');
                    startBtn.style.display = 'none';

                    // Play a silent sound to initialize audio context
                    const utterance = new SpeechSynthesisUtterance('');
                    this.synthesis.speak(utterance);

                    resolve();
                };
            } else {
                // Fallback if button not found
                console.warn('Start voice button not found');
                resolve();
            }
        });
    }

    async startOnboarding() {
        console.log('Starting onboarding...');

        // Show onboarding overlay
        this.elements.onboardingOverlay.classList.remove('hidden');
        setTimeout(() => {
            this.elements.onboardingOverlay.classList.add('visible');
        }, 100);

        // Wait for user interaction to enable audio
        await this.waitForUserInteraction();

        // Step 1: Ask for name
        await this.sleep(1000);
        await this.speakOnboarding("Hello! What's your name?");

        // Listen for name
        console.log('⏳ Waiting for name response...');
        let nameResponse = await this.listenOnboarding();
        console.log('Got name response:', nameResponse);
        if (!nameResponse) {
            await this.startOnboarding(); // Retry
            return;
        }
        
        // Extract actual name from responses like "My name is John" or "I'm John" or just "John"
        let name = nameResponse;
        if (nameResponse.toLowerCase().includes('my name is')) {
            name = nameResponse.toLowerCase().replace('my name is', '').trim();
        } else if (nameResponse.toLowerCase().includes("i'm")) {
            name = nameResponse.toLowerCase().replace("i'm", '').replace('i am', '').trim();
        } else if (nameResponse.toLowerCase().includes('i am')) {
            name = nameResponse.toLowerCase().replace('i am', '').trim();
        }
        
        // Capitalize first letter of each word
        name = name.split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
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

        // Step 3: Simple welcome - don't list features
        await this.sleep(500);
        await this.speakOnboarding(`Thank you, ${name}! I'm ready to help. What would you like to do?`);

        // Save profile to session
        await this.saveProfile(name, age);

        // Hide onboarding overlay
        await this.sleep(1000);
        this.elements.onboardingOverlay.classList.remove('visible');
        setTimeout(() => {
            this.elements.onboardingOverlay.classList.add('hidden');
            this.state.onboardingComplete = true;
            
            // Start listening for user's first request after onboarding
            setTimeout(() => {
                console.log('Starting listening after onboarding...');
                this.startRecording();
            }, 1000);
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
            utterance.volume = 1.0;

            utterance.onstart = () => {
                console.log('Speaking:', text);
            };

            utterance.onend = () => {
                console.log('Finished speaking');
                this.elements.onboardingCircle.classList.remove('speaking');
                this.elements.onboardingPulse.classList.remove('active');
                this.stopOnboardingBarsAnimation();
                resolve();
            };

            utterance.onerror = (event) => {
                console.error('Speech synthesis error:', event.error);
                // If speech fails, still resolve after text is displayed
                setTimeout(() => {
                    this.elements.onboardingCircle.classList.remove('speaking');
                    this.elements.onboardingPulse.classList.remove('active');
                    this.stopOnboardingBarsAnimation();
                    resolve();
                }, 2000);
            };

            // Try to speak
            try {
                this.synthesis.cancel(); // Clear any pending speech
                this.synthesis.speak(utterance);
                console.log('Speech synthesis started');
            } catch (error) {
                console.error('Failed to start speech:', error);
                setTimeout(resolve, 2000);
            }
        });
    }

    async listenOnboarding() {
        return new Promise((resolve) => {
            console.log('👂 Starting to listen for user response...');
            
            // Clear message
            this.elements.onboardingMessage.textContent = '';

            // Set circle to listening state
            this.elements.onboardingCircle.classList.add('listening');

            // Start recognition
            const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';

            recognition.onstart = () => {
                console.log('✅ Speech recognition started, say your answer now...');
            };

            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                console.log('📝 Heard:', transcript);
                this.elements.onboardingCircle.classList.remove('listening');
                resolve(transcript.trim());
            };

            recognition.onerror = (event) => {
                console.error('❌ Speech recognition error:', event.error);
                this.elements.onboardingCircle.classList.remove('listening');
                resolve(null);
            };

            recognition.onend = () => {
                console.log('🛑 Speech recognition ended');
                this.elements.onboardingCircle.classList.remove('listening');
            };

            try {
                recognition.start();
                console.log('🎤 Recognition.start() called');
            } catch (error) {
                console.error('❌ Failed to start recognition:', error);
                resolve(null);
            }
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

            // Check if response is OK
            if (!response.ok) {
                const errorText = await response.text();
                console.error('HTTP error:', response.status, errorText);
                throw new Error(`Server error: ${response.status}`);
            }

            const data = await response.json();
            console.log('Full response from agent:', data);

            // Check for actual errors (not just unclear intent)
            // If there's a message, it's a valid response even if success is false
            if (data.success === false && !data.message) {
                const errorMsg = data.error || 'Unknown error';
                console.error('Agent returned error:', errorMsg);
                throw new Error(errorMsg);
            }

            // Display agent response
            this.setMode('speaking');
            this.elements.statusText.textContent = '';

            // Make sure we have a message to display
            const agentMessage = data.message || 'I heard you, but I\'m not sure how to respond.';
            await this.displayAgentMessage(agentMessage);

            // Speak the response
            try {
                await this.speak(agentMessage);
            } catch (speechError) {
                console.error('Text-to-speech error:', speechError);
                // Continue even if speech fails
            }

            // Show UI if present
            if (data.ui) {
                this.showUIOverlay(data.ui);
            }

            // Return to idle
            this.setMode('idle');
            
            // Auto-restart listening for continuous conversation (grandma doesn't need to press button again)
            // Wait longer for the agent to finish speaking and user to process
            setTimeout(() => {
                if (this.state.onboardingComplete && !this.state.isRecording) {
                    console.log('Auto-restarting listening for continuous conversation...');
                    this.startRecording();
                }
            }, 2500); // Wait 2.5 seconds to ensure speech finishes and user has time to respond

        } catch (error) {
            console.error('Error processing message:', error);
            console.error('Error details:', {
                message: error.message,
                stack: error.stack
            });

            this.setMode('idle');
            this.elements.statusText.textContent = '';

            // Show more helpful error message
            const errorMsg = error.message || 'Unknown error occurred';
            this.showToast(`Error: ${errorMsg}. Please try again.`, 'error');

            // Also display error in agent message area
            this.elements.agentMessage.textContent = `Sorry, I encountered an error: ${errorMsg}`;
            this.elements.agentMessage.classList.add('visible');
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

        if (templateId === 'emergency_ui') {
            this.renderEmergencyUI(uiConfig);
        } else if (templateId === 'call_ui') {
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
        const config = uiConfig.ui_config;
        
        // Handle both old format (elements array) and new format (direct properties)
        let contactName, relationship, phone, callUrl;
        
        if (config.elements) {
            // Old format with elements array
            contactName = config.elements.find(e => e.id === 'contact_name')?.content || 'Contact';
            relationship = config.elements.find(e => e.id === 'relationship')?.content || '';
            const callButton = config.elements.find(e => e.id === 'call_button');
            callUrl = callButton?.url || '#';
        } else {
            // New simpler format
            contactName = config.contact_name || 'Contact';
            relationship = config.relationship || '';
            phone = config.phone || '';
            // Create WhatsApp call URL
            callUrl = phone ? `https://wa.me/${phone.replace(/[^0-9]/g, '')}` : '#';
        }

        const relText = relationship ? `(${relationship})` : '';

        this.elements.uiContent.innerHTML = `
            <div style="text-align: center; padding: 30px;">
                <h2 style="font-size: 36px; margin-bottom: 10px;">📞 ${contactName}</h2>
                <p style="font-size: 24px; color: #666; margin-bottom: 10px;">${relText}</p>
                ${phone ? `<p style="font-size: 20px; color: #888; margin-bottom: 30px;">${phone}</p>` : ''}
                <button onclick="window.open('${callUrl}', '_blank')" 
                        style="font-size: 28px; padding: 20px 40px; background: #25D366; color: white; border: none; border-radius: 15px; cursor: pointer;">
                    📱 Start Video Call
                </button>
            </div>
        `;
    }

    renderEmergencyUI(uiConfig) {
        const config = uiConfig.ui_config;
        const situation = config.situation || 'Emergency';
        const emergencyNumber = config.emergency_number || '911';
        
        this.elements.uiContent.innerHTML = `
            <div style="text-align: center; padding: 40px; background: #ff0000; color: white; border-radius: 20px;">
                <h1 style="font-size: 60px; margin-bottom: 20px; animation: pulse 1s infinite;">🚨</h1>
                <h2 style="font-size: 42px; margin-bottom: 20px;">CALLING ${emergencyNumber}</h2>
                <p style="font-size: 28px; margin-bottom: 30px;">${situation}</p>
                <button onclick="window.location.href='tel:${emergencyNumber}'" 
                        style="font-size: 36px; padding: 25px 50px; background: white; color: red; border: none; border-radius: 15px; cursor: pointer; font-weight: bold; animation: pulse 1s infinite;">
                    📞 CALL NOW
                </button>
                <p style="font-size: 20px; margin-top: 30px;">Help is on the way. Stay calm.</p>
            </div>
            <style>
                @keyframes pulse {
                    0%, 100% { transform: scale(1); }
                    50% { transform: scale(1.1); }
                }
            </style>
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

