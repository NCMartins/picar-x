// Voice control for the PiCar: speak, the car acts and answers.
//
// Speech recognition runs in the browser rather than on the Pi, which is what
// makes this work with no extra hardware - your phone is already a very good
// microphone. The recognised text is POSTed to /api/voice/command, where
// Claude decides what the car should do.
//
// Two things about the browser side are worth knowing:
//
//   * Speech recognition and microphone access need a *secure context*. Over
//     plain http://<pi-ip>:5000 the browser blocks the microphone with no
//     useful error. See docs/VOICE.md for the three ways round it; the typed
//     command box below always works regardless.
//   * "stop" never goes to the model. It's matched here and sent straight to
//     the emergency-stop endpoint, so stopping the car doesn't wait on a
//     network round-trip to an API.

const VOICE_WAKE_WORDS = ['claude', 'cloud', 'clod'];  // recognisers mishear it a lot
const VOICE_STOP_PHRASES = ['stop', 'stop stop', 'halt', 'whoa', 'freeze', 'stop it'];

let recognition = null;
let handsFree = false;
let listening = false;
let commandInFlight = false;

// ===== Initialization =====
document.addEventListener('DOMContentLoaded', () => {
    const panel = document.getElementById('voice-panel');
    if (!panel) return;

    refreshVoiceStatus();
    refreshOnboardListener();
    setInterval(refreshVoiceStatus, 5000);
    setInterval(refreshOnboardListener, 5000);
    loadTranscript();
    setupRecognition();

    document.getElementById('voice-talk')?.addEventListener('click', toggleListening);
    document.getElementById('voice-handsfree')?.addEventListener('change', (e) => {
        handsFree = e.target.checked;
        if (handsFree) {
            startListening();
        } else {
            stopListening();
        }
    });
    document.getElementById('voice-stop')?.addEventListener('click', emergencyStop);
    document.getElementById('voice-listener-toggle')
        ?.addEventListener('click', toggleOnboardListener);
    document.getElementById('voice-reset')?.addEventListener('click', resetConversation);
    document.getElementById('voice-text-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        const input = document.getElementById('voice-text-input');
        const text = input.value.trim();
        if (text) {
            input.value = '';
            sendCommand(text);
        }
    });
});

// ===== Status =====
async function refreshVoiceStatus() {
    try {
        const response = await fetch('/api/voice/status');
        const data = await response.json();
        const badge = document.getElementById('voice-state');

        if (!data.enabled || !data.available) {
            badge.textContent = 'not configured';
            badge.className = 'voice-badge voice-badge-off';
            document.getElementById('voice-hint').textContent =
                'Set ANTHROPIC_API_KEY on the Pi and restart the server to enable this.';
            setVoiceControlsEnabled(false);
            return;
        }

        setVoiceControlsEnabled(true);
        if (data.busy) {
            badge.textContent = 'working';
            badge.className = 'voice-badge voice-badge-busy';
        } else if (listening) {
            badge.textContent = 'listening';
            badge.className = 'voice-badge voice-badge-live';
        } else {
            badge.textContent = 'ready';
            badge.className = 'voice-badge voice-badge-ready';
        }
        document.getElementById('voice-hint').textContent =
            `${data.model} · max ${data.max_speed}% speed · ${data.max_move_seconds}s per move` +
            (data.speaker_available ? ' · speaking through the car' : ' · speaking through this browser');
    } catch (error) {
        console.error('Voice status check failed:', error);
    }
}

function setVoiceControlsEnabled(enabled) {
    ['voice-talk', 'voice-handsfree', 'voice-text-input'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.disabled = !enabled;
    });
}

