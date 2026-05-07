let audioCtx: AudioContext | null = null

function getCtx(): AudioContext | null {
  try {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)()
    }
    return audioCtx
  } catch {
    return null
  }
}

export function playMoveSound() {
  const ctx = getCtx()
  if (!ctx) return

  try {
    const now = ctx.currentTime

    // ── Impact transient: sharp white-noise burst filtered through wood resonance ──
    const impactBufSize = Math.floor(ctx.sampleRate * 0.025)
    const impactBuf = ctx.createBuffer(1, impactBufSize, ctx.sampleRate)
    const impactData = impactBuf.getChannelData(0)
    for (let i = 0; i < impactBufSize; i++) {
      const env = Math.exp(-i / (impactBufSize * 0.18))
      impactData[i] = (Math.random() * 2 - 1) * env
    }

    const impact = ctx.createBufferSource()
    impact.buffer = impactBuf

    // Bandpass around wood's fundamental frequency (300 Hz)
    const bp1 = ctx.createBiquadFilter()
    bp1.type = 'bandpass'
    bp1.frequency.value = 300
    bp1.Q.value = 1.8

    const impactGain = ctx.createGain()
    impactGain.gain.setValueAtTime(0.9, now)
    impactGain.gain.exponentialRampToValueAtTime(0.001, now + 0.025)

    impact.connect(bp1)
    bp1.connect(impactGain)
    impactGain.connect(ctx.destination)
    impact.start(now)
    impact.stop(now + 0.025)

    // ── Body resonance: low woody thud that fades quickly ──
    const thud = ctx.createOscillator()
    thud.type = 'sine'
    thud.frequency.setValueAtTime(220, now)
    thud.frequency.exponentialRampToValueAtTime(90, now + 0.055)

    const thudGain = ctx.createGain()
    thudGain.gain.setValueAtTime(0.28, now)
    thudGain.gain.exponentialRampToValueAtTime(0.001, now + 0.055)

    thud.connect(thudGain)
    thudGain.connect(ctx.destination)
    thud.start(now)
    thud.stop(now + 0.06)

    // ── High click: the hard wooden surface "tap" ──
    const tapBufSize = Math.floor(ctx.sampleRate * 0.012)
    const tapBuf = ctx.createBuffer(1, tapBufSize, ctx.sampleRate)
    const tapData = tapBuf.getChannelData(0)
    for (let i = 0; i < tapBufSize; i++) {
      tapData[i] = (Math.random() * 2 - 1) * Math.exp(-i / (tapBufSize * 0.12))
    }

    const tap = ctx.createBufferSource()
    tap.buffer = tapBuf

    const hp = ctx.createBiquadFilter()
    hp.type = 'highpass'
    hp.frequency.value = 1800

    const tapGain = ctx.createGain()
    tapGain.gain.setValueAtTime(0.18, now)
    tapGain.gain.exponentialRampToValueAtTime(0.001, now + 0.012)

    tap.connect(hp)
    hp.connect(tapGain)
    tapGain.connect(ctx.destination)
    tap.start(now)
    tap.stop(now + 0.012)

  } catch {
    // Audio not supported — fail silently
  }
}
