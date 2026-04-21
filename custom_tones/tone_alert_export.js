window.AlertToneLab = {
  play: function(audioCtx, config){
    if(!audioCtx || !config) return;

    const presets = {
  "svr": {
    "mode": "pulse",
    "wave1": "sine",
    "wave2": "square",
    "f1": 350,
    "f2": 350,
    "amp": 0.2,
    "dur": 3.95,
    "gap": 1.3,
    "count": 3,
    "detune": 0,
    "attack": 0.02,
    "release": 0.05,
    "note": "TV-style long beeps."
  },
  "tor": {
    "mode": "pulse",
    "wave1": "triangle",
    "wave2": "sawtooth",
    "f1": 2000,
    "f2": 2000,
    "amp": 0.41,
    "dur": 3.55,
    "gap": 1.3,
    "count": 3,
    "detune": 5,
    "attack": 0.065,
    "release": 0.08,
    "note": "Broadcast-style sustained dual tone."
  },
  "tor-confirmed": {
    "mode": "pulse",
    "wave1": "square",
    "wave2": "square",
    "f1": 850,
    "f2": 960,
    "amp": 0.26,
    "dur": 5,
    "gap": 1.55,
    "count": 3,
    "detune": 16,
    "attack": 0.03,
    "release": 0.08,
    "note": "Sharper, faster repeated beeps."
  },
  "tor-emergency": {
    "mode": "pulse",
    "wave1": "square",
    "wave2": "square",
    "f1": 1397,
    "f2": 1400,
    "amp": 0.3,
    "dur": 8,
    "gap": 1.9,
    "count": 6,
    "detune": 15,
    "attack": 0.1,
    "release": 0.1,
    "note": "Layered aggressive beep train."
  }
};
    const now = audioCtx.currentTime;
    const sev = config.severity;

    let key = 'svr';
    if (sev === 'tor') key = 'tor';
    else if (sev === 'tor-confirmed') key = 'tor-confirmed';
    else if (sev === 'tor-emergency') key = 'tor-emergency';
    else if (sev === 'svr' || sev === 'svr-considerable' || sev === 'svr-destructive') key = 'svr';

    const s = presets[key];

    function playVoice(start, duration, f1, f2, wave1, wave2, amp, detune, attack, release){
      const gain = audioCtx.createGain();
      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.exponentialRampToValueAtTime(Math.max(0.0002, amp), start + attack);
      gain.gain.exponentialRampToValueAtTime(0.0001, Math.max(start + attack + 0.01, start + duration - release));
      gain.connect(audioCtx.destination);

      const osc1 = audioCtx.createOscillator();
      const osc2 = audioCtx.createOscillator();

      osc1.type = wave1;
      osc2.type = wave2;
      osc1.frequency.value = f1;
      osc2.frequency.value = f2;
      osc2.detune.value = detune;

      osc1.connect(gain);
      osc2.connect(gain);

      osc1.start(start);
      osc2.start(start);
      osc1.stop(start + duration + 0.02);
      osc2.stop(start + duration + 0.02);
    }

    if (s.mode === 'sustained') {
      playVoice(
        now,
        Number(s.dur),
        Number(s.f1),
        Number(s.f2),
        s.wave1,
        s.wave2,
        Number(s.amp),
        Number(s.detune),
        Number(s.attack),
        Number(s.release)
      );

      if (key === 'tor-emergency') {
        playVoice(
          now,
          Number(s.dur),
          Math.max(100, Number(s.f1) - 300),
          Math.max(100, Number(s.f2) - 600),
          'sawtooth',
          'sawtooth',
          Math.max(0.05, Number(s.amp) * 0.70),
          -10,
          Number(s.attack),
          Number(s.release)
        );
      }
      return;
    }

    for (let i = 0; i < Number(s.count || 1); i++) {
      let thisAmp = Number(s.amp);
      let thisF1 = Number(s.f1);
      let thisF2 = Number(s.f2);
      let thisWave1 = s.wave1;
      let thisWave2 = s.wave2;

      if (key === 'tor-emergency' && i % 2 === 1) {
        thisF1 = Math.max(100, Number(s.f1) - 300);
        thisF2 = Math.max(100, Number(s.f2) - 600);
        thisWave1 = 'sawtooth';
        thisWave2 = 'sawtooth';
        thisAmp = Math.max(0.05, Number(s.amp) * 0.75);
      }

      playVoice(
        now + i * Number(s.gap || 0.7),
        Number(s.dur),
        thisF1,
        thisF2,
        thisWave1,
        thisWave2,
        thisAmp,
        Number(s.detune),
        Number(s.attack),
        Number(s.release)
      );
    }
  }
};
