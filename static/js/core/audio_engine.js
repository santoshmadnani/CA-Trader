// ============================================================================
// CA TRADER NATIVE WEB AUDIO SYNTHESIZER (Item: Audio & Voice Alerts Engine)
// Synthesizes institutional sound cues using Web Audio API (zero audio files)
// ============================================================================

(function(){
  let audioCtx = null;
  let isMuted = localStorage.getItem('ca_audio_enabled') === 'false';

  function getAudioContext(){
    if(!audioCtx){
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if(AudioCtx) audioCtx = new AudioCtx();
    }
    if(audioCtx && audioCtx.state === 'suspended'){
      audioCtx.resume().catch(()=>{});
    }
    return audioCtx;
  }

  // 1. Target Hit Chime (Crisp, pleasant harmonic chord)
  function playTargetChime(){
    if(isMuted) return;
    try {
      const ctx = getAudioContext();
      if(!ctx) return;
      const now = ctx.currentTime;
      [880, 1108.73, 1318.51].forEach((freq, i) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, now + i * 0.08);
        gain.gain.setValueAtTime(0.18, now + i * 0.08);
        gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.08 + 0.6);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now + i * 0.08);
        osc.stop(now + i * 0.08 + 0.65);
      });
    } catch(_) {}
  }

  // 2. Max Loss / Emergency Warning (Urgent double pulse beep)
  function playWarningAlarm(){
    if(isMuted) return;
    try {
      const ctx = getAudioContext();
      if(!ctx) return;
      const now = ctx.currentTime;
      [0, 0.16].forEach(delay => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'square';
        osc.frequency.setValueAtTime(370, now + delay);
        gain.gain.setValueAtTime(0.15, now + delay);
        gain.gain.exponentialRampToValueAtTime(0.001, now + delay + 0.12);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now + delay);
        osc.stop(now + delay + 0.13);
      });
    } catch(_) {}
  }

  // 3. CA AI High-Conviction Breakout Tone (Ascending triad ping)
  function playBreakoutTone(){
    if(isMuted) return;
    try {
      const ctx = getAudioContext();
      if(!ctx) return;
      const now = ctx.currentTime;
      [523.25, 659.25, 783.99].forEach((freq, i) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, now + i * 0.07);
        gain.gain.setValueAtTime(0.16, now + i * 0.07);
        gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.07 + 0.45);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now + i * 0.07);
        osc.stop(now + i * 0.07 + 0.5);
      });
    } catch(_) {}
  }

  // 4. Quick Order Placed Ding
  function playOrderPlacedTone(){
    if(isMuted) return;
    try {
      const ctx = getAudioContext();
      if(!ctx) return;
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(987.77, now);
      gain.gain.setValueAtTime(0.14, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.36);
    } catch(_) {}
  }

  function toggleMute(){
    isMuted = !isMuted;
    localStorage.setItem('ca_audio_enabled', isMuted ? 'false' : 'true');
    updateSoundButtonUI();
    if(!isMuted) playOrderPlacedTone();
    return !isMuted;
  }

  function updateSoundButtonUI(){
    const btn = document.getElementById('soundToggleBtn');
    if(btn){
      btn.innerHTML = isMuted ? '🔇' : '🔊';
      btn.title = isMuted ? 'Audio alerts muted (Click to enable sound)' : 'Audio alerts active (Click to mute)';
      btn.classList.toggle('muted', isMuted);
    }
  }

  window.caAudio = {
    playTargetChime,
    playWarningAlarm,
    playBreakoutTone,
    playOrderPlacedTone,
    toggleMute,
    isMuted: () => isMuted
  };

  // Wire UI button when ready
  document.addEventListener('DOMContentLoaded', () => {
    updateSoundButtonUI();
    document.getElementById('soundToggleBtn')?.addEventListener('click', () => {
      toggleMute();
    });
  });

  // Unlock AudioContext on first user interaction anywhere
  const unlockEvents = ['click', 'keydown', 'touchstart'];
  function unlockAudio(){
    getAudioContext();
    unlockEvents.forEach(e => document.removeEventListener(e, unlockAudio));
  }
  unlockEvents.forEach(e => document.addEventListener(e, unlockAudio, { passive: true }));
})();

