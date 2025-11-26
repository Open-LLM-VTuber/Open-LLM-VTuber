const API_BASE_URL = window.location.origin;
const recorder = new AudioRecorder();

// Audio context and buffers
let audioContext = null;
let audioBuffers = [];
let pendingAudioPaths = new Set();
let currentAudioPath = null;
let ws = null;

// DOM Elements
const startRecordingBtn = document.getElementById('startRecording');
const stopRecordingBtn = document.getElementById('stopRecording');
const transcriptionArea = document.getElementById('transcription');
const asrStatus = document.getElementById('asrStatus');
const ttsInput = document.getElementById('ttsInput');
const generateSpeechBtn = document.getElementById('generateSpeech');
const ttsStatus = document.getElementById('ttsStatus');
const audioPlayer = document.getElementById('audioPlayer');
const downloadAudioBtn = document.getElementById('downloadAudio');
const audioFileInput = document.getElementById('audioFileInput');
const uploadAudioBtn = document.getElementById('uploadAudio');

// File upload handler with format conversion
uploadAudioBtn.addEventListener('click', async () => {
    const file = audioFileInput.files[0];
    if (!file) {
        asrStatus.textContent = 'Please select an audio file';
        asrStatus.className = 'status error';
        return;
    }

    try {
        asrStatus.textContent = 'Processing audio file...';
        asrStatus.className = 'status';

        // Convert audio to WAV format
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const arrayBuffer = await file.arrayBuffer();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        
        // Create WAV file
        const wavBuffer = await audioBufferToWav(audioBuffer);
        const wavBlob = new Blob([wavBuffer], { type: 'audio/wav' });

        const formData = new FormData();
        formData.append('file', wavBlob, 'recording.wav');

        const response = await fetch(`${API_BASE_URL}/asr`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('ASR request failed');

        const data = await response.json();
        transcriptionArea.value = data.text;
        asrStatus.textContent = 'Transcription complete!';
        asrStatus.className = 'status success';
        
        // Clean up
        audioContext.close();
    } catch (error) {
        asrStatus.textContent = 'Error: ' + error.message;
        asrStatus.className = 'status error';
    }
});

// Recording handlers
startRecordingBtn.addEventListener('click', async () => {
    try {
        asrStatus.textContent = 'Starting recording...';
        asrStatus.className = 'status';
        await recorder.start();
        startRecordingBtn.disabled = true;
        stopRecordingBtn.disabled = false;
        asrStatus.textContent = 'Recording...';
    } catch (error) {
        asrStatus.textContent = 'Error starting recording: ' + error.message;
        asrStatus.className = 'status error';
    }
});

stopRecordingBtn.addEventListener('click', async () => {
    try {
        const audioBlob = await recorder.stop();
        startRecordingBtn.disabled = false;
        stopRecordingBtn.disabled = true;
        asrStatus.textContent = 'Processing audio...';

        // Send to ASR endpoint
        const formData = new FormData();
        formData.append('file', audioBlob);

        const response = await fetch(`${API_BASE_URL}/asr`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('ASR request failed');

        const data = await response.json();
        transcriptionArea.value = data.text;
        asrStatus.textContent = 'Transcription complete!';
        asrStatus.className = 'status success';
    } catch (error) {
        asrStatus.textContent = 'Error: ' + error.message;
        asrStatus.className = 'status error';
        startRecordingBtn.disabled = false;
        stopRecordingBtn.disabled = true;
    }
});

// TTS handlers
function connectWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${wsProtocol}://${window.location.host}/tts-ws`);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        generateSpeechBtn.disabled = false;
        ttsStatus.textContent = 'Connected to TTS service';
        ttsStatus.className = 'status success';
        
        // Initialize AudioContext if needed
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        } else if (audioContext.state === 'suspended') {
            audioContext.resume();
        }
    };

    ws.onmessage = async (event) => {
        const response = JSON.parse(event.data);
        
        if (response.status === 'partial') {
            ttsStatus.textContent = 'Generating audio...';
            ttsStatus.className = 'status';
            
            try {
                const audioPath = response.audioPath.split('/').pop();
                pendingAudioPaths.add(audioPath);
                
                if (audioContext.state === 'suspended') {
                    await audioContext.resume();
                }
                
                // Use retry mechanism for fetching audio
                const audioResponse = await fetchWithRetry(`${API_BASE_URL}/cache/${audioPath}`);
                const arrayBuffer = await audioResponse.arrayBuffer();
                
                if (arrayBuffer.byteLength === 0) {
                    throw new Error('Empty audio data received');
                }
                
                const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
                audioBuffers.push(audioBuffer);
                pendingAudioPaths.delete(audioPath);
            } catch (error) {
                console.error('Error loading audio:', error);
                ttsStatus.textContent = 'Error loading audio: ' + error.message;
                ttsStatus.className = 'status error';
                pendingAudioPaths.clear();
            }
        } else if (response.status === 'complete') {
            // Wait for any pending audio loads to complete
            if (pendingAudioPaths.size > 0) {
                ttsStatus.textContent = 'Finalizing audio...';
                await new Promise(resolve => setTimeout(resolve, 500));
            }

            try {
                // Combine all audio buffers
                const targetSampleRate = 16000;
                const totalLength = audioBuffers.reduce((acc, buffer) => {
                    // Calculate resampled length if needed
                    const ratio = targetSampleRate / buffer.sampleRate;
                    return acc + Math.ceil(buffer.length * ratio);
                }, 0);
                
                const combinedBuffer = audioContext.createBuffer(
                    1,  // mono
                    totalLength,
                    targetSampleRate
                );
                
                let offset = 0;
                for (const buffer of audioBuffers) {
                    // Resample if needed
                    let channelData = buffer.getChannelData(0);
                    if (buffer.sampleRate !== targetSampleRate) {
                        channelData = await resampleAudio(channelData, buffer.sampleRate, targetSampleRate);
                    }
                    combinedBuffer.copyToChannel(channelData, 0, offset);
                    offset += channelData.length;
                }
                
                // Convert to WAV for download
                const wavBlob = new Blob([await audioBufferToWav(combinedBuffer)], { type: 'audio/wav' });
                const audioUrl = URL.createObjectURL(wavBlob);
                
                // Update audio player
                audioPlayer.src = audioUrl;
                audioPlayer.load();
                downloadAudioBtn.disabled = false;
                
                // Store for download
                currentAudioPath = audioUrl;
                
                ttsStatus.textContent = 'Audio generated successfully!';
                ttsStatus.className = 'status success';
            } catch (error) {
                console.error('Error combining audio:', error);
                ttsStatus.textContent = 'Error combining audio: ' + error.message;
                ttsStatus.className = 'status error';
            } finally {
                // Clear buffers
                audioBuffers = [];
                pendingAudioPaths.clear();
            }
        } else if (response.status === 'error') {
            ttsStatus.textContent = 'Error: ' + response.message;
            ttsStatus.className = 'status error';
            audioBuffers = [];
            pendingAudioPaths.clear();
        }
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        generateSpeechBtn.disabled = true;
        ttsStatus.textContent = 'Disconnected. Trying to reconnect...';
        ttsStatus.className = 'status error';
        
        // Clean up any pending audio resources
        audioBuffers = [];
        pendingAudioPaths.clear();
        if (currentAudioPath) {
            URL.revokeObjectURL(currentAudioPath);
            currentAudioPath = null;
        }
        
        setTimeout(connectWebSocket, 5000);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        ttsStatus.textContent = 'Connection error. Retrying...';
        ttsStatus.className = 'status error';
        
        // Clean up audio resources on error
        audioBuffers = [];
        pendingAudioPaths.clear();
        if (currentAudioPath) {
            URL.revokeObjectURL(currentAudioPath);
            currentAudioPath = null;
        }
    };
}

