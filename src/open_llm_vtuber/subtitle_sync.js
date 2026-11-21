/* Follow the actual speech player's clock; never run a separate wall-clock timer. */
(() => {
  const split = text => {
    const parts = String(text).replace(/\[[a-z_]+\]/gi, '').match(/[^。！？!?；;，,\n]+[。！？!?；;，,]?/g) || [];
    const cues = [];
    for (const part of parts) {
      const words = part.trim().split(/\s+/);
      let line = '';
      for (const word of words) {
        for (const char of word + ' ') {
          if (Array.from(line).length >= 32) { cues.push(line.trim()); line = ''; }
          line += char;
        }
      }
      if (line.trim()) cues.push(line.trim());
    }
    return cues;
  };
  window.vtuberSubtitleSegments = split;
  window.bindVtuberSubtitles = (audio, text, update) => {
    const cues = split(text);
    const weights = cues.map(cue => Math.max(1, cue.replace(/\s/g, '').length));
    const total = weights.reduce((a, b) => a + b, 0);
    let last = -1;
    const render = () => {
      if (!cues.length || !Number.isFinite(audio.duration) || audio.duration <= 0) return;
      const position = audio.currentTime / audio.duration * total;
      let end = 0, index = cues.length - 1;
      for (let i = 0; i < cues.length; i++) {
        end += weights[i];
        if (position < end) { index = i; break; }
      }
      if (index !== last) { last = index; update(cues[index]); }
    };
    for (const event of ['playing', 'timeupdate', 'seeked', 'ratechange']) audio.addEventListener(event, render);
    audio.addEventListener('ended', () => update(''));
    audio.addEventListener('emptied', () => update(''));
    audio.addEventListener('error', () => update(''));
    // Pause retains the current cue; seek and resume use currentTime.
  };
})();
