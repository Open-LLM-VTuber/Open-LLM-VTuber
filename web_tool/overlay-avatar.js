/**
 * Character layer for the Ruta B overlay: a still image avatar with life.
 *
 * No Live2D, no Cubism, no canvas: an ``<img>`` that breathes, blinks and
 * pulses while the voice plays. That keeps the overlay free of Live2D sample
 * models (LICENSE-Live2D.md) and works with any PNG/JPEG/GIF with alpha.
 *
 * Why it lives in its own layer instead of a normal prop: ``setProps()`` in
 * ``overlay.html`` clears every prop on each ``stage-update`` that carries
 * ``props``, so a tarot draw would delete the character. The avatar keeps its
 * own element and only changes when the payload (or the URL) says so.
 *
 * Kept apart from the DOM on purpose, like ``overlay-protocol.js``, so
 * ``node scripts/test_overlay_avatar.js`` can drive it with fake nodes and a
 * fake clock (no browser, no OBS, no timers left behind).
 *
 * States (CSS classes are added to ``root``):
 *   idle       -> breathing animation (CSS)
 *   is-talking -> talk image and/or pulse animation (CSS)
 * Blinking is done here because it swaps ``src``, which CSS cannot do.
 */
(function (root, factory) {
    if (typeof module === "object" && module.exports) {
        module.exports = factory();
    } else {
        root.OverlayAvatar = factory();
    }
}(typeof self !== "undefined" ? self : this, function () {
    "use strict";

    var DEFAULTS = {
        x: 0.27,
        y: 0.52,
        scale: 1,
        blinkMinMs: 3000,
        blinkMaxMs: 6500,
        blinkMs: 130
    };

    /** Coerce ``value`` to a finite number inside ``[low, high]``. */
    function number(value, fallback, low, high) {
        if (typeof value === "boolean") {
            return fallback;
        }
        var parsed = parseFloat(value);
        if (isNaN(parsed) || !isFinite(parsed)) {
            return fallback;
        }
        if (parsed < low) {
            return low;
        }
        if (parsed > high) {
            return high;
        }
        return parsed;
    }

    /**
     * Create the avatar controller.
     *
     * @param {Object} options
     * @param {Object} options.root       Outer element (positioned + ``hidden``).
     * @param {Object} options.image      ``<img>`` whose ``src`` is swapped.
     * @param {string} [options.openSrc]  Idle image; empty means "no avatar".
     * @param {string} [options.blinkSrc] Closed-eyes image (optional).
     * @param {string} [options.talkSrc]  Talking image (optional).
     * @param {number|string} [options.x] Normalised 0..1, default 0.27.
     * @param {number|string} [options.y] Normalised 0..1, default 0.52.
     * @param {number|string} [options.scale] 0.05..10, default 1.
     * @param {number|string} [options.blinkMinMs] Default 3000.
     * @param {number|string} [options.blinkMaxMs] Default 6500.
     * @param {number|string} [options.blinkMs]    Default 130.
     * @param {Function} [options.random]          Injectable for tests.
     * @param {Function} [options.setTimeout]      Injectable for tests.
     * @param {Function} [options.clearTimeout]    Injectable for tests.
     */
    function createAvatarController(options) {
        var opts = options || {};
        var rootEl = opts.root || null;
        var imageEl = opts.image || null;

        var openSrc = typeof opts.openSrc === "string" ? opts.openSrc : "";
        var blinkSrc = typeof opts.blinkSrc === "string" ? opts.blinkSrc : "";
        var talkSrc = typeof opts.talkSrc === "string" ? opts.talkSrc : "";

        var setTimer = opts.setTimeout ||
            (typeof setTimeout === "function" ? setTimeout : null);
        var clearTimer = opts.clearTimeout ||
            (typeof clearTimeout === "function" ? clearTimeout : null);
        var random = typeof opts.random === "function" ? opts.random : Math.random;

        var blinkMin = number(opts.blinkMinMs, DEFAULTS.blinkMinMs, 250, 600000);
        var blinkMax = number(opts.blinkMaxMs, DEFAULTS.blinkMaxMs, blinkMin, 600000);
        var blinkMs = number(opts.blinkMs, DEFAULTS.blinkMs, 20, 2000);

        var position = {
            x: number(opts.x, DEFAULTS.x, 0, 1),
            y: number(opts.y, DEFAULTS.y, 0, 1),
            scale: number(opts.scale, DEFAULTS.scale, 0.05, 10)
        };

        var running = false;
        var talking = false;
        var blinking = false;
        var blinkTimer = null;
        var openTimer = null;

        function hasNode(node) {
            return !!node && typeof node === "object";
        }

        function setTalkingClass(on) {
            if (!hasNode(rootEl) || !rootEl.classList) {
                return;
            }
            if (on) {
                rootEl.classList.add("is-talking");
            } else {
                rootEl.classList.remove("is-talking");
            }
        }

        function showVisible(on) {
            if (!hasNode(rootEl)) {
                return;
            }
            rootEl.hidden = !on;
            if (!rootEl.classList) {
                return;
            }
            if (on) {
                rootEl.classList.add("is-visible");
            } else {
                rootEl.classList.remove("is-visible");
            }
        }

        /** Blinking needs art and must not fight a dedicated talk frame. */
        function canBlink() {
            return !!blinkSrc && !!openSrc && !(talking && talkSrc);
        }

        /** Paint the frame that matches the current state. */
        function renderSource() {
            if (!hasNode(imageEl)) {
                return;
            }
            var url = openSrc;
            if (talking && talkSrc) {
                url = talkSrc;
            } else if (blinking && blinkSrc) {
                url = blinkSrc;
            }
            if (url) {
                imageEl.src = url;
            } else if (typeof imageEl.removeAttribute === "function") {
                imageEl.removeAttribute("src");
            } else {
                imageEl.src = "";
            }
        }

        /** Percent with at most two decimals (0.27 -> "27%", no float noise). */
        function percent(value) {
            return (Math.round(value * 10000) / 100) + "%";
        }

        function place() {
            if (!hasNode(rootEl) || !rootEl.style) {
                return;
            }
            rootEl.style.left = percent(position.x);
            rootEl.style.top = percent(position.y);
            rootEl.style.transform =
                "translate(-50%, -50%) scale(" + position.scale + ")";
        }

        function clearBlinkTimer() {
            if (blinkTimer !== null && clearTimer) {
                clearTimer(blinkTimer);
            }
            blinkTimer = null;
        }

        function clearOpenTimer() {
            if (openTimer !== null && clearTimer) {
                clearTimer(openTimer);
            }
            openTimer = null;
        }

        function scheduleBlink() {
            if (!running || blinkTimer !== null || !canBlink() || !setTimer) {
                return;
            }
            var spread = blinkMax - blinkMin;
            var delay = blinkMin + Math.round(random() * spread);
            blinkTimer = setTimer(function () {
                blinkTimer = null;
                doBlink();
            }, delay);
        }

        function doBlink() {
            if (!running || !canBlink()) {
                // Talking with a talk frame: idle until the turn ends.
                return;
            }
            blinking = true;
            renderSource();
            if (!setTimer) {
                blinking = false;
                return;
            }
            openTimer = setTimer(function () {
                openTimer = null;
                blinking = false;
                renderSource();
                scheduleBlink();
            }, blinkMs);
        }

        /** Replace the idle image (URL parameter or a ``stage-update``). */
        function setSource(url) {
            var next = typeof url === "string" ? url.trim() : "";
            if (next === openSrc) {
                return;
            }
            openSrc = next;
            blinking = false;
            clearBlinkTimer();
            clearOpenTimer();
            showVisible(!!openSrc);
            renderSource();
            place();
            if (running && openSrc) {
                scheduleBlink();
            }
        }

        /** Speak state: adds the CSS class and swaps to the talk frame. */
        function setTalking(on) {
            var next = on === true;
            if (next === talking) {
                return;
            }
            talking = next;
            setTalkingClass(talking);
            if (talking) {
                clearBlinkTimer();
            }
            renderSource();
            if (!talking) {
                scheduleBlink();
            }
        }

        /** Move/scale the layer (``x``/``y`` normalised 0..1). */
        function setPosition(next) {
            var source = next || {};
            position = {
                x: number(source.x, position.x, 0, 1),
                y: number(source.y, position.y, 0, 1),
                scale: number(source.scale, position.scale, 0.05, 10)
            };
            place();
        }

        function start() {
            running = true;
            showVisible(!!openSrc);
            place();
            renderSource();
            scheduleBlink();
        }

        function stop() {
            running = false;
            clearBlinkTimer();
            clearOpenTimer();
            blinking = false;
            talking = false;
            setTalkingClass(false);
            renderSource();
        }

        function getState() {
            return {
                visible: !!openSrc,
                talking: talking,
                blinking: blinking,
                src: hasNode(imageEl) ? imageEl.src : "",
                x: position.x,
                y: position.y,
                scale: position.scale,
                blinkPending: blinkTimer !== null
            };
        }

        // Initial paint so a URL-only avatar shows before `start()` runs.
        showVisible(!!openSrc);
        place();
        renderSource();

        return {
            setSource: setSource,
            setTalking: setTalking,
            setPosition: setPosition,
            start: start,
            stop: stop,
            getState: getState
        };
    }

    return {
        createAvatarController: createAvatarController
    };
}));
