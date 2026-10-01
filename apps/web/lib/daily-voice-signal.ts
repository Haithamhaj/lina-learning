import type { VoiceSignalMonitor } from "./daily-voice-recorder";

/** A conservative near-silence check. Only amplitude counts are retained, never samples. */
export function monitorMicrophoneSignal(stream: MediaStream): VoiceSignalMonitor | null {
  if (typeof AudioContext === "undefined") return null;
  let context: AudioContext | null = null;
  try {
    context = new AudioContext();
    const source = context.createMediaStreamSource(stream);
    const analyser = context.createAnalyser();
    analyser.fftSize = 2048;
    const silentOutput = context.createGain();
    silentOutput.gain.value = 0;
    source.connect(analyser);
    analyser.connect(silentOutput);
    silentOutput.connect(context.destination);

    const samples = new Float32Array(analyser.fftSize);
    let observedFrames = 0;
    let signalFrames = 0;
    const sample = () => {
      if (context?.state !== "running") return;
      analyser.getFloatTimeDomainData(samples);
      let power = 0;
      for (let index = 0; index < samples.length; index += 1) power += samples[index] * samples[index];
      observedFrames += 1;
      if (Math.sqrt(power / samples.length) >= 0.002) signalFrames += 1;
    };
    if (context.state === "suspended") void context.resume().catch(() => {});
    const timer = window.setInterval(sample, 100);
    return {
      hasNonSilentSignal: () => {
        sample();
        // Unobservable or very short recordings still go to the provider.
        return observedFrames < 3 ? null : signalFrames > 0;
      },
      stop: () => {
        window.clearInterval(timer);
        samples.fill(0);
        source.disconnect();
        analyser.disconnect();
        silentOutput.disconnect();
        void context?.close().catch(() => {});
      },
    };
  } catch {
    if (context) void context.close().catch(() => {});
    return null;
  }
}