// ===== The car's own microphone =====
// Optional second input path: with a USB mic on the Pi the car listens for
// its wake word itself and this browser isn't in the loop at all. The panel
// stays hidden unless the Pi reports the hardware is actually usable.
async function refreshOnboardListener() {
    const panel = document.getElementById('voice-onboard');
    if (!panel) return;

    try {
        const response = await fetch('/api/voice/listener');
        const data = await response.json();

        // Show the control if it's configured or already running; a Pi with
        // no microphone shouldn't advertise a button that can't work.
        panel.hidden = !(data.configured || data.running);

        const state = document.getElementById('voice-onboard-state');
        const button = document.getElementById('voice-listener-toggle');
        if (data.running) {
            const heard = data.last_heard ? ` · last heard: “${data.last_heard}”` : '';
            state.textContent = data.awaiting_command
                ? `Car's own microphone: waiting for your command${heard}`
                : `Car's own microphone: listening for “${data.wake_word}”${heard}`;
            button.textContent = 'Stop listening on the car';
        } else {
            state.textContent = data.error
                ? `Car's own microphone: ${data.error}`
                : "Car's own microphone: off";
            button.textContent = 'Listen on the car';
        }
    } catch (error) {
        console.debug('Listener status unavailable');
    }
}

async function toggleOnboardListener() {
    const button = document.getElementById('voice-listener-toggle');
    const starting = button.textContent.startsWith('Listen');
    button.disabled = true;

    try {
        const response = await fetch(
            `/api/voice/listener/${starting ? 'start' : 'stop'}`, { method: 'POST' });
        const data = await response.json();
        if (!response.ok) {
            addTranscriptLine('system', data.message || 'Could not change the microphone.');
        }
    } catch (error) {
        addTranscriptLine('system', 'Could not reach the car.');
    } finally {
        button.disabled = false;
        refreshOnboardListener();
    }
}

// ===== Speech recognition =====
function setupRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        disableMic('This browser has no speech recognition. Chrome, Edge or Safari can do it — or type a command below.');
        return;
    }
    if (!window.isSecureContext) {
        disableMic('The microphone needs a secure connection (HTTPS or localhost). See docs/VOICE.md — or type a command below.');
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = false;   // one utterance per start; we restart as needed
    recognition.interimResults = true;

    recognition.addEventListener('result', (event) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const result = event.results[i];
            if (result.isFinal) {
                handleUtterance(result[0].transcript.trim());
            } else {
                interim += result[0].transcript;
            }
        }
        if (interim) showInterim(interim);
    });

    recognition.addEventListener('error', (event) => {
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
            disableMic('Microphone permission was denied. Allow it in the browser, or type a command below.');
            return;
        }
        // 'no-speech' and 'aborted' are routine; keep hands-free mode alive.
        if (event.error !== 'no-speech' && event.error !== 'aborted') {
            console.warn('Speech recognition error:', event.error);
        }
    });

    recognition.addEventListener('end', () => {
        listening = false;
        updateTalkButton();
        // Hands-free means keep the recogniser alive across utterances. The
        // browser ends a session after each one, so restart it - unless a
        // command is running, in which case restarting is handled after.
        if (handsFree && !commandInFlight) {
            startListening();
        }
    });
}

function disableMic(message) {
    const button = document.getElementById('voice-talk');
    const toggle = document.getElementById('voice-handsfree');
    if (button) { button.disabled = true; button.title = message; }
    if (toggle) { toggle.disabled = true; }
    document.getElementById('voice-mic-note').textContent = message;
}

function toggleListening() {
    if (listening) {
        // A deliberate tap means stop, so drop out of hands-free too -
        // otherwise the 'end' handler would immediately restart listening.
        handsFree = false;
        const toggle = document.getElementById('voice-handsfree');
        if (toggle) toggle.checked = false;
        stopListening();
    } else {
        startListening();
    }
}

function startListening() {
    if (!recognition || listening) return;
    try {
        recognition.start();
        listening = true;
        updateTalkButton();
    } catch (error) {
        // start() throws if a session is already running; harmless.
        console.debug('recognition.start():', error.message);
    }
}

function stopListening() {
    if (!recognition) return;
    try { recognition.stop(); } catch (error) { /* already stopped */ }
    listening = false;
    updateTalkButton();
}

function updateTalkButton() {
    const button = document.getElementById('voice-talk');
    if (!button) return;
    button.textContent = listening ? '🔴 Listening…' : '🎤 Tap to talk';
    button.classList.toggle('listening', listening);
}

