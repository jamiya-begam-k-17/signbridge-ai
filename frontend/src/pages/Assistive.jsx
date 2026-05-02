// ============================================================
// Assistive Mode – for visually impaired students
// ============================================================

import { useState, useEffect, useRef, useCallback } from 'react';
import { useAssistiveVoice } from '../context/AssistiveVoiceContext';
import './Assistive.css';

export default function Assistive() {
  const videoRef    = useRef(null);
  const canvasRef   = useRef(null);
  const streamRef   = useRef(null);
  const cameraOnRef = useRef(false); // ref so callbacks always read current value

  const [cameraOn,  setCameraOn]  = useState(false);
  const [snapshot,  setSnapshot]  = useState(null);
  const [ocrText,   setOcrText]   = useState('');
  const [status,    setStatus]    = useState('idle');
  const [statusMsg, setStatusMsg] = useState('');

  const { lastExtractedText, setLastExtractedText, isSpeaking, speak, stopSpeaking } =
    useAssistiveVoice();

  // keep ref in sync with state
  const setCameraOnBoth = (val) => {
    cameraOnRef.current = val;
    setCameraOn(val);
  };

  // ── Camera ──────────────────────────────────────────────
  const startCamera = useCallback(async () => {
    if (cameraOnRef.current) return; // already on — don't speak again
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'environment' },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraOnBoth(true);
      setStatusMsg('Camera ready. Press "Capture & Read" or Space.');
      // speak only once here — no loop
      speak('Camera is on. Press Capture and Read to begin.');
    } catch {
      setStatusMsg('Camera access denied. Please allow camera permission.');
      speak('Camera access denied.');
    }
  }, [speak]);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;
    setCameraOnBoth(false);
    setStatusMsg('');
  }, []);

  // ── Capture frame ─────────────────────────────────────
  const captureFrame = useCallback(() => {
    const video  = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < 2) return null;
    canvas.width  = video.videoWidth  || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.9);
  }, []);

  // ── OCR + Speak ───────────────────────────────────────
  // Uses ref so it always reads the LIVE cameraOn value — no stale closure bug
  const runOCRAndSpeak = useCallback(async () => {
    if (!cameraOnRef.current) {
      // camera off: just start it, don't recurse
      speak('Starting camera. Please wait, then press Capture again.');
      await startCamera();
      return;
    }

    const dataUrl = captureFrame();
    if (!dataUrl) {
      speak('Could not capture image. Try again.');
      return;
    }

    setSnapshot(dataUrl);
    setStatus('loading');
    setStatusMsg('Reading text from image…');
    speak('Captured. Reading text now, please wait.');

    try {
      const Tesseract = (await import('tesseract.js')).default;
      const result    = await Tesseract.recognize(dataUrl, 'eng', { logger: () => {} });
      const text      = result.data.text.trim();

      if (!text) {
        setStatus('done');
        setStatusMsg('No text found in image.');
        speak('No readable text found in the image. Try better lighting.');
        return;
      }

      setOcrText(text);
      setLastExtractedText(text);
      setStatus('done');
      setStatusMsg('Done! Reading aloud…');
      speak(text);
    } catch {
      setStatus('error');
      setStatusMsg('OCR failed. Please try again.');
      speak('Text reading failed. Please try again.');
    }
  }, [speak, startCamera, captureFrame, setLastExtractedText]);

  // ── Voice command wiring ──────────────────────────────
  // Store runOCRAndSpeak in a ref so the event listener never goes stale
  const runOCRRef = useRef(runOCRAndSpeak);
  useEffect(() => { runOCRRef.current = runOCRAndSpeak; }, [runOCRAndSpeak]);

  useEffect(() => {
    const onVoiceCmd = (e) => {
      const cmd = e.detail;
      if (cmd === 'start_reading' || cmd === 'capture') {
        runOCRRef.current();
      } else if (cmd === 'pause') {
        stopSpeaking();
      } else if (cmd === 'repeat') {
        if (lastExtractedText) speak(lastExtractedText);
        else speak('Nothing to repeat yet.');
      }
    };
    window.addEventListener('assistive-voice-cmd', onVoiceCmd);
    return () => window.removeEventListener('assistive-voice-cmd', onVoiceCmd);
  // only register once — uses refs internally
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Keyboard shortcuts ────────────────────────────────
  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.code === 'Space') { e.preventDefault(); runOCRRef.current(); }
      if (e.key  === 'p')    stopSpeaking();
      if (e.key  === 'r' && lastExtractedText) speak(lastExtractedText);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastExtractedText]);

  // Cleanup on unmount
  useEffect(() => () => stopCamera(), [stopCamera]);

  return (
    <div className="assistive-page" role="main" aria-label="Assistive Mode">

      <div className="assistive-page__header fade-up">
        <h1 className="assistive-page__title">
          <span aria-hidden="true">◉</span> Vision Assist
        </h1>
        <p className="assistive-page__sub">
          Point your camera at any printed text — the app will read it aloud instantly.
          Use voice commands or keyboard shortcuts.
        </p>
      </div>

      {/* Voice command hint bar */}
      <div className="assistive-page__hint-bar fade-up" aria-label="Voice commands">
        <span className="assistive-hint__chip">🎙 "start reading"</span>
        <span className="assistive-hint__chip">📷 "capture image"</span>
        <span className="assistive-hint__chip">⏸ "pause"</span>
        <span className="assistive-hint__chip">🔁 "repeat"</span>
        <span className="assistive-hint__chip assistive-hint__chip--key">Space = capture</span>
        <span className="assistive-hint__chip assistive-hint__chip--key">P = pause</span>
        <span className="assistive-hint__chip assistive-hint__chip--key">R = repeat</span>
      </div>

      <div className="assistive-page__layout fade-up" style={{ animationDelay: '0.1s' }}>

        {/* Camera panel */}
        <div className="assistive-page__camera-panel">
          <div className={`assistive-page__viewfinder ${cameraOn ? 'assistive-page__viewfinder--active' : ''}`}>
            <video ref={videoRef} muted playsInline className="assistive-page__video" />
            <canvas ref={canvasRef} style={{ display: 'none' }} />

            {!cameraOn && (
              <div className="assistive-page__placeholder" aria-live="polite">
                <div className="assistive-page__placeholder-icon" aria-hidden="true">◈</div>
                <p>Camera is off</p>
                <span>Press "Start Camera" to begin</span>
              </div>
            )}

            {cameraOn && (
              <div className="assistive-page__live-badge">
                <span className="badge badge-live">LIVE</span>
              </div>
            )}
          </div>

          {/* Camera controls */}
          <div className="assistive-page__cam-controls">
            {!cameraOn ? (
              <button
                className="btn btn-primary assistive-page__big-btn"
                onClick={startCamera}
                aria-label="Start camera"
              >
                ▶ Start Camera
              </button>
            ) : (
              <>
                <button
                  className="btn btn-primary assistive-page__big-btn"
                  onClick={runOCRAndSpeak}
                  aria-label="Capture and read text"
                  disabled={status === 'loading'}
                >
                  {status === 'loading' ? '⟳ Reading…' : '📷 Capture & Read'}
                </button>
                <button
                  className="btn btn-ghost"
                  onClick={stopCamera}
                  aria-label="Stop camera"
                >
                  ■ Stop Camera
                </button>
              </>
            )}
          </div>

          {/* Status */}
          {statusMsg && (
            <div
              className={`assistive-page__status assistive-page__status--${status}`}
              role="status"
              aria-live="polite"
            >
              {status === 'loading' && <span className="assistive-spinner" aria-hidden="true" />}
              {statusMsg}
            </div>
          )}
        </div>

        {/* Results panel */}
        <div className="assistive-page__results-panel">

          {snapshot && (
            <div className="assistive-page__snapshot-wrap">
              <p className="assistive-page__section-label">Captured Image</p>
              <img src={snapshot} alt="Captured frame for OCR" className="assistive-page__snapshot" />
            </div>
          )}

          <div className="assistive-page__text-box" aria-live="polite">
            <p className="assistive-page__section-label">Extracted Text</p>
            {ocrText ? (
              <>
                <div className="assistive-page__ocr-text">{ocrText}</div>
                <div className="assistive-page__text-actions">
                  <button
                    className="btn btn-primary"
                    onClick={() => speak(ocrText)}
                    aria-label="Read text aloud"
                    disabled={isSpeaking}
                  >
                    🔊 {isSpeaking ? 'Speaking…' : 'Read Aloud'}
                  </button>
                  <button className="btn btn-ghost" onClick={stopSpeaking} aria-label="Pause speech">
                    ⏸ Pause
                  </button>
                  <button
                    className="btn btn-ghost"
                    onClick={() => navigator.clipboard.writeText(ocrText)}
                    aria-label="Copy text"
                  >
                    📋 Copy
                  </button>
                </div>
              </>
            ) : (
              <p className="assistive-page__empty">
                {status === 'loading'
                  ? 'Analyzing image…'
                  : 'No text extracted yet. Capture an image to begin.'}
              </p>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
