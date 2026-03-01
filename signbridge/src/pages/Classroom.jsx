// ============================================================
// Classroom Page – Classroom Accessibility Mode
//
// Two simultaneous channels:
//  1. SIGN → TEXT : webcam frames sent to /predict every 800ms
//  2. SPEECH → TEXT : Web Speech API (SpeechRecognition) converts
//                     teacher's speech to live captions for students
//
// Together these create a fully bidirectional classroom environment.
// ============================================================

import { useState, useEffect, useRef, useCallback } from 'react';
import { useCamera } from '../hooks/useCamera';
import { useSpeech } from '../hooks/useSpeech';
import { predictSign } from '../services/api';
import CameraFeed from '../components/CameraFeed';
import './Classroom.css';

const PREDICT_INTERVAL_MS = 1000;

export default function Classroom() {
  // Camera / sign detection
  const { videoRef, canvasRef, active, error: camError, startCamera, stopCamera, captureFrame } =
    useCamera();

  const { speak } = useSpeech();

  const [sessionActive,    setSessionActive]    = useState(false);
  const [signPrediction,   setSignPrediction]   = useState('');
  const [signTranscript,   setSignTranscript]   = useState([]);

  // Speech recognition (teacher → captions for students)
  const [speechCaption,    setSpeechCaption]    = useState('');
  const [speechHistory,    setSpeechHistory]    = useState([]);
  const [speechActive,     setSpeechActive]     = useState(false);
  const [speechSupported,  setSpeechSupported]  = useState(false);

  const intervalRef    = useRef(null);
  const lastSignRef    = useRef('');
  const recognitionRef = useRef(null);

  // ── Speech Recognition setup ─────────────────────────────
  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) { setSpeechSupported(false); return; }

    setSpeechSupported(true);
    const rec = new SpeechRecognition();
    rec.continuous     = true;
    rec.interimResults = true;
    rec.lang           = 'en-US';

    rec.onresult = (event) => {
      let interim = '';
      let final   = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) final += t;
        else interim += t;
      }
      setSpeechCaption(interim || final);
      if (final.trim()) {
        setSpeechHistory((prev) => [
          ...prev,
          { id: Date.now(), text: final.trim() },
        ]);
        setSpeechCaption('');
      }
    };

    rec.onerror = (e) => console.warn('SpeechRecognition error:', e.error);
    recognitionRef.current = rec;

    return () => { rec.stop(); };
  }, []);

  // ── Sign prediction loop ─────────────────────────────────
  const runSignPrediction = useCallback(async () => {
    if (!active) return;
    try {
      const blob   = await captureFrame();
      if (!blob) return;
      const result = await predictSign(blob);
      const word   = result.prediction;

      if (word && word !== 'No hand detected') {
        setSignPrediction(word);
        if (word !== lastSignRef.current) {
          lastSignRef.current = word;
          setSignTranscript((prev) => [...prev, { id: Date.now(), word }]);
          speak(word); // auto-speak so teacher can hear student's sign
        }
      } else {
        setSignPrediction('');
      }
    } catch (_) {}
  }, [active, captureFrame, speak]);

  // ── Start session ────────────────────────────────────────
  const startSession = useCallback(async () => {
    await startCamera();
    setSessionActive(true);
    if (speechSupported && recognitionRef.current) {
      recognitionRef.current.start();
      setSpeechActive(true);
    }
  }, [startCamera, speechSupported]);

  // ── Stop session ─────────────────────────────────────────
  const stopSession = useCallback(() => {
    clearInterval(intervalRef.current);
    stopCamera();
    if (recognitionRef.current && speechActive) {
      recognitionRef.current.stop();
      setSpeechActive(false);
    }
    setSessionActive(false);
    setSignPrediction('');
  }, [stopCamera, speechActive]);

  // ── Prediction interval ───────────────────────────────────
  useEffect(() => {
    if (active && sessionActive) {
      intervalRef.current = setInterval(runSignPrediction, PREDICT_INTERVAL_MS);
    }
    return () => clearInterval(intervalRef.current);
  }, [active, sessionActive, runSignPrediction]);

  const clearAll = () => {
    setSignTranscript([]);
    setSpeechHistory([]);
    lastSignRef.current = '';
    setSignPrediction('');
    setSpeechCaption('');
  };

  return (
    <div className="classroom-page">
      {/* Header */}
      <div className="classroom-page__header fade-up">
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
          <h1 className="classroom-page__title">Classroom Mode</h1>
          {sessionActive && <span className="badge badge-live">SESSION LIVE</span>}
        </div>
        <p className="classroom-page__sub">
          Bidirectional classroom accessibility — student signs are detected and spoken
          aloud; teacher speech is captioned in real time.
        </p>
      </div>

      {camError && (
        <div className="classroom-page__error fade-in">⚠ {camError}</div>
      )}

      {/* Session controls */}
      <div className="classroom-page__controls fade-up" style={{ animationDelay: '0.1s' }}>
        {!sessionActive ? (
          <button className="btn btn-primary" onClick={startSession}>
            ◉ Start Classroom Session
          </button>
        ) : (
          <button className="btn btn-danger" onClick={stopSession}>
            ■ End Session
          </button>
        )}
        {(signTranscript.length > 0 || speechHistory.length > 0) && (
          <button className="btn btn-ghost" onClick={clearAll}>
            Clear All
          </button>
        )}
        {!speechSupported && (
          <span className="classroom-page__no-speech">
            ⚠ Speech recognition not supported in this browser
          </span>
        )}
      </div>

      {/* Main layout */}
      <div className="classroom-page__layout fade-up" style={{ animationDelay: '0.2s' }}>
        {/* Student panel */}
        <div className="classroom-page__panel">
          <div className="classroom-page__panel-header">
            <span className="classroom-page__panel-icon">◈</span>
            <span className="classroom-page__panel-title">Student (Sign → Text)</span>
          </div>

          <CameraFeed videoRef={videoRef} canvasRef={canvasRef} active={active} />

          {/* Live sign */}
          <div className="classroom-page__live-sign">
            <span className="classroom-page__live-label">Current sign:</span>
            <span className={`classroom-page__live-word ${signPrediction ? 'classroom-page__live-word--active' : ''}`}>
              {signPrediction || (sessionActive ? '…' : '—')}
            </span>
          </div>

          {/* Sign transcript */}
          <div className="classroom-page__scroll-box">
            <p className="classroom-page__scroll-label">Sign transcript</p>
            <div className="classroom-page__tokens">
              {signTranscript.length === 0
                ? <span className="classroom-page__empty-note">Signs will appear here…</span>
                : signTranscript.map((e) => (
                    <span key={e.id} className="pred-display__token">{e.word}</span>
                  ))
              }
            </div>
          </div>
        </div>

        {/* Teacher panel */}
        <div className="classroom-page__panel">
          <div className="classroom-page__panel-header">
            <span className="classroom-page__panel-icon">◎</span>
            <span className="classroom-page__panel-title">Teacher (Speech → Caption)</span>
          </div>

          {/* Live caption bubble */}
          <div className={`classroom-page__caption-box ${speechCaption ? 'classroom-page__caption-box--active' : ''}`}>
            {speechCaption
              ? <p className="classroom-page__caption-live">{speechCaption}</p>
              : <p className="classroom-page__caption-placeholder">
                  {speechActive
                    ? '🎤 Listening for speech…'
                    : 'Start the session to enable captioning'}
                </p>
            }
          </div>

          {/* Speech history */}
          <div className="classroom-page__scroll-box classroom-page__speech-history">
            <p className="classroom-page__scroll-label">Spoken captions</p>
            <div className="classroom-page__speech-list">
              {speechHistory.length === 0
                ? <span className="classroom-page__empty-note">Captions will appear here…</span>
                : speechHistory.map((e) => (
                    <div key={e.id} className="classroom-page__speech-item fade-in">
                      <span className="classroom-page__speech-dot" />
                      <p>{e.text}</p>
                    </div>
                  ))
              }
            </div>
          </div>

          {/* Copy captions */}
          {speechHistory.length > 0 && (
            <button
              className="btn btn-ghost"
              style={{ fontSize: '0.8rem', padding: '8px 16px', marginTop: '8px' }}
              onClick={() =>
                navigator.clipboard.writeText(speechHistory.map((e) => e.text).join(' '))
              }
            >
              📋 Copy Captions
            </button>
          )}
        </div>
      </div>
    </div>
  );
}