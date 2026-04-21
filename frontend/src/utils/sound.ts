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

    // Noise burst — the "clac" of the piece hitting the board
    const bufSize = Math.floor(ctx.sampleRate * 0.08)
    const buf = ctx.createBuffer(1, bufSize, ctx.sampleRate)
    const data = buf.getChannelData(0)
    for (let i = 0; i < bufSize; i++) data[i] = Math.random() * 2 - 1

    const noise = ctx.createBufferSource()
    noise.buffer = buf

    const bandpass = ctx.createBiquadFilter()
    bandpass.type = 'bandpass'
    bandpass.frequency.value = 900
    bandpass.Q.value = 2.5

    const noiseGain = ctx.createGain()
    noiseGain.gain.setValueAtTime(0.45, now)
    noiseGain.gain.exponentialRampToValueAtTime(0.001, now + 0.07)

    noise.connect(bandpass)
    bandpass.connect(noiseGain)
    noiseGain.connect(ctx.destination)
    noise.start(now)
    noise.stop(now + 0.08)

    // Low thud — body resonance of the wooden piece
    const osc = ctx.createOscillator()
    osc.type = 'sine'
    osc.frequency.setValueAtTime(160, now)
    osc.frequency.exponentialRampToValueAtTime(55, now + 0.07)

    const oscGain = ctx.createGain()
    oscGain.gain.setValueAtTime(0.35, now)
    oscGain.gain.exponentialRampToValueAtTime(0.001, now + 0.07)

    osc.connect(oscGain)
    oscGain.connect(ctx.destination)
    osc.start(now)
    osc.stop(now + 0.08)
  } catch {
    // Audio not supported — fail silently
  }
}
