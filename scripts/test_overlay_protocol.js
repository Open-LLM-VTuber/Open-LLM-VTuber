/**
 * Unit tests for the Ruta B overlay protocol (audit §1.3, §1.4, §6.11).
 *
 * The overlay has to answer ``frontend-playback-complete`` once the audio
 * queue drains, otherwise the backend waits ``PLAYBACK_ACK_TIMEOUT`` (180 s)
 * on every single turn (A18). These tests drive the real
 * ``web_tool/overlay-protocol.js`` with a fake socket and a fake player, so
 * the behaviour can be checked without OBS, a browser or a running backend.
 *
 *     node scripts/test_overlay_protocol.js
 */

"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
    createOverlayProtocol,
    mimeForFormat,
    buildDataUrl
} = require("../web_tool/overlay-protocol.js");

/** Fake audio adapter: ``finish()`` plays the "chunk ended" callback. */
function fakePlayer(behaviour) {
    const player = {
        current: null,
        played: [],
        stopped: 0,
        play(url, done) {
            this.played.push(url);
            if (behaviour === "throw") {
                throw new Error("no audio device");
            }
            if (behaviour === "end-now") {
                done();
                return;
            }
            this.current = { url, done };
        },
        stop() {
            this.stopped += 1;
            this.current = null;
        },
        finish() {
            const current = this.current;
            this.current = null;
            if (current) {
                current.done();
            }
        }
    };
    return player;
}

function harness(options) {
    const opts = options || {};
    const sent = [];
    const subtitles = [];
    const texts = [];
    const stages = [];
    const player = opts.player || fakePlayer();
    const protocol = createOverlayProtocol({
        send(message) {
            sent.push(message);
        },
        audio: player,
        onSubtitle: (displayText) => subtitles.push(displayText),
        onSubtitleText: (text) => texts.push(text),
        onStage: (message) => stages.push(message),
        onConfig: opts.onConfig
    });
    return {
        sent,
        subtitles,
        texts,
        stages,
        player,
        protocol,
        acks: () => sent.filter((m) => m.type === "frontend-playback-complete"),
        playStarts: () => sent.filter((m) => m.type === "audio-play-start")
    };
}

function chunk(text, extra) {
    return Object.assign(
        {
            type: "audio",
            audio: "QUJD",
            audio_format: "wav",
            volumes: [1, 0.5],
            slice_length: 20,
            display_text: { name: "tarot", avatar: "", text: text },
            actions: null,
            forwarded: false
        },
        extra || {}
    );
}

test("mimeForFormat and buildDataUrl map the export formats", () => {
    assert.equal(mimeForFormat("wav"), "audio/wav");
    assert.equal(mimeForFormat("MP3"), "audio/mpeg");
    assert.equal(mimeForFormat(undefined), "audio/wav");
    assert.equal(mimeForFormat("flac"), "audio/wav");
    assert.equal(buildDataUrl("QUJD", "mp3"), "data:audio/mpeg;base64,QUJD");
});

test("acks immediately when the turn produced no audio", () => {
    const h = harness();

    h.protocol.handleMessage({ type: "backend-synth-complete" });

    assert.equal(h.acks().length, 1);
    assert.equal(h.playStarts().length, 0);
    assert.equal(h.player.played.length, 0);
});

test("does not ack until the last chunk has finished playing", () => {
    const h = harness();

    h.protocol.handleMessage({ type: "control", text: "conversation-chain-start" });
    h.protocol.handleMessage(chunk("hola"));
    h.protocol.handleMessage({ type: "backend-synth-complete" });

    assert.equal(h.acks().length, 0, "still playing, no ack yet");
    assert.equal(h.protocol.isPlaying(), true);

    h.player.finish();

    assert.equal(h.acks().length, 1);
    assert.equal(h.protocol.isPlaying(), false);
});

test("plays every chunk in order with one audio-play-start each", () => {
    const h = harness();

    h.protocol.handleMessage(chunk("uno"));
    h.protocol.handleMessage(chunk("dos", { audio_format: "mp3" }));

    assert.equal(h.player.played.length, 1, "chunks are serialised");
    assert.equal(h.player.played[0], "data:audio/wav;base64,QUJD");
    assert.equal(h.protocol.pendingChunks(), 1);

    h.player.finish();

    assert.equal(h.player.played[1], "data:audio/mpeg;base64,QUJD");
    assert.equal(h.playStarts().length, 2);
    assert.deepEqual(
        h.playStarts().map((m) => m.display_text.text),
        ["uno", "dos"]
    );
    assert.deepEqual(
        h.subtitles.map((d) => d.text),
        ["uno", "dos"]
    );
});

