// ============================================================
// useSpeech – Web Speech API wrapper
// Speaks predicted sign words aloud so teachers/peers can hear
// ============================================================

import { useCallback, useRef } from 'react';

export function useSpeech() {
  const synth    = useRef(window.speechSynthesis);
  const supported = 'speechSynthesis' in window;

  const speak = useCallback((text) => {
    if (!supported || !text) return;
    // Cancel any ongoing utterance
    synth.current.cancel();
    const utt  = new SpeechSynthesisUtterance(text);
    utt.rate   = 0.95;
    utt.pitch  = 1;
    utt.volume = 1;
    // Use first English voice available
    const voices = synth.current.getVoices();
    const eng    = voices.find((v) => v.lang.startsWith('en'));
    if (eng) utt.voice = eng;
    synth.current.speak(utt);
  }, [supported]);

  const stop = useCallback(() => {
    synth.current.cancel();
  }, []);

  return { speak, stop, supported };
}