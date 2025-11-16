/**
 * ElderCare Agent - Web Speech API Integration
 * Provides speech-to-text and text-to-speech for accessible voice interaction
 */

class SpeechManager {
    constructor() {
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.isListening = false;
        this.isSpeaking = false;

        // Speech recognition configuration
        this.recognitionConfig = {
            language: 'en-US',
            continuous: false,
            interimResults: false,
            maxAlternatives: 1
        };

        // Speech synthesis configuration
        this.synthesisConfig = {
            voice: null,
            rate: 0.9,  // Slightly slower for elderly users
            pitch: 1.0,
            volume: 1.0
        };

        this.initializeSpeechRecognition();
        this.initializeSpeechSynthesis();
    }

    /**
     * Initialize Web Speech API recognition
     */
    initializeSpeechRecognition() {
        // Check browser support
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            console.error('Web Speech API not supported in this browser');
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.lang = this.recognitionConfig.language;
        this.recognition.continuous = this.recognitionConfig.continuous;
        this.recognition.interimResults = this.recognitionConfig.interimResults;
        this.recognition.maxAlternatives = this.recognitionConfig.maxAlternatives;

        // Event handlers
        this.recognition.onstart = () => {
            this.isListening = true;
            console.log('Speech recognition started');
            this.onListeningStart();
        };

        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            const confidence = event.results[0][0].confidence;

            console.log(`Recognized: "${transcript}" (confidence: ${confidence})`);
            this.onSpeechResult(transcript, confidence);
        };

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.isListening = false;
            this.onListeningError(event.error);
        };

        this.recognition.onend = () => {
            this.isListening = false;
            console.log('Speech recognition ended');
            this.onListeningEnd();
        };
    }

    /**
     * Initialize speech synthesis with preferred voice
     */
    initializeSpeechSynthesis() {
        if (!this.synthesis) {
            console.error('Speech synthesis not supported');
            return;
        }

        // Wait for voices to load
        if (this.synthesis.getVoices().length === 0) {
            this.synthesis.onvoiceschanged = () => {
                this.selectPreferredVoice();
            };
        } else {
            this.selectPreferredVoice();
        }
    }

    /**
     * Select a clear, natural-sounding voice
     */
    selectPreferredVoice() {
        const voices = this.synthesis.getVoices();

        // Prefer female voice, US English, natural quality
        const preferredVoices = [
            'Google US English Female',
            'Microsoft Zira',
            'Samantha',
            'Karen',
            'Victoria'
        ];

        for (const prefName of preferredVoices) {
            const voice = voices.find(v => v.name.includes(prefName));
            if (voice) {
                this.synthesisConfig.voice = voice;
                console.log(`Selected voice: ${voice.name}`);
                return;
            }
        }

        // Fallback to any English voice
        const englishVoice = voices.find(v => v.lang.startsWith('en'));
        if (englishVoice) {
            this.synthesisConfig.voice = englishVoice;
            console.log(`Selected fallback voice: ${englishVoice.name}`);
        }
    }

    /**
     * Start listening for speech input
     */
    startListening() {
        if (!this.recognition) {
            console.error('Speech recognition not available');
            this.onListeningError('not_supported');
            return;
        }

        if (this.isListening) {
            console.warn('Already listening');
            return;
        }

        // Stop any ongoing speech first
        this.stopSpeaking();

        try {
            this.recognition.start();
        } catch (error) {
            console.error('Failed to start recognition:', error);
            this.onListeningError(error.message);
        }
    }

    /**
     * Stop listening
     */
    stopListening() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
        }
    }

    /**
     * Speak text using speech synthesis
     */
    speak(text, options = {}) {
        if (!this.synthesis) {
            console.error('Speech synthesis not available');
            return;
        }

        // Stop any ongoing speech
        this.stopSpeaking();

        const utterance = new SpeechSynthesisUtterance(text);

        // Apply configuration
        utterance.voice = this.synthesisConfig.voice;
        utterance.rate = options.rate || this.synthesisConfig.rate;
        utterance.pitch = options.pitch || this.synthesisConfig.pitch;
        utterance.volume = options.volume || this.synthesisConfig.volume;

        // Event handlers
        utterance.onstart = () => {
            this.isSpeaking = true;
            console.log('Started speaking:', text);
            this.onSpeakingStart();
        };

        utterance.onend = () => {
            this.isSpeaking = false;
            console.log('Finished speaking');
            this.onSpeakingEnd();
        };

        utterance.onerror = (event) => {
            console.error('Speech synthesis error:', event.error);
            this.isSpeaking = false;
            this.onSpeakingError(event.error);
        };

        // Speak
        this.synthesis.speak(utterance);
    }

    /**
     * Stop speaking
     */
    stopSpeaking() {
        if (this.synthesis && this.isSpeaking) {
            this.synthesis.cancel();
            this.isSpeaking = false;
        }
    }

    /**
     * Check if browser supports speech features
     */
    static isSupported() {
        const hasRecognition = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
        const hasSynthesis = !!window.speechSynthesis;

        return {
            recognition: hasRecognition,
            synthesis: hasSynthesis,
            full: hasRecognition && hasSynthesis
        };
    }

    // Event handlers (to be overridden by app)
    onListeningStart() {}
    onListeningEnd() {}
    onListeningError(error) {}
    onSpeechResult(transcript, confidence) {}
    onSpeakingStart() {}
    onSpeakingEnd() {}
    onSpeakingError(error) {}
}

// Export for use in app.js
window.SpeechManager = SpeechManager;