// Convert AudioBuffer to WAV with specific format requirements
async function audioBufferToWav(buffer) {
    // Resample to 16kHz if needed
    let audioData = buffer.getChannelData(0);
    if (buffer.sampleRate !== 16000) {
        audioData = await resampleAudio(audioData, buffer.sampleRate, 16000);
    }
    
    const numChannels = 1; // Mono
    const sampleRate = 16000;
    const format = 1; // PCM
    const bitDepth = 16;
    
    const dataLength = audioData.length * (bitDepth / 8);
    const headerLength = 44;
    const totalLength = headerLength + dataLength;
    
    const arrayBuffer = new ArrayBuffer(totalLength);
    const view = new DataView(arrayBuffer);
    
    // Write WAV header
    writeString(view, 0, 'RIFF');
    view.setUint32(4, totalLength - 8, true);
    writeString(view, 8, 'WAVE');
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, format, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numChannels * (bitDepth / 8), true);
    view.setUint16(32, numChannels * (bitDepth / 8), true);
    view.setUint16(34, bitDepth, true);
    writeString(view, 36, 'data');
    view.setUint32(40, dataLength, true);
    
    // Write audio data
    floatTo16BitPCM(view, 44, audioData);
    
    return arrayBuffer;
}

function resampleAudio(audioData, originalSampleRate, targetSampleRate) {
    const ratio = targetSampleRate / originalSampleRate;
    const newLength = Math.round(audioData.length * ratio);
    const result = new Float32Array(newLength);
    
    for (let i = 0; i < newLength; i++) {
        const position = i / ratio;
        const index = Math.floor(position);
        const fraction = position - index;
        
        if (index + 1 < audioData.length) {
            result[i] = audioData[index] * (1 - fraction) + audioData[index + 1] * fraction;
        } else {
            result[i] = audioData[index];
        }
    }
    
    return result;
}

