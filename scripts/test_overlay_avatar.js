/**
 * Unit tests for the overlay character layer (`web_tool/overlay-avatar.js`).
 *
 * The avatar replaced the Live2D model in the OBS overlay, so its three states
 * (idle / blink / talking) are now part of the live look. These tests drive the
 * real controller with fake nodes and a fake clock, so a wrong `src`, a timer
 * that never fires or a blink that fights the talking frame is caught without
 * opening OBS.
 *
 *     node scripts/test_overlay_avatar.js
 */

"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { createAvatarController } = require("../web_tool/overlay-avatar.js");

/** Minimal element: `hidden`, `src`, inline style and a classList Set. */
function fakeNode(withStyle) {
    const classes = new Set();
    return {
        hidden: false,
        src: "",
        style: withStyle === false ? undefined : {},
        classList: {
            add(name) {
                classes.add(name);
            },
            remove(name) {
                classes.delete(name);
            },
            contains(name) {
                return classes.has(name);
            }
        },
        removeAttribute(name) {
            if (name === "src") {
                this.src = "";
            }
        },
        classes
    };
}

/** Deterministic timer queue: `runNext()` executes the oldest pending timer. */
function fakeClock() {
    let nextId = 0;
    const timers = new Map();
    return {
        setTimeout(fn, ms) {
            const id = ++nextId;
            timers.set(id, { fn, ms });
            return id;
        },
        clearTimeout(id) {
            timers.delete(id);
        },
        pending() {
            return timers.size;
        },
        runNext() {
            const entry = timers.entries().next().value;
            if (!entry) {
                throw new Error("no pending timer");
            }
            timers.delete(entry[0]);
            entry[1].fn();
            return entry[1].ms;
        }
    };
}

function harness(options) {
    const opts = options || {};
    const clock = opts.clock || fakeClock();
    const root = fakeNode();
    const image = fakeNode(false);
    const avatar = createAvatarController({
        root,
        image,
        openSrc: opts.openSrc === undefined ? "/avatars/a.png" : opts.openSrc,
        blinkSrc: opts.blinkSrc || "",
        talkSrc: opts.talkSrc || "",
        x: opts.x,
        y: opts.y,
        scale: opts.scale,
        blinkMinMs: opts.blinkMinMs,
        blinkMaxMs: opts.blinkMaxMs,
        blinkMs: opts.blinkMs,
        random: opts.random || (() => 0),
        setTimeout: clock.setTimeout,
        clearTimeout: clock.clearTimeout
    });
    return { avatar, root, image, clock };
}

test("is hidden without art and visible once a source is set", () => {
    const empty = harness({ openSrc: "" });
    assert.equal(empty.root.hidden, true);
    assert.equal(empty.root.classList.contains("is-visible"), false);
    assert.equal(empty.image.src, "");

    const dressed = harness();
    assert.equal(dressed.root.hidden, false);
    assert.equal(dressed.root.classList.contains("is-visible"), true);
    assert.equal(dressed.image.src, "/avatars/a.png");
});

test("places the layer with normalised coordinates", () => {
    const { root } = harness();
    assert.equal(root.style.left, "27%");
    assert.equal(root.style.top, "52%");
    assert.equal(root.style.transform, "translate(-50%, -50%) scale(1)");
});

test("clamps x, y and scale to their ranges", () => {
    const { root } = harness({ x: 2, y: -1, scale: 0 });
    assert.equal(root.style.left, "100%");
    assert.equal(root.style.top, "0%");
    assert.equal(root.style.transform, "translate(-50%, -50%) scale(0.05)");
});

test("talking swaps to the talk frame and back", () => {
    const { avatar, image, root } = harness({
        talkSrc: "/avatars/talk.png"
    });
    avatar.setTalking(true);
    assert.equal(image.src, "/avatars/talk.png");
    assert.equal(root.classList.contains("is-talking"), true);
    assert.equal(avatar.getState().talking, true);

    avatar.setTalking(false);
    assert.equal(image.src, "/avatars/a.png");
    assert.equal(root.classList.contains("is-talking"), false);
});

test("talking without a talk frame only adds the CSS class", () => {
    const { avatar, image, root } = harness();
    avatar.setTalking(true);
    assert.equal(image.src, "/avatars/a.png");
    assert.equal(root.classList.contains("is-talking"), true);
});

test("blinks with the closed-eyes frame and restores it", () => {
    const { avatar, image, clock } = harness({
        blinkSrc: "/avatars/blink.png",
        blinkMinMs: 1000,
        blinkMaxMs: 1000,
        blinkMs: 120
    });
    avatar.start();
    assert.equal(clock.pending(), 1);

    assert.equal(clock.runNext(), 1000, "first blink delay");
    assert.equal(image.src, "/avatars/blink.png");
    assert.equal(avatar.getState().blinking, true);

    assert.equal(clock.runNext(), 120, "time the eyes stay closed");
    assert.equal(image.src, "/avatars/a.png");
    assert.equal(avatar.getState().blinking, false);
});

test("does not blink without a blink frame", () => {
    const { avatar, clock } = harness();
    avatar.start();
    assert.equal(clock.pending(), 0);
});

test("does not blink over a dedicated talking frame", () => {
    const { avatar, image, clock } = harness({
        blinkSrc: "/avatars/blink.png",
        talkSrc: "/avatars/talk.png",
        blinkMinMs: 1000,
        blinkMaxMs: 1000
    });
    avatar.start();
    assert.equal(clock.pending(), 1);

    avatar.setTalking(true);
    assert.equal(clock.pending(), 0);
    assert.equal(image.src, "/avatars/talk.png");

    avatar.setTalking(false);
    assert.equal(clock.pending(), 1, "blinking resumes after the turn");
    clock.runNext();
    assert.equal(image.src, "/avatars/blink.png");
});

test("setPosition moves the layer without touching the frame", () => {
    const { avatar, image, root } = harness();
    avatar.setPosition({ x: 0.5, y: 0.8, scale: 1.2 });
    assert.equal(root.style.left, "50%");
    assert.equal(root.style.top, "80%");
    assert.equal(root.style.transform, "translate(-50%, -50%) scale(1.2)");
    assert.equal(image.src, "/avatars/a.png");
});

test("a new source replaces the frame and can hide the layer", () => {
    const { avatar, image, root } = harness();
    avatar.setSource("  /avatars/astrologo.png  ");
    assert.equal(image.src, "/avatars/astrologo.png");
    assert.equal(root.hidden, false);

    avatar.setSource("   ");
    assert.equal(root.hidden, true);
    assert.equal(root.classList.contains("is-visible"), false);
});

test("stop clears the timers and leaves the idle frame", () => {
    const { avatar, image, clock, root } = harness({
        blinkSrc: "/avatars/blink.png",
        talkSrc: "/avatars/talk.png",
        blinkMinMs: 1000,
        blinkMaxMs: 1000
    });
    avatar.start();
    avatar.setTalking(true);
    avatar.stop();

    assert.equal(clock.pending(), 0);
    assert.equal(image.src, "/avatars/a.png");
    assert.equal(root.classList.contains("is-talking"), false);
});

