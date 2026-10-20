/**
 * Cross-check the real backend frames against the real overlay protocol.
 *
 * `scripts/test_overlay_protocol.js` drives `web_tool/overlay-protocol.js` with
 * hand-made messages, and `scripts/test_stage_obs.py` checks the Python
 * producers against their own assumptions. Neither would notice if both halves
 * disagreed about the wire format — which is exactly the failure that leaves a
 * live stream silent (A18).
 *
 * This test replays `tests/fixtures/overlay-wire.json`: the exact
 * `json.dumps()` strings the backend passes to `websocket_send`, exported by
 * `scripts/export_overlay_fixtures.py`. Producer and consumer are therefore
 * checked against the same bytes.
 *
 *     python scripts/export_overlay_fixtures.py    # after changing the backend
 *     python scripts/export_overlay_fixtures.py --check
 *     node scripts/test_overlay_wire.js
 */

"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const { createOverlayProtocol } = require("../web_tool/overlay-protocol.js");

const FIXTURE = path.join(__dirname, "..", "tests", "fixtures", "overlay-wire.json");
const fixture = JSON.parse(fs.readFileSync(FIXTURE, "utf8"));

/** Every wire string of a scenario, including the frames that follow the ack. */
function wireFrames(scenario) {
    return scenario.frames.concat(scenario.after_ack || []);
}