function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}

function floatTo16BitPCM(view, offset, input) {
    for (let i = 0; i < input.length; i++, offset += 2) {
        const s = Math.max(-1, Math.min(1, input[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
}

generateSpeechBtn.addEventListener('click', () => {
    const text = ttsInput.value.trim();
    if (!text) {
        ttsStatus.textContent = 'Please enter some text';
        ttsStatus.className = 'status error';
        return;
    }

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ text }));
        ttsStatus.textContent = 'Generating audio...';
        ttsStatus.className = 'status';
    } else {
        ttsStatus.textContent = 'Connection lost. Reconnecting...';
        ttsStatus.className = 'status error';
        connectWebSocket();
    }
});

downloadAudioBtn.addEventListener('click', () => {
    if (currentAudioPath) {
        const link = document.createElement('a');
        link.href = currentAudioPath;
        link.download = `combined_audio_${Date.now()}.wav`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
});

// Clean up resources when leaving the page
window.addEventListener('beforeunload', () => {
    if (audioContext) {
        audioContext.close();
    }
    if (ws) {
        ws.close();
    }
    // Clean up any blob URLs
    if (currentAudioPath) {
        URL.revokeObjectURL(currentAudioPath);
    }
    // Clear any pending audio buffers
    audioBuffers = [];
    pendingAudioPaths.clear();
});

// Initialize WebSocket connection
connectWebSocket();

async function fetchWithRetry(url, maxRetries = 3, retryDelay = 1000) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response;
        } catch (error) {
            if (i === maxRetries - 1) throw error;
            await new Promise(resolve => setTimeout(resolve, retryDelay));
        }
    }
}

// ========================
// Direct Control UI logic
// ========================

// Elements
const dcSessionSelect = document.getElementById('dcSessionSelect');
const dcRefreshSessions = document.getElementById('dcRefreshSessions');
const dcApplyAll = document.getElementById('dcApplyAll');

const dcTabSpeak = document.getElementById('dcTabSpeak');
const dcTabSystem = document.getElementById('dcTabSystem');
const dcTabRespond = document.getElementById('dcTabRespond');

const dcSpeakPanel = document.getElementById('dcSpeakPanel');
const dcSystemPanel = document.getElementById('dcSystemPanel');
const dcRespondPanel = document.getElementById('dcRespondPanel');

const dcSpeakText = document.getElementById('dcSpeakText');
const dcSpeakBtn = document.getElementById('dcSpeakBtn');
const dcSpeakStatus = document.getElementById('dcSpeakStatus');

const dcSystemText = document.getElementById('dcSystemText');
const dcSystemMode = document.getElementById('dcSystemMode');
const dcSystemBtn = document.getElementById('dcSystemBtn');
const dcSystemStatus = document.getElementById('dcSystemStatus');

