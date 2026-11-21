/* Adapter for the bundled web client. Motions begin with their matching speech. */
(() => {
  const NativeWebSocket = window.WebSocket;
  window.WebSocket = class extends NativeWebSocket {
    constructor(...args) {
      super(...args);
      const pending = [];
      let emotions = {};
      const celebrate = data => {
        const text = data.display_text?.text || '';
        const joy = emotions.joy;
        const explicit = /\[joy\]/i.test(text);
        const unique = joy != null && !Object.entries(emotions).some(
          ([key, value]) => key !== 'joy' && value === joy
        );
        if (explicit || (unique && data.actions?.expressions?.includes(joy))) {
          window.dispatchEvent(new Event('vtuber-joy'));
        }
      };
      const playLine = data => {
        play(data.actions?.motions);
        celebrate(data);
      };
      let lastMotion = -Infinity;
      const play = motions => {
        if (!motions?.length || performance.now() - lastMotion < 4000) return;
        const model = window.getLAppAdapter?.()?.getModel?.();
        const motion = motions[0];
        if (!model || typeof motion.group !== 'string' || !Number.isInteger(motion.index) || motion.index < 0) return;
        const setting = model._modelSetting;
        if (!setting || motion.index >= setting.getMotionCount(motion.group)) return;
        try { model.startMotion(motion.group, motion.index, 2); lastMotion = performance.now(); }
        catch (error) { console.warn('Live2D action failed', error); }
      };
      this.addEventListener('message', event => {
        try {
          const data = JSON.parse(event.data);
          if (window.vtuberBroadcastStopped && ['audio', 'full-text', 'tool_call_status'].includes(data.type)) {
            event.stopImmediatePropagation();
            return;
          }
          if (data.type === 'tool_call_status' && data.tool_name === 'local_stage') {
            event.stopImmediatePropagation();
            if (data.status === 'completed' && data.stage_action) {
              window.dispatchEvent(new CustomEvent('vtuber-stage-action', {detail: data.stage_action}));
            }
          }
          if (data.type === 'user-input-transcription') {
            window.dispatchEvent(new CustomEvent('vtuber-media-command', {detail: data.text}));
          }
          if (data.type === 'control') {
            window.dispatchEvent(new CustomEvent('vtuber-conversation', {detail: data.text}));
          }
          if (data.type === 'audio' && !data.forwarded) {
            if (!data.audio) playLine(data);
            else pending.push({display_text: data.display_text, actions: data.actions});
          }
          if (data.type === 'set-model-and-conf') emotions = data.model_info?.emotionMap || {};
          if (data.type === 'set-model-and-conf' || data.type === 'interrupt-signal') pending.length = 0;
        } catch (_) { /* Other messages retain their original handling. */ }
      });
      const nativeSend = this.send.bind(this);
      window.addEventListener('vtuber-emergency-stop', () => {
        pending.length = 0;
        if (this.readyState === NativeWebSocket.OPEN) nativeSend(JSON.stringify({type:'interrupt-signal', text:''}));
      });
      this.send = data => {
        try {
          const message = JSON.parse(data);
          if (message.type === 'ai-speak-signal') {
            if ([...document.querySelectorAll('audio, video')].some(media => !media.paused && !media.ended)) return;
            const language = document.documentElement.lang.toLowerCase().split('-')[0];
            if (language === 'zh' || language === 'en') {
              data = JSON.stringify({...message, language});
            }
          }
          if (message.type === 'text-input') {
            window.dispatchEvent(new CustomEvent('vtuber-media-command', {detail: message.text}));
          }
          if (message.type === 'interrupt-signal') pending.length = 0;
          if (message.type === 'text-input' || message.type === 'audio-play-start') {
            window.dispatchEvent(new CustomEvent('vtuber-dialogue', {
              detail: message.type === 'text-input' ? message.text : message.display_text?.text
            }));
          }
          if (message.type === 'audio-play-start') {
            const index = pending.findIndex(item => item.display_text?.text === message.display_text?.text);
            if (index >= 0) playLine(pending.splice(0, index + 1).at(-1));
          }
        } catch (_) { /* Never block the original transport. */ }
        return nativeSend(data);
      };
      this.addEventListener('close', () => { pending.length = 0; });
    }
  };
})();
