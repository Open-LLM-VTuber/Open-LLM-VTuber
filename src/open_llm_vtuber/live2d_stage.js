/* Broadcast stop control and celebration effects. Media lives in React sidebar. */
(() => {
  document.addEventListener('DOMContentLoaded', () => {
    fetch('/api/broadcast/status').then(r => r.json()).then(state => {
      if (!state.enabled) return;
      window.vtuberLiveMode = true;
      const control = document.createElement('button');
      control.textContent = 'AI 虚拟主播 · 紧急停止';
      control.style.cssText = 'position:fixed;top:12px;right:12px;z-index:99999;background:#991b1b;color:white;padding:10px 16px;border:0;border-radius:6px;cursor:pointer';
      const stop = () => {
        window.vtuberBroadcastStopped = true;
        document.querySelectorAll('audio,video').forEach(element => element.pause());
        window.dispatchEvent(new Event('vtuber-emergency-stop'));
        control.textContent = '直播输出已停止 · 刷新前请检查内容';
      };
      control.onclick = stop;
      document.body.append(control);
      if (state.stopped) stop();
      setInterval(() => fetch('/api/broadcast/status').then(r=>r.json()).then(s=>{if(s.stopped) stop();}).catch(()=>{}), 1000);
    }).catch(()=>{});
  });
})();

/* Celebration layer. It never captures clicks or changes Live2D state. */
(() => {
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const colors = ['#ff759f', '#ffd166', '#8af3d3', '#bda4ff', '#86ceff'];
  let lastBurst = -Infinity;

  window.addEventListener('vtuber-joy', () => {
    const now = performance.now();
    if (reducedMotion.matches || now - lastBurst < 5500) return;
    const stage = document.getElementById('live2d') || document.querySelector('canvas');
    if (!stage) return;
    const rect = stage.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    lastBurst = now;
    const layer = document.createElement('div');
    layer.setAttribute('aria-hidden', 'true');
    layer.style.cssText = 'position:fixed;inset:0;overflow:hidden;pointer-events:none;z-index:1200';
    document.body.append(layer);

    for (let i = 0; i < 32; i++) {
      const particle = document.createElement('span');
      const star = i % 5 === 0;
      const smile = i % 11 === 0;
      const angle = Math.PI + Math.random() * Math.PI;
      const distance = 80 + Math.random() * Math.min(rect.width * .36, 240);
      const x = Math.round(Math.cos(angle) * distance);
      const y = Math.round(Math.sin(angle) * distance);
      const color = colors[i % colors.length];
      particle.style.cssText = `position:absolute;left:${rect.left + rect.width * .5}px;top:${rect.top + rect.height * .48}px;color:${color};`;
      if (star || smile) {
        particle.textContent = smile ? '☺' : '✦';
        particle.style.fontSize = smile ? '29px' : '23px';
        particle.style.textShadow = '0 0 8px currentColor';
      } else {
        particle.style.cssText += `width:7px;height:13px;border-radius:2px;background:${color}`;
      }
      layer.append(particle);
      particle.animate([
        { transform: 'translate(0,0) scale(.2)', opacity: 0 },
        { transform: `translate(${x}px,${y}px) rotate(${i * 23}deg)`, opacity: 1, offset: .32 },
        { transform: `translate(${x * 1.35}px,${y + 190}px) rotate(${i * 47}deg)`, opacity: 0 },
      ], { duration: 1450 + Math.random() * 350, delay: Math.random() * 130, fill: 'both' });
    }
    setTimeout(() => layer.remove(), 2000);
  });
})();