test("silent and forwarded chunks are shown but never block the ack", () => {
    const h = harness();

    h.protocol.handleMessage(chunk("otro cliente", { audio: null, forwarded: true }));
    h.protocol.handleMessage(chunk("eco", { audio: null }));
    h.protocol.handleMessage({ type: "backend-synth-complete" });

    assert.equal(h.player.played.length, 0);
    assert.equal(h.playStarts().length, 0);
    assert.equal(h.acks().length, 1);
    assert.deepEqual(
        h.subtitles.map((d) => d.text),
        ["otro cliente", "eco"]
    );
});

test("conversation-chain-start stops playback and swallows the stale ack", () => {
    const h = harness();

    h.protocol.handleMessage(chunk("viejo"));
    h.protocol.handleMessage({ type: "backend-synth-complete" });
    h.protocol.handleMessage({ type: "control", text: "conversation-chain-start" });

    assert.equal(h.player.stopped, 1);
    assert.equal(h.acks().length, 0);
    assert.equal(h.protocol.isPlaying(), false);
    assert.equal(h.protocol.pendingChunks(), 0);
});

test("interrupt-signal drops the queue without acking", () => {
    const h = harness();

    h.protocol.handleMessage(chunk("uno"));
    h.protocol.handleMessage(chunk("dos"));
    h.protocol.handleMessage({ type: "interrupt-signal", text: "conversation-interrupted" });

    assert.equal(h.player.stopped, 1);
    assert.equal(h.acks().length, 0);
    assert.equal(h.protocol.pendingChunks(), 0);
});

test("a chunk that cannot be played does not freeze the turn", () => {
    const h = harness({ player: fakePlayer("throw") });

    h.protocol.handleMessage(chunk("uno"));
    h.protocol.handleMessage(chunk("dos"));
    h.protocol.handleMessage({ type: "backend-synth-complete" });

    assert.equal(h.acks().length, 1);
    assert.equal(h.protocol.isPlaying(), false);
});

test("a synchronous end (or error) still drains the queue", () => {
    const h = harness({ player: fakePlayer("end-now") });

    h.protocol.handleMessage(chunk("uno"));
    h.protocol.handleMessage(chunk("dos"));
    h.protocol.handleMessage({ type: "backend-synth-complete" });

    assert.equal(h.player.played.length, 2);
    assert.equal(h.acks().length, 1);
});

test("a stale end callback after a reset must not ack the new turn", () => {
    const h = harness();

    h.protocol.handleMessage(chunk("viejo"));
    const staleDone = h.player.current.done;
    h.protocol.handleMessage({ type: "control", text: "conversation-chain-start" });
    staleDone();

    assert.equal(h.acks().length, 0);
    assert.equal(h.protocol.isPlaying(), false);
});

test("reconnect fetches the cached stage and clears pending work", () => {
    const h = harness();

    h.protocol.handleMessage(chunk("viejo"));
    h.protocol.handleMessage({ type: "backend-synth-complete" });
    h.protocol.onOpen();

    const stages = h.sent.filter((m) => m.type === "fetch-stage");
    assert.equal(stages.length, 1, "one fetch-stage per (re)connect");
    assert.deepEqual(h.sent[h.sent.length - 1], { type: "fetch-stage" });
    assert.equal(h.acks().length, 0);
    assert.equal(h.protocol.waitingForAck(), false);
    assert.equal(h.protocol.isPlaying(), false);
});

test("routes the UI messages the overlay renders", () => {
    const h = harness();

    h.protocol.handleMessage({ type: "stage-update", stage: "tarot_main" });
    h.protocol.handleMessage({ type: "full-text", text: "Pensando..." });
    h.protocol.handleMessage({ type: "force-new-message" });
    h.protocol.handleMessage({ type: "user-input-transcription", text: "hola" });
    h.protocol.handleMessage({ type: "expression", actions: { happy: 1 } });
    h.protocol.handleMessage({ type: "not-a-real-type" });
    h.protocol.handleMessage(null);
    h.protocol.handleMessage("texto suelto");

    assert.deepEqual(h.stages, [{ type: "stage-update", stage: "tarot_main" }]);
    assert.deepEqual(h.texts, ["Pensando...", ""]);
});

test("a whole turn hits the wire in the order the backend expects", () => {
    const h = harness();

    h.protocol.handleMessage({ type: "control", text: "conversation-chain-start" });
    h.protocol.handleMessage({ type: "full-text", text: "Pensando..." });
    h.protocol.handleMessage(chunk("una frase"));
    h.protocol.handleMessage(chunk("otra frase"));
    h.protocol.handleMessage({ type: "backend-synth-complete" });
    h.player.finish();
    h.player.finish();
    h.protocol.handleMessage({ type: "control", text: "conversation-chain-end" });

    assert.deepEqual(
        h.sent.map((m) => m.type),
        ["audio-play-start", "audio-play-start", "frontend-playback-complete"]
    );
    assert.equal(h.player.played.length, 2);
});
