// ============================================================
// AssistiveVoiceContext – global voice commands + TTS
// ============================================================

import { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const AssistiveVoiceContext = createContext(null);

export function AssistiveVoiceProvider({ children }) {
  const [lastExtractedText, setLastExtractedText] = useState('');
  const [isSpeaking,        setIsSpeaking]        = useState(false);
  const [voiceActive,       setVoiceActive]       = useState(false);

  const synthRef           = useRef(window.speechSynthesis);
  const lastExtractedRef   = useRef(''); // ref so onresult closure is always fresh
  const locationRef        = useRef('/');

  const navigate = useNavigate();
  const location = useLocation();

  // keep refs in sync
  useEffect(() => { lastExtractedRef.current = lastExtractedText; }, [lastExtractedText]);
  useEffect(() => { locationRef.current = location.pathname; },     [location.pathname]);

  // ── TTS — stable reference, never recreated ──────────────
  const speak = useCallback((text) => {
    if (!text) return;
    synthRef.current.cancel();
    const utt = new SpeechSynthesisUtterance(text);
    utt.rate  = 0.92;
    utt.pitch = 1;
    // voices may not be loaded yet on first call; that's fine, browser picks default
    const voices = synthRef.current.getVoices();
    const eng    = voices.find(v => v.lang.startsWith('en'));
    if (eng) utt.voice = eng;
    utt.onstart = () => setIsSpeaking(true);
    utt.onend   = () => setIsSpeaking(false);
    utt.onerror = () => setIsSpeaking(false);
    synthRef.current.speak(utt);
  }, []); // no deps → truly stable

  const stopSpeaking = useCallback(() => {
    synthRef.current.cancel();
    setIsSpeaking(false);
  }, []);

  // ── Voice recognition — started once, never restarted by deps ──
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const rec = new SpeechRecognition();
    rec.continuous     = true;
    rec.interimResults = false;
    rec.lang           = 'en-US';

    rec.onresult = (event) => {
      const transcript = event.results[event.results.length - 1][0].transcript
        .trim()
        .toLowerCase();

      console.log('[AssistiveVoice] heard:', transcript);

      const goAssistive = () => {
        if (locationRef.current !== '/assistive') navigate('/assistive');
      };

      if (transcript.includes('start reading')) {
        goAssistive();
        setTimeout(() => window.dispatchEvent(new CustomEvent('assistive-voice-cmd', { detail: 'start_reading' })), 600);

      } else if (transcript.includes('capture image') || transcript.includes('capture')) {
        goAssistive();
        setTimeout(() => window.dispatchEvent(new CustomEvent('assistive-voice-cmd', { detail: 'capture' })), 600);

      } else if (transcript.includes('pause') || transcript.includes('stop reading')) {
        synthRef.current.cancel();
        setIsSpeaking(false);
        window.dispatchEvent(new CustomEvent('assistive-voice-cmd', { detail: 'pause' }));

      } else if (transcript.includes('repeat')) {
        const text = lastExtractedRef.current;
        if (text) speak(text);
        else speak('Nothing to repeat yet.');
        window.dispatchEvent(new CustomEvent('assistive-voice-cmd', { detail: 'repeat' }));
      }
    };

    rec.onerror = (e) => {
      if (e.error === 'no-speech' || e.error === 'aborted') return;
      console.warn('[AssistiveVoice] error:', e.error);
    };

    // keep it alive
    rec.onend = () => {
      try { rec.start(); } catch (_) {}
    };

    rec.start();
    setVoiceActive(true);

    return () => {
      rec.onend = null; // stop the auto-restart before cleanup
      try { rec.stop(); } catch (_) {}
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // mount once — reads fresh data via refs

  return (
    <AssistiveVoiceContext.Provider
      value={{
        speak,
        stopSpeaking,
        isSpeaking,
        voiceActive,
        lastExtractedText,
        setLastExtractedText,
      }}
    >
      {children}
    </AssistiveVoiceContext.Provider>
  );
}

export function useAssistiveVoice() {
  const ctx = useContext(AssistiveVoiceContext);
  if (!ctx) throw new Error('useAssistiveVoice must be used inside AssistiveVoiceProvider');
  return ctx;
}
