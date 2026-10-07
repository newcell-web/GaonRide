/* voice.js — MediaRecorder-based voice capture (passenger.html only) */

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

// Parsed data from the last AI result, read by passenger.js confirm button
let _lastParsed = null;

function getLastParsed() {
    return _lastParsed;
}

// ---------------------------------------------------------------------------
// DOM initialisation
// ---------------------------------------------------------------------------

function initVoice() {
    // Check MediaRecorder support
    if (!navigator.mediaDevices || !window.MediaRecorder) {
        const unavailable = document.getElementById('voice-unavailable');
        const micBtn = document.getElementById('mic-btn');
        if (unavailable) unavailable.removeAttribute('hidden');
        if (micBtn) micBtn.setAttribute('hidden', '');
        return;
    }

    const micBtn = document.getElementById('mic-btn');
    if (!micBtn) return;

    micBtn.addEventListener('click', () => {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    });
}

// ---------------------------------------------------------------------------
// Recording lifecycle
// ---------------------------------------------------------------------------

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = [];
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) {
                audioChunks.push(e.data);
            }
        };

        mediaRecorder.onstop = () => {
            // Stop all tracks to release mic
            stream.getTracks().forEach(t => t.stop());
            const blob = new Blob(audioChunks, { type: 'audio/webm' });
            uploadAudio(blob);
        };

        mediaRecorder.start();
        isRecording = true;

        // Update UI
        const micBtn = document.getElementById('mic-btn');
        const status = document.getElementById('recording-status');
        if (micBtn) {
            micBtn.classList.add('recording');
            const label = micBtn.querySelector('.mic-label');
            if (label) label.textContent = 'Tap to Stop';
        }
        if (status) status.removeAttribute('hidden');

    } catch (err) {
        showToast('Could not access microphone: ' + err.message, 'error');
    }
}

function stopRecording() {
    if (!mediaRecorder || mediaRecorder.state === 'inactive') return;
    mediaRecorder.stop();
    isRecording = false;

    // Restore UI immediately; audio upload will happen in onstop
    const micBtn = document.getElementById('mic-btn');
    const status = document.getElementById('recording-status');
    if (micBtn) {
        micBtn.classList.remove('recording');
        const label = micBtn.querySelector('.mic-label');
        if (label) label.textContent = 'Tap to Record';
    }
    if (status) status.setAttribute('hidden', '');
}

// ---------------------------------------------------------------------------
// Upload and transcribe
// ---------------------------------------------------------------------------

async function uploadAudio(blob) {
    showLoading('Transcribing your voice...');

    const formData = new FormData();
    formData.append('file', blob, 'recording.webm');

    try {
        // Do NOT set Content-Type — browser sets multipart/form-data with boundary
        const result = await apiFetch('/voice/transcribe', {
            method: 'POST',
            body: formData,
        });

        const transcriptionText = document.getElementById('transcription-text');
        const transcriptionResult = document.getElementById('transcription-result');
        const parseBtn = document.getElementById('parse-btn');

        if (transcriptionText) transcriptionText.textContent = result.text;
        if (transcriptionResult) transcriptionResult.removeAttribute('hidden');

        if (parseBtn) {
            // Replace to remove any old listener, then re-attach
            const newBtn = parseBtn.cloneNode(true);
            parseBtn.parentNode.replaceChild(newBtn, parseBtn);
            newBtn.addEventListener('click', () => parseTranscription(result.text));
        }

    } catch (err) {
        if (err.message && err.message.includes('503')) {
            const unavailable = document.getElementById('voice-unavailable');
            if (unavailable) {
                unavailable.querySelector('p').textContent =
                    '⚠️ AI service is unavailable. Add a GROQ_API_KEY to enable voice transcription.';
                unavailable.removeAttribute('hidden');
            }
        } else {
            showToast(err.message || 'Transcription failed', 'error');
        }
    } finally {
        hideLoading();
    }
}

// ---------------------------------------------------------------------------
// Parse transcription with AI
// ---------------------------------------------------------------------------

async function parseTranscription(text) {
    showLoading('AI is interpreting your request...');
    try {
        const data = await apiFetch('/voice/parse', {
            method: 'POST',
            body: JSON.stringify({ text }),
        });
        showAIResult(data.parsed, text);
    } catch (err) {
        const msg = err.message || '';
        if (msg.includes('503')) {
            showToast('AI service is unavailable. Please type your request manually.', 'error');
        } else if (msg.includes('422')) {
            showToast('Could not understand the request. Please try again or type it manually.', 'error');
        } else {
            showToast(msg || 'Could not parse request', 'error');
        }
    } finally {
        hideLoading();
    }
}

// ---------------------------------------------------------------------------
// Show AI result card
// ---------------------------------------------------------------------------

function showAIResult(parsed, rawText) {
    _lastParsed = parsed;

    // Populate display fields
    const set = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val || '—';
    };

    set('ai-origin',      parsed.origin);
    set('ai-destination', parsed.destination);
    set('ai-date',        formatDate(parsed.travel_date));
    set('ai-time',        formatTime(parsed.preferred_time));
    set('ai-passengers',  parsed.passenger_count);
    set('ai-language',    parsed.language || 'en');
    set('ai-notes',       parsed.notes || '—');

    const card = document.getElementById('ai-result-card');
    if (card) card.removeAttribute('hidden');
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', initVoice);
