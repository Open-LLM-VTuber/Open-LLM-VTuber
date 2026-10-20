/**
 * Protocol logic for the Ruta B overlay (AUDITORIA-MVP-TAROT.md §2.4 and §6.11).
 *
 * Kept apart from ``overlay.html`` on purpose: there is no DOM and no Web Audio
 * here, so ``node scripts/test_overlay_protocol.js`` can drive a whole turn
 * (audio chunks -> drain -> ``frontend-playback-complete``) without OBS, a
 * browser or a running backend.
 *
 * Contract (audit §1.3 / §1.4):
 *   server -> overlay: control/conversation-chain-start, full-text, audio,
 *                      expression, backend-synth-complete, interrupt-signal,
 *                      force-new-message, stage-update, set-model-and-conf
 *   overlay -> server: fetch-stage, audio-play-start, frontend-playback-complete
 *
 * The ack is mandatory: without it the backend waits ``PLAYBACK_ACK_TIMEOUT``
 * (180 s) before closing *every* turn (audit A18).
 */
(function (root, factory) {
    if (typeof module === "object" && module.exports) {
        module.exports = factory();
    } else {
        root.OverlayProtocol = factory();
    }
}(typeof self !== "undefined" ? self : this, function () {
    "use strict";

    var MIME_BY_FORMAT = {
        wav: "audio/wav",
        mp3: "audio/mpeg",
        ogg: "audio/ogg",
        webm: "audio/webm"
    };

    /**
     * Pick the MIME type of an ``audio_format`` field (A23 allows wav and mp3).
     * Unknown or missing formats fall back to wav, which is the default export.
     */
    function mimeForFormat(format) {
        if (typeof format !== "string") {
            return MIME_BY_FORMAT.wav;
        }
        return MIME_BY_FORMAT[format.toLowerCase()] || MIME_BY_FORMAT.wav;
    }

    /** Build the ``data:`` URL an ``<audio>`` element can play. */
    function buildDataUrl(base64, format) {
        return "data:" + mimeForFormat(format) + ";base64," + base64;
    }

    /**
     * Create the message pump of the overlay.
     *
     * @param {Object} options
     * @param {Function} options.send       Sends one message object to the socket.
     * @param {Object} [options.audio]      ``{play(url, done), stop()}`` adapter.
     *                                      ``done`` must be called once when the
     *                                      chunk ends (or fails to play).
     * @param {Function} [options.onStage]  Receives a ``stage-update`` message.
     * @param {Function} [options.onSubtitle] Receives a ``display_text`` object.
     * @param {Function} [options.onSubtitleText] Receives a plain string.
     * @param {Function} [options.onExpression] Receives ``actions``.
     * @param {Function} [options.onUserText] Receives the user transcription.
     * @param {Function} [options.onConfig] Receives ``set-model-and-conf``.
     * @param {Function} [options.onStatus] Receives short status strings (HUD).
     */
    function createOverlayProtocol(options) {
        var opts = options || {};
        var send = opts.send || function () {};
        var audio = opts.audio || null;
        var onStage = opts.onStage || function () {};
        var onSubtitle = opts.onSubtitle || function () {};
        var onSubtitleText = opts.onSubtitleText || function () {};
        var onExpression = opts.onExpression || function () {};
        var onUserText = opts.onUserText || function () {};
        var onConfig = opts.onConfig || function () {};
        var onStatus = opts.onStatus || function () {};

        var queue = [];          // playable chunks of the current turn
        var playing = null;      // chunk handed to the audio adapter
        var synthComplete = false;

        function emit(message) {
            try {
                send(message);
            } catch (error) {
                onStatus("send failed: " + error);
            }
        }

        function stopPlayback() {
            queue.length = 0;
            playing = null;
            if (audio && typeof audio.stop === "function") {
                try {
                    audio.stop();
                } catch (error) {
                    // A stopped element that throws is not a reason to stall.
                }
            }
        }

        // One ``frontend-playback-complete`` per ``backend-synth-complete``
        // edge, and only once nothing is left to play (audit §1.4).
        function maybeAck() {
            if (!synthComplete || playing || queue.length > 0) {
                return;
            }
            synthComplete = false;
            emit({ type: "frontend-playback-complete" });
            onStatus("acked playback");
        }

        function finish(entry) {
            // Stale callback: the turn was reset or interrupted meanwhile.
            if (playing !== entry) {
                return;
            }
            playing = null;
            pump();
        }

        function pump() {
            while (!playing && queue.length > 0) {
                var entry = queue.shift();
                playing = entry;
                emit({ type: "audio-play-start", display_text: entry.displayText });
                try {
                    audio.play(buildDataUrl(entry.base64, entry.format), function () {
                        finish(entry);
                    });
                } catch (error) {
                    // A chunk that cannot be played must not freeze the turn.
                    finish(entry);
                }
            }
            maybeAck();
        }

        function handleAudio(message) {
            var displayText = message.display_text || null;
            if (displayText) {
                onSubtitle(displayText);
            }
            // Payloads without audio are display-only: subtitles forwarded for
            // the other group members (A21), never a reason to wait.
            if (!message.audio || message.forwarded === true) {
                onStatus(message.forwarded ? "forwarded chunk" : "silent chunk");
                return;
            }
            queue.push({
                base64: message.audio,
                format: message.audio_format,
                displayText: displayText
            });
            pump();
        }

        function interrupt(reason) {
            stopPlayback();
            synthComplete = false;
            onStatus(reason || "interrupted");
        }

        function handleMessage(message) {
            if (!message || typeof message !== "object") {
                return;
            }
            var type = message.type;

            if (type === "audio") {
                handleAudio(message);
            } else if (type === "control") {
                if (message.text === "conversation-chain-start") {
                    interrupt("chain-start");
                } else if (message.text === "conversation-chain-end") {
                    synthComplete = false;
                    onStatus("chain-end");
                }
            } else if (type === "interrupt-signal") {
                interrupt("interrupted");
            } else if (type === "backend-synth-complete") {
                synthComplete = true;
                maybeAck();
            } else if (type === "full-text") {
                onSubtitleText(message.text || "");
            } else if (type === "user-input-transcription") {
                onUserText(message.text || "");
            } else if (type === "expression") {
                onExpression(message.actions || null);
            } else if (type === "stage-update") {
                onStage(message);
            } else if (type === "force-new-message") {
                onSubtitleText("");
            } else if (type === "set-model-and-conf") {
                onConfig(message);
            }
            // heartbeat-ack, background-files, ... are irrelevant here.
        }

        function onOpen() {
            // A reload mid-turn loses the queue but must not lose the scene.
            stopPlayback();
            synthComplete = false;
            emit({ type: "fetch-stage" });
            onStatus("connected");
        }

        return {
            handleMessage: handleMessage,
            onOpen: onOpen,
            interrupt: function (reason) { interrupt(reason || "manual"); },
            isPlaying: function () { return playing !== null; },
            pendingChunks: function () { return queue.length; },
            waitingForAck: function () { return synthComplete; }
        };
    }

    return {
        createOverlayProtocol: createOverlayProtocol,
        mimeForFormat: mimeForFormat,
        buildDataUrl: buildDataUrl
    };
}));