/** Overlay + fake socket + fake `<audio>` adapter, fed with wire strings. */
function harness() {
    const sent = [];
    const subtitles = [];
    const texts = [];
    const stages = [];
    const statuses = [];
    const player = {
        current: null,
        played: [],
        stopped: 0,
        play(url, done) {
            this.played.push(url);
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
    const protocol = createOverlayProtocol({
        send(message) {
            sent.push(message);
        },
        audio: player,
        onStage(message) {
            stages.push(message);
        },
        onSubtitle(displayText) {
            subtitles.push(displayText);
        },
        onSubtitleText(text) {
            texts.push(text);
        },
        onStatus(status) {
            statuses.push(status);
        }
    });
    return {
        protocol,
        player,
        sent,
        subtitles,
        texts,
        stages,
        statuses,
        feed(frames) {
            for (const frame of frames) {
                assert.equal(typeof frame, "string", "frames must be wire strings");
                protocol.handleMessage(JSON.parse(frame));
            }
        },
        acks() {
            return sent.filter((message) => message.type === "frontend-playback-complete");
        },
        starts() {
            return sent.filter((message) => message.type === "audio-play-start");
        }
    };
}

/**
 * What each scenario must do in the overlay. A scenario without an entry here
 * fails the suite on purpose: the exporter cannot add a case that the consumer
 * silently ignores.
 */
const expectations = {
    turn_wav_two_chunks(h, scenario) {
        h.feed(scenario.frames);

        assert.equal(h.player.played.length, 1, "chunks play one at a time");
        assert.match(h.player.played[0], /^data:audio\/wav;base64,/);
        assert.equal(h.acks().length, 0, "nothing is acked while audio plays");

        h.player.finish();
        assert.equal(h.player.played.length, 2, "the second chunk follows in order");
        assert.equal(h.acks().length, 0, "still one chunk to play");

        h.player.finish();
        assert.equal(h.acks().length, 1, "exactly one ack per turn");
        assert.equal(h.protocol.waitingForAck(), false);
        assert.equal(h.protocol.pendingChunks(), 0);

        const starts = h.starts();
        assert.equal(starts.length, 2, "one audio-play-start per chunk");
        assert.equal(starts[0].display_text.name, "Tarotista");
        assert.match(starts[0].display_text.text, /La Torre/);
        assert.match(starts[1].display_text.text, /tarot/);
        assert.equal(h.subtitles.length, 2, "subtitles follow the audio");

        // The server only sends these once it has the ack: they must not ack again.
        h.feed(scenario.after_ack);
        assert.equal(h.acks().length, 1, "chain-end must not ack twice");
        assert.ok(h.statuses.includes("chain-end"));
        assert.ok(h.texts.includes(""), "force-new-message clears the subtitle");
    },

    turn_mp3_two_chunks(h, scenario) {
        h.feed(scenario.frames);

        assert.match(h.player.played[0], /^data:audio\/mpeg;base64,/);
        h.player.finish();
        h.player.finish();
        assert.match(h.player.played[1], /^data:audio\/mpeg;base64,/);
        assert.equal(h.acks().length, 1);

        h.feed(scenario.after_ack);
        assert.equal(h.acks().length, 1, "chain-end must not ack twice");
    },

    turn_silent_and_forwarded(h, scenario) {
        h.feed(scenario.frames);

        assert.equal(h.player.played.length, 0, "silent chunks are not played");
        assert.equal(h.acks().length, 1, "the ack must not wait for audio: null");
        assert.equal(h.protocol.waitingForAck(), false);
        assert.equal(h.protocol.pendingChunks(), 0);
        assert.ok(h.statuses.includes("silent chunk"));
        assert.ok(h.statuses.includes("forwarded chunk"));
        assert.equal(h.subtitles.length, 2, "both chunks still show a subtitle");

        h.feed(scenario.after_ack);
        assert.equal(h.acks().length, 1, "chain-end must not ack twice");
    },

    interrupt_after_chunk(h, scenario) {
        h.feed(scenario.frames);

        assert.equal(h.acks().length, 0, "the server closes an interrupted turn");
        // One stop when the turn starts (chain-start clears the queue) and one
        // when the interrupt arrives: the audio never survives the signal.
        assert.equal(h.player.stopped, 2);
        assert.equal(h.protocol.isPlaying(), false);
        assert.equal(h.protocol.pendingChunks(), 0);
        assert.ok(h.statuses.includes("interrupted"));
    },

    stage_background_only(h, scenario) {
        h.feed(scenario.frames);

        assert.equal(h.stages.length, 1);
        assert.equal(h.stages[0].stage, "tarot_main");
        assert.equal(h.stages[0].background, "/bg/tarot_table.png");
        assert.equal(
            "props" in h.stages[0],
            false,
            "no props key means: keep the cards already on screen"
        );
    },

    stage_with_props(h, scenario) {
        h.feed(scenario.frames);

        const stage = h.stages[0];
        assert.deepEqual(
            stage.props.map((prop) => prop.id),
            ["card_1", "card_2"],
            "the prop without src was dropped by the backend"
        );
        for (const prop of stage.props) {
            assert.match(prop.src, /^\/bg\/cards\//, "every prop keeps a playable src");
        }
        assert.equal(stage.props[1].x, 1, "x is clamped to 0..1");
        assert.equal(stage.props[1].y, 0, "y is clamped to 0..1");
        assert.equal(stage.props[0].rot, -8);
        assert.equal(stage.props[0].scale, 1.1);
        assert.equal(stage.props[0].opacity, 0.95);
    },

    stage_transition_none(h, scenario) {
        h.feed(scenario.frames);

        assert.equal(h.stages[0].transition, "none");
        assert.equal(h.stages[0].duration_ms, 0);
        assert.equal(h.stages[0].stage, "quiet");
    },

    tarot_draw_three_cards(h, scenario) {
        h.feed(scenario.frames);

        const stage = h.stages[0];
        assert.equal(stage.stage, "card_of_the_day");
        assert.equal(
            "background" in stage,
            false,
            "a draw alone is a valid stage-update: the table art is optional"
        );
        assert.deepEqual(
            stage.props.map((prop) => prop.id),
            ["card_1", "card_2", "card_3"]
        );
        for (const prop of stage.props) {
            assert.match(prop.src, /^\/bg\/cards\/major_\d\d\.svg$/);
            assert.equal("label" in prop, false, "art props are images");
            assert.ok(prop.x > 0 && prop.x < 1, "cards are spread inside the frame");
            assert.equal(prop.y, 0.68, "cards sit low, the avatar keeps the top");
            assert.equal(prop.scale, 0.55, "three cards must not overlap");
            assert.ok(prop.rot === 0 || prop.rot === 180, "reversed cards are rotated");
        }
    },

    tarot_draw_text_fallback(h, scenario) {
        h.feed(scenario.frames);

        const stage = h.stages[0];
        assert.equal(stage.props.length, 3);
        for (const prop of stage.props) {
            assert.equal("src" in prop, false, "no art: the overlay draws the text card");
            assert.equal(typeof prop.label, "string");
            assert.equal(typeof prop.sublabel, "string");
        }
    }
};

test("fixture: every frame is a wire string with a type", () => {
    assert.ok(fixture.scenarios.length >= 5, "the fixture must cover several scenarios");
    for (const scenario of fixture.scenarios) {
        assert.equal(typeof scenario.name, "string");
        assert.ok(scenario.frames.length > 0, `${scenario.name} has no frames`);
        for (const frame of wireFrames(scenario)) {
            assert.equal(typeof frame, "string", `${scenario.name}: frame is not a string`);
            const message = JSON.parse(frame);
            assert.equal(typeof message.type, "string", `${scenario.name}: frame without type`);
        }
    }
});

test("fixture: covers the frames the overlay depends on", () => {
    const types = new Set();
    const controls = new Set();
    for (const scenario of fixture.scenarios) {
        for (const frame of wireFrames(scenario)) {
            const message = JSON.parse(frame);
            types.add(message.type);
            if (message.type === "control") {
                controls.add(message.text);
            }
        }
    }
    const required = [
        "audio",
        "backend-synth-complete",
        "control",
        "force-new-message",
        "full-text",
        "interrupt-signal",
        "stage-update"
    ];
    for (const type of required) {
        assert.ok(types.has(type), `the fixture never sends '${type}'`);
    }
    for (const text of ["conversation-chain-start", "conversation-chain-end"]) {
        assert.ok(controls.has(text), `the fixture never sends control '${text}'`);
    }
});

for (const scenario of fixture.scenarios) {
    test(`wire: ${scenario.name}`, () => {
        const check = expectations[scenario.name];
        assert.ok(check, `no expectation for '${scenario.name}': add it to this file`);
        check(harness(), scenario);
    });
}

test("wire: unrelated frames are ignored, not fatal", () => {
    const h = harness();

    h.feed([
        JSON.stringify({ type: "heartbeat-ack" }),
        JSON.stringify({ type: "background-files", files: [] })
    ]);

    assert.equal(h.sent.length, 0);
    assert.equal(h.acks().length, 0);
});
