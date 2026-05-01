import { useState, useEffect, useRef, useCallback } from 'react';
import { useCamera } from '../hooks/useCamera';
import { useSpeech } from '../hooks/useSpeech';
import { predictSign } from '../services/api';
import CameraFeed from '../components/CameraFeed';
import PredictionDisplay from '../components/PredictionDisplay';
import './Detect.css';

const PREDICT_INTERVAL_MS = 800; // how often we send a frame to backend

export default function Detect() {
  const { videoRef, canvasRef, active, error: camError, startCamera, stopCamera, captureFrame } =
    useCamera();
  const { speak, supported: speechSupported } = useSpeech();

  const [isDetecting, setIsDetecting]     = useState(false);
  const [prediction,  setPrediction]      = useState('');
  const [transcript,  setTranscript]      = useState([]); // [{ id, word }]
  const [apiError,    setApiError]        = useState(null);
  const [fps,         setFps]             = useState(0);

  const intervalRef   = useRef(null);
  const lastWordRef   = useRef('');
  const frameCount    = useRef(0);
  const fpsTimer      = useRef(null);

  // ── Run prediction loop ───────────────────────────────────
  const runLoop = useCallback(async () => {
    if (!active) return;
    try {
      const blob = await captureFrame();
      if (!blob) return;

      const result = await predictSign(blob);
      frameCount.current++;

      if (result.error) {
        setApiError(result.error);
        return;
      }

      setApiError(null);
      const word = result.prediction;

      if (word && word !== 'No hand detected') {
        setPrediction(word);

        // Append to transcript only if different from last word
        if (word !== lastWordRef.current) {
          lastWordRef.current = word;
          setTranscript((prev) => [
            ...prev,
            { id: Date.now(), word },
          ]);
        }
      } else {
        setPrediction('');
      }
    } catch (err) {
      setApiError(err.message);
    }
  }, [active, captureFrame]);

  // ── Start detection ───────────────────────────────────────
  const handleStart = useCallback(async () => {
    await startCamera();
    setIsDetecting(true);
  }, [startCamera]);

  // ── Stop detection ────────────────────────────────────────
  const handleStop = useCallback(() => {
    clearInterval(intervalRef.current);
    clearInterval(fpsTimer.current);
    stopCamera();
    setIsDetecting(false);
    setPrediction('');
    setFps(0);
  }, [stopCamera]);

  // ── Prediction interval (starts after camera becomes active) ─
  useEffect(() => {
    if (active && isDetecting) {
      intervalRef.current = setInterval(runLoop, PREDICT_INTERVAL_MS);

      // FPS counter
      fpsTimer.current = setInterval(() => {
        setFps(frameCount.current);
        frameCount.current = 0;
      }, 1000);
    }
    return () => {
      clearInterval(intervalRef.current);
      clearInterval(fpsTimer.current);
    };
  }, [active, isDetecting, runLoop]);

  const clearTranscript = () => {
    setTranscript([]);
    lastWordRef.current = '';
    setPrediction('');
  };

  return (
    <div className="detect-page">
      <div className="detect-page__header fade-up">
        <h1 className="detect-page__title">Sign Detection</h1>
        <p className="detect-page__sub">
          Show a sign to the camera — the AI model will recognise it in real time.
        </p>
      </div>

      {/* Error banners */}
      {(camError || apiError) && (
        <div className="detect-page__error fade-in">
          ⚠ {camError || apiError}
        </div>
      )}

      <div className="detect-page__layout">
        {/* Camera column */}
        <div className="detect-page__camera-col">
          <CameraFeed videoRef={videoRef} canvasRef={canvasRef} active={active} />

          {/* Controls */}
          <div className="detect-page__controls">
            {!isDetecting ? (
              <button className="btn btn-primary" onClick={handleStart}>
                ▶ Start Detection
              </button>
            ) : (
              <button className="btn btn-danger" onClick={handleStop}>
                ■ Stop
              </button>
            )}

            {isDetecting && (
              <div className="detect-page__fps">
                <span className="detect-page__fps-dot" />
                {fps} req/s
              </div>
            )}
          </div>

          {/* Tips */}
          <div className="detect-page__tips">
            <p className="detect-page__tips-title">Tips for best results</p>
            <ul>
              <li>Ensure good, even lighting</li>
              <li>Keep your hand fully visible in frame</li>
              <li>Hold the sign steady for ~1 second</li>
              <li>Plain background improves accuracy</li>
            </ul>
          </div>
        </div>

        {/* Prediction column */}
        <div className="detect-page__pred-col">
          <PredictionDisplay
            prediction={prediction}
            transcript={transcript}
            isDetecting={isDetecting}
            onClearTranscript={clearTranscript}
            onSpeak={speechSupported ? speak : null}
          />
        </div>
      </div>
    </div>
  );
}