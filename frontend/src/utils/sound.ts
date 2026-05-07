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

    // Random variation per tap — prevents the robotic identical-sound effect
    const pitchVar = 0.88 + Math.random() * 0.24   // ×0.88–1.12
    const velVar   = 0.82 + Math.random() * 0.18   // ×0.82–1.00

    // ── 1. Initial crack: very short broadband burst (the surface contact) ──
    const crackSize = Math.floor(ctx.sampleRate * 0.005)
    const crackBuf  = ctx.createBuffer(1, crackSize, ctx.sampleRate)
    const crackData = crackBuf.getChannelData(0)
    for (let i = 0; i < crackSize; i++) {
      crackData[i] = (Math.random() * 2 - 1) * Math.exp(-i / (crackSize * 0.28))
    }
    const crack     = ctx.createBufferSource()
    crack.buffer    = crackBuf
    const crackGain = ctx.createGain()
    crackGain.gain.setValueAtTime(velVar * 0.55, now)
    crackGain.gain.exponentialRampToValueAtTime(0.001, now + 0.005)
    crack.connect(crackGain)
    crackGain.connect(ctx.destination)
    crack.start(now)
    crack.stop(now + 0.006)

    // ── 2. Body resonance: two detuned oscillators (inharmonic = natural wood) ──
    //    Small delay so crack arrives first, then the thud follows — like real physics
    const t0       = now + 0.002
    const baseFreq = 170 * pitchVar

    const body1 = ctx.createOscillator()
    body1.type  = 'sine'
    body1.frequency.setValueAtTime(baseFreq, t0)
    body1.frequency.exponentialRampToValueAtTime(baseFreq * 0.52, t0 + 0.085)

    // Inharmonic partial — slightly detuned ratio makes it sound like wood, not a synth
    const body2 = ctx.createOscillator()
    body2.type  = 'sine'
    body2.frequency.setValueAtTime(baseFreq * 2.73, t0)
    body2.frequency.exponentialRampToValueAtTime(baseFreq * 1.18, t0 + 0.055)

    const bodyGain = ctx.createGain()
    bodyGain.gain.setValueAtTime(0.001, t0)
    bodyGain.gain.linearRampToValueAtTime(velVar * 0.30, t0 + 0.004)  // quick attack
    bodyGain.gain.exponentialRampToValueAtTime(0.001, t0 + 0.095)

    const body2Gain = ctx.createGain()
    body2Gain.gain.setValueAtTime(velVar * 0.10, t0)
    body2Gain.gain.exponentialRampToValueAtTime(0.001, t0 + 0.050)

    body1.connect(bodyGain);  bodyGain.connect(ctx.destination)
    body2.connect(body2Gain); body2Gain.connect(ctx.destination)
    body1.start(t0); body1.stop(t0 + 0.10)
    body2.start(t0); body2.stop(t0 + 0.06)

    // ── 3. Surface texture: pink-ish noise (correlated samples = smoother than white) ──
    const texSize = Math.floor(ctx.sampleRate * 0.022)
    const texBuf  = ctx.createBuffer(1, texSize, ctx.sampleRate)
    const texData = texBuf.getChannelData(0)
    let prev = 0
    for (let i = 0; i < texSize; i++) {
      // Simple first-order pink noise approximation
      prev       = (Math.random() * 2 - 1) * 0.55 + prev * 0.45
      texData[i] = prev * Math.exp(-i / (texSize * 0.22))
    }
    const tex = ctx.createBufferSource()
    tex.buffer = texBuf

    const bp    = ctx.createBiquadFilter()
    bp.type     = 'bandpass'
    bp.frequency.value = 550 * pitchVar
    bp.Q.value  = 1.4

    const texGain = ctx.createGain()
    texGain.gain.setValueAtTime(velVar * 0.48, now)
    texGain.gain.exponentialRampToValueAtTime(0.001, now + 0.022)

    tex.connect(bp); bp.connect(texGain); texGain.connect(ctx.destination)
    tex.start(now)
    tex.stop(now + 0.024)

  } catch {
    // Audio not supported — fail silently
  }
}
