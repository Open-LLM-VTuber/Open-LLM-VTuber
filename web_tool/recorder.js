class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }

    async start() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: 16000
                }
            });
            this.mediaRecorder = new MediaRecorder(stream);
            this.audioChunks = [];
            this.isRecording = true;

            this.mediaRecorder.addEventListener("dataavailable", (event) => {
                this.audioChunks.push(event.data);
            });

            this.mediaRecorder.start();
            return true;
        } catch (error) {
            console.error("Error starting recording:", error);
            throw error;
        }
    }

    async stop() {
        return new Promise(async (resolve) => {
            this.mediaRecorder.addEventListener("stop", async () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
                this.isRecording = false;

                // Convert to WAV with correct format
                const arrayBuffer = await audioBlob.arrayBuffer();
                const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);

                // Create WAV file
                const wavBuffer = await this.createWAV(audioBuffer);
                const wavBlob = new Blob([wavBuffer], { type: 'audio/wav' });

                resolve(wavBlob);
            });

            this.mediaRecorder.stop();
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
        });
    }

    async createWAV(audioBuffer) {
        const numChannels = 1; // Mono
        const sampleRate = 16000; // Target sample rate
        const format = 1; // PCM
        const bitDepth = 16;

        // Resample if needed
        let samples = audioBuffer.getChannelData(0);
        if (audioBuffer.sampleRate !== sampleRate) {
            samples = await this.resampleAudio(samples, audioBuffer.sampleRate, sampleRate);
        }

        const dataLength = samples.length * (bitDepth / 8);
        const headerLength = 44;
        const totalLength = headerLength + dataLength;

        const buffer = new ArrayBuffer(totalLength);
        const view = new DataView(buffer);

        // Write WAV header
        this.writeString(view, 0, 'RIFF');
        view.setUint32(4, totalLength - 8, true);
        this.writeString(view, 8, 'WAVE');
        this.writeString(view, 12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, format, true);
        view.setUint16(22, numChannels, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * numChannels * (bitDepth / 8), true);
        view.setUint16(32, numChannels * (bitDepth / 8), true);
        view.setUint16(34, bitDepth, true);
        this.writeString(view, 36, 'data');
        view.setUint32(40, dataLength, true);

        // Write audio data
        this.floatTo16BitPCM(view, 44, samples);

        return buffer;
    }

    writeString(view, offset, string) {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    }

    floatTo16BitPCM(view, offset, input) {
        for (let i = 0; i < input.length; i++, offset += 2) {
            const s = Math.max(-1, Math.min(1, input[i]));
            view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        }
    }

    async resampleAudio(audioData, originalSampleRate, targetSampleRate) {
        const originalLength = audioData.length;
        const ratio = targetSampleRate / originalSampleRate;
        const newLength = Math.round(originalLength * ratio);
        const result = new Float32Array(newLength);

        for (let i = 0; i < newLength; i++) {
            const position = i / ratio;
            const index = Math.floor(position);
            const fraction = position - index;

            if (index + 1 < originalLength) {
                result[i] = audioData[index] * (1 - fraction) + audioData[index + 1] * fraction;
            } else {
                result[i] = audioData[index];
            }
        }

        return result;
    }

    isActive() {
        return this.isRecording;
    }
}