function handleUtterance(text) {
    if (!text) return;
    showInterim('');
    const normalized = text.toLowerCase().replace(/[.,!?]/g, '').trim();

    // Stopping never waits for the model.
    if (VOICE_STOP_PHRASES.includes(normalized)) {
        addTranscriptLine('operator', text);
        emergencyStop();
        return;
    }

    // In hands-free mode, only act on utterances addressed to the car, so a
    // conversation in the room doesn't drive it across the floor.
    if (handsFree) {
        const wake = VOICE_WAKE_WORDS.find((word) =>
            normalized === word || normalized.startsWith(word + ' '));
        if (!wake) {
            console.debug('Ignoring (no wake word):', text);
            return;
        }
        text = text.slice(wake.length).replace(/^[,\s]+/, '').trim();
        if (!text) return;
    }

    sendCommand(text);
}

// ===== Commands =====
async function sendCommand(text) {
    if (commandInFlight) {
        addTranscriptLine('system', 'Still working on the last command.');
        return;
    }
    commandInFlight = true;
    addTranscriptLine('operator', text);
    setThinking(true);

    try {
        const response = await fetch('/api/voice/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });
        const data = await response.json();

        if (!response.ok) {
            addTranscriptLine('system', data.message || `Request failed (${response.status})`);
            return;
        }

        if (data.actions?.length) {
            addTranscriptLine('actions', data.actions
                .map((a) => `${a.name}: ${a.detail}${a.aborted ? ' (stopped)' : ''}`)
                .join(' · '));
        }
        if (data.reply) {
            addTranscriptLine('claude', data.reply);
            // The Pi speaks through its own speaker when espeak-ng is there;
            // otherwise fall back to this browser so there's always a voice.
            if (!data.spoken_on_pi) speakInBrowser(data.reply);
        }
        if (data.hit_tool_limit) {
            addTranscriptLine('system', 'Stopped early: too many actions for one command.');
        }
    } catch (error) {
        console.error('Voice command failed:', error);
        addTranscriptLine('system', 'Could not reach the car.');
    } finally {
        commandInFlight = false;
        setThinking(false);
        refreshVoiceStatus();
        if (handsFree) startListening();
    }
}

async function emergencyStop() {
    try {
        await fetch('/api/voice/stop', { method: 'POST' });
        addTranscriptLine('system', 'Emergency stop.');
        if (window.speechSynthesis) window.speechSynthesis.cancel();
    } catch (error) {
        console.error('Emergency stop failed:', error);
        addTranscriptLine('system', 'Emergency stop could not reach the car — use the STOP button.');
    }
}

async function resetConversation() {
    try {
        await fetch('/api/voice/reset', { method: 'POST' });
        document.getElementById('voice-transcript').innerHTML = '';
        addTranscriptLine('system', 'Conversation cleared.');
    } catch (error) {
        console.error('Reset failed:', error);
    }
}

async function loadTranscript() {
    try {
        const response = await fetch('/api/voice/transcript');
        const data = await response.json();
        (data.transcript || []).forEach((line) => addTranscriptLine(line.role, line.text));
    } catch (error) {
        console.debug('No transcript to restore');
    }
}

// ===== Browser speech output (fallback when the Pi can't speak) =====
function speakInBrowser(text) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    utterance.rate = 1.05;
    window.speechSynthesis.speak(utterance);
}

// ===== Transcript UI =====
function addTranscriptLine(role, text) {
    const log = document.getElementById('voice-transcript');
    if (!log || !text) return;

    const line = document.createElement('div');
    line.className = `voice-line voice-line-${role}`;
    const label = { operator: 'You', claude: 'Car', actions: 'Did', system: '—' }[role] || role;
    line.innerHTML = `<span class="voice-role">${label}</span><span class="voice-text"></span>`;
    line.querySelector('.voice-text').textContent = text;

    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
}

function showInterim(text) {
    const el = document.getElementById('voice-interim');
    if (el) el.textContent = text;
}

function setThinking(thinking) {
    const el = document.getElementById('voice-thinking');
    if (el) el.hidden = !thinking;
}