const dcRespondText = document.getElementById('dcRespondText');
const dcRespondBtn = document.getElementById('dcRespondBtn');
const dcRespondStatus = document.getElementById('dcRespondStatus');

function switchDcTab(target) {
    dcSpeakPanel.style.display = target === 'speak' ? 'block' : 'none';
    dcSystemPanel.style.display = target === 'system' ? 'block' : 'none';
    dcRespondPanel.style.display = target === 'respond' ? 'block' : 'none';
}

async function loadSessions() {
    try {
        const res = await fetch(`${API_BASE_URL}/v1/sessions`);
        if (!res.ok) throw new Error('Failed to load sessions');
        const sessions = await res.json();
        dcSessionSelect.innerHTML = '';
        if (!sessions || sessions.length === 0) {
            const opt = document.createElement('option');
            opt.value = '';
            opt.textContent = 'No sessions';
            dcSessionSelect.appendChild(opt);
            return;
        }
        for (const uid of sessions) {
            const opt = document.createElement('option');
            opt.value = uid;
            opt.textContent = uid;
            dcSessionSelect.appendChild(opt);
        }
    } catch (e) {
        // keep select as-is
    }
}

function buildTargetingPayload() {
    const payload = {};
    if (dcApplyAll.checked) {
        payload.apply_to_all = true;
    } else {
        const uid = dcSessionSelect.value;
        if (uid) payload.client_uid = uid;
    }
    return payload;
}

dcRefreshSessions.addEventListener('click', () => {
    loadSessions();
});

dcTabSpeak.addEventListener('click', () => switchDcTab('speak'));
dcTabSystem.addEventListener('click', () => switchDcTab('system'));
dcTabRespond.addEventListener('click', () => switchDcTab('respond'));

dcSpeakBtn.addEventListener('click', async () => {
    const text = (dcSpeakText.value || '').trim();
    if (!text) {
        dcSpeakStatus.textContent = 'Please enter text to speak';
        dcSpeakStatus.className = 'status error';
        return;
    }
    try {
        dcSpeakStatus.textContent = 'Sending...';
        dcSpeakStatus.className = 'status';
        const body = { text, ...buildTargetingPayload() };
        const res = await fetch(`${API_BASE_URL}/v1/control/speak`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Speak request failed');
        dcSpeakStatus.textContent = `OK: ${data.message}`;
        dcSpeakStatus.className = 'status success';
    } catch (e) {
        dcSpeakStatus.textContent = 'Error: ' + e.message;
        dcSpeakStatus.className = 'status error';
    }
});

dcSystemBtn.addEventListener('click', async () => {
    const text = (dcSystemText.value || '').trim();
    const mode = (dcSystemMode.value || 'append');
    if (!text && mode !== 'reset') {
        dcSystemStatus.textContent = 'Please enter system instruction or choose reset';
        dcSystemStatus.className = 'status error';
        return;
    }
    try {
        dcSystemStatus.textContent = 'Applying...';
        dcSystemStatus.className = 'status';
        const body = { text, mode, ...buildTargetingPayload() };
        const res = await fetch(`${API_BASE_URL}/v1/control/system`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'System request failed');
        dcSystemStatus.textContent = `OK: ${data.message}`;
        dcSystemStatus.className = 'status success';
    } catch (e) {
        dcSystemStatus.textContent = 'Error: ' + e.message;
        dcSystemStatus.className = 'status error';
    }
});

dcRespondBtn.addEventListener('click', async () => {
    const text = (dcRespondText.value || '').trim();
    if (!text) {
        dcRespondStatus.textContent = 'Please enter message text';
        dcRespondStatus.className = 'status error';
        return;
    }
    try {
        dcRespondStatus.textContent = 'Triggering...';
        dcRespondStatus.className = 'status';
        const body = { text, ...buildTargetingPayload() };
        const res = await fetch(`${API_BASE_URL}/v1/control/respond`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Respond request failed');
        dcRespondStatus.textContent = `OK: ${data.message}`;
        dcRespondStatus.className = 'status success';
    } catch (e) {
        dcRespondStatus.textContent = 'Error: ' + e.message;
        dcRespondStatus.className = 'status error';
    }
});

// Initialize sessions and default tab
loadSessions();
switchDcTab('speak');