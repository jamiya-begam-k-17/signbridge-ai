import { useState, useRef, useCallback } from 'react';
import { useSpeech } from '../hooks/useSpeech';
import { predictVideoSign } from '../services/api';
import '../components/PredictionDisplay.css';
import './Detect.css';

const ACCEPTED_EXTENSIONS = ['.mp4', '.mov'];
const ACCEPTED_MIME = ['video/mp4', 'video/quicktime'];
const MAX_FILE_SIZE_MB = 100;

function isAcceptedFile(file) {
  if (!file) return false;
  const name = file.name?.toLowerCase() || '';
  const hasExt = ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext));
  const hasMime = !file.type || ACCEPTED_MIME.includes(file.type);
  return hasExt && hasMime;
}

export default function Detect() {
  const { speak, supported: speechSupported } = useSpeech();

  const [videoFile, setVideoFile]     = useState(null);
  const [videoUrl, setVideoUrl]       = useState(null);
  const [isDragging, setIsDragging]   = useState(false);
  const [isPredicting, setIsPredicting] = useState(false);
  const [result, setResult]           = useState(null); // { prediction, probability, status }
  const [fileError, setFileError]     = useState(null);
  const [apiError, setApiError]       = useState(null);

  const fileInputRef = useRef(null);

  // ── Handle a newly chosen/dropped file ────────────────────
  const handleFile = useCallback((file) => {
    setResult(null);
    setApiError(null);

    if (!file) return;

    if (!isAcceptedFile(file)) {
      setFileError('Unsupported file type. Please upload a .mp4 or .mov video.');
      return;
    }
    if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      setFileError(`File is too large. Max size is ${MAX_FILE_SIZE_MB}MB.`);
      return;
    }

    setFileError(null);
    setVideoFile(file);
    setVideoUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return URL.createObjectURL(file);
    });
  }, []);

  const handleInputChange = (e) => {
    handleFile(e.target.files?.[0]);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFile(e.dataTransfer.files?.[0]);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleBrowseClick = () => fileInputRef.current?.click();

  const handleReset = () => {
    setVideoFile(null);
    setVideoUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });
    setResult(null);
    setFileError(null);
    setApiError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // ── Send video to backend for prediction ──────────────────
  const handlePredict = async () => {
    if (!videoFile) return;
    setIsPredicting(true);
    setApiError(null);
    setResult(null);

    try {
      const data = await predictVideoSign(videoFile);

      if (data.error) {
        setApiError(data.error);
        return;
      }

      setResult({
        prediction: data.prediction,
        probability: data.probability ?? 0,
        status: data.status,
      });
    } catch (err) {
      setApiError(err?.response?.data?.error || err.message || 'Prediction failed');
    } finally {
      setIsPredicting(false);
    }
  };

  const friendlyStatus = (status) => {
    switch (status) {
      case 'no_hand_detected':
        return 'No hand/pose landmarks were detected in this video.';
      case 'model_unavailable':
        return 'Prediction model is currently unavailable.';
      default:
        return null;
    }
  };

  const hasUsablePrediction =
    result && result.status === 'ok' && result.prediction && result.prediction !== 'unknown';

  return (
    <div className="detect-page">
      <div className="detect-page__header fade-up">
        <h1 className="detect-page__title">Sign Detection</h1>
        <p className="detect-page__sub">
          Upload a short video of a sign — the AI model will analyse it and recognise the sign.
        </p>
      </div>

      {/* Error banners */}
      {(fileError || apiError) && (
        <div className="detect-page__error fade-in">⚠ {fileError || apiError}</div>
      )}

      <div className="detect-page__layout">
        {/* Upload column */}
        <div className="detect-page__camera-col">
          {!videoUrl ? (
            <div
              className={`detect-dropzone ${isDragging ? 'detect-dropzone--active' : ''}`}
              onClick={handleBrowseClick}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              role="button"
              tabIndex={0}
            >
              <div className="detect-dropzone__icon">🎬</div>
              <p className="detect-dropzone__title">Drag & drop a video here</p>
              <p className="detect-dropzone__sub">or click to browse · .mp4 / .mov</p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".mp4,.mov,video/mp4,video/quicktime"
                onChange={handleInputChange}
                hidden
              />
            </div>
          ) : (
            <div className="detect-preview">
              <video
                className="detect-preview__video"
                src={videoUrl}
                controls
                playsInline
              />
              <div className="detect-preview__meta">
                <span className="detect-preview__name">{videoFile?.name}</span>
                <span className="detect-preview__size">
                  {(videoFile.size / (1024 * 1024)).toFixed(1)} MB
                </span>
              </div>
            </div>
          )}

          {/* Controls */}
          <div className="detect-page__controls">
            {videoUrl && (
              <button
                className="btn btn-primary"
                onClick={handlePredict}
                disabled={isPredicting}
              >
                {isPredicting ? '⏳ Analysing…' : '▶ Predict Sign'}
              </button>
            )}
            {videoUrl && (
              <button className="btn btn-ghost" onClick={handleReset} disabled={isPredicting}>
                ✕ Remove Video
              </button>
            )}
          </div>

          {/* Tips */}
          <div className="detect-page__tips">
            <p className="detect-page__tips-title">Tips for best results</p>
            <ul>
              <li>Use a well-lit, plain background</li>
              <li>Keep your hand(s) fully visible throughout</li>
              <li>Perform the full sign motion clearly</li>
              <li>Videos of a few seconds work best</li>
              <li>Supported formats: MP4, MOV (max {MAX_FILE_SIZE_MB}MB)</li>
            </ul>
          </div>
        </div>

        {/* Prediction column */}
        <div className="detect-page__pred-col">
          <div className="pred-display">
            <div className="pred-display__current">
              <div className="pred-display__label">Detected Sign</div>
              <div
                className={`pred-display__word ${
                  hasUsablePrediction ? 'pred-display__word--active' : ''
                }`}
              >
                {isPredicting
                  ? '…'
                  : hasUsablePrediction
                  ? result.prediction
                  : '—'}
              </div>

              {result && !hasUsablePrediction && friendlyStatus(result.status) && (
                <p className="detect-page__result-note">{friendlyStatus(result.status)}</p>
              )}

              {hasUsablePrediction && (
                <>
                  <div className="detect-page__confidence">
                    Confidence: {(result.probability * 100).toFixed(1)}%
                  </div>
                  {speechSupported && (
                    <button
                      className="btn btn-ghost pred-display__speak-btn"
                      onClick={() => speak(result.prediction)}
                    >
                      🔊 Speak
                    </button>
                  )}
                </>
              )}
            </div>

            <hr className="divider" />

            <div className="detect-page__placeholder">
              {!videoUrl && (
                <p className="pred-display__empty">
                  Upload a video to see the predicted sign here…
                </p>
              )}
              {videoUrl && !result && !isPredicting && (
                <p className="pred-display__empty">
                  Click <strong>Predict Sign</strong> to analyse your video.
                </p>
              )}
              {isPredicting && (
                <p className="pred-display__empty">Processing video, please wait…</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}









// import { useState, useEffect, useRef, useCallback } from 'react';
// import { useCamera } from '../hooks/useCamera';
// import { useSpeech } from '../hooks/useSpeech';
// import { predictSign } from '../services/api';
// import CameraFeed from '../components/CameraFeed';
// import PredictionDisplay from '../components/PredictionDisplay';
// import './Detect.css';

// const PREDICT_INTERVAL_MS = 800; // how often we send a frame to backend

// export default function Detect() {
//   const { videoRef, canvasRef, active, error: camError, startCamera, stopCamera, captureFrame } =
//     useCamera();
//   const { speak, supported: speechSupported } = useSpeech();

//   const [isDetecting, setIsDetecting]     = useState(false);
//   const [prediction,  setPrediction]      = useState('');
//   const [transcript,  setTranscript]      = useState([]); // [{ id, word }]
//   const [apiError,    setApiError]        = useState(null);
//   const [fps,         setFps]             = useState(0);

//   const intervalRef   = useRef(null);
//   const lastWordRef   = useRef('');
//   const frameCount    = useRef(0);
//   const fpsTimer      = useRef(null);

//   // ── Run prediction loop ───────────────────────────────────
//   const runLoop = useCallback(async () => {
//     if (!active) return;
//     try {
//       const blob = await captureFrame();
//       if (!blob) return;

//       const result = await predictSign(blob);
//       frameCount.current++;

//       if (result.error) {
//         setApiError(result.error);
//         return;
//       }

//       setApiError(null);
//       const word = result.prediction;

//       if (word && word !== 'No hand detected') {
//         setPrediction(word);

//         // Append to transcript only if different from last word
//         if (word !== lastWordRef.current) {
//           lastWordRef.current = word;
//           setTranscript((prev) => [
//             ...prev,
//             { id: Date.now(), word },
//           ]);
//         }
//       } else {
//         setPrediction('');
//       }
//     } catch (err) {
//       setApiError(err.message);
//     }
//   }, [active, captureFrame]);

//   // ── Start detection ───────────────────────────────────────
//   const handleStart = useCallback(async () => {
//     await startCamera();
//     setIsDetecting(true);
//   }, [startCamera]);

//   // ── Stop detection ────────────────────────────────────────
//   const handleStop = useCallback(() => {
//     clearInterval(intervalRef.current);
//     clearInterval(fpsTimer.current);
//     stopCamera();
//     setIsDetecting(false);
//     setPrediction('');
//     setFps(0);
//   }, [stopCamera]);

//   // ── Prediction interval (starts after camera becomes active) ─
//   useEffect(() => {
//     if (active && isDetecting) {
//       intervalRef.current = setInterval(runLoop, PREDICT_INTERVAL_MS);

//       // FPS counter
//       fpsTimer.current = setInterval(() => {
//         setFps(frameCount.current);
//         frameCount.current = 0;
//       }, 1000);
//     }
//     return () => {
//       clearInterval(intervalRef.current);
//       clearInterval(fpsTimer.current);
//     };
//   }, [active, isDetecting, runLoop]);

//   const clearTranscript = () => {
//     setTranscript([]);
//     lastWordRef.current = '';
//     setPrediction('');
//   };

//   return (
//     <div className="detect-page">
//       <div className="detect-page__header fade-up">
//         <h1 className="detect-page__title">Sign Detection</h1>
//         <p className="detect-page__sub">
//           Show a sign to the camera — the AI model will recognise it in real time.
//         </p>
//       </div>

//       {/* Error banners */}
//       {(camError || apiError) && (
//         <div className="detect-page__error fade-in">
//           ⚠ {camError || apiError}
//         </div>
//       )}

//       <div className="detect-page__layout">
//         {/* Camera column */}
//         <div className="detect-page__camera-col">
//           <CameraFeed videoRef={videoRef} canvasRef={canvasRef} active={active} />

//           {/* Controls */}
//           <div className="detect-page__controls">
//             {!isDetecting ? (
//               <button className="btn btn-primary" onClick={handleStart}>
//                 ▶ Start Detection
//               </button>
//             ) : (
//               <button className="btn btn-danger" onClick={handleStop}>
//                 ■ Stop
//               </button>
//             )}

//             {isDetecting && (
//               <div className="detect-page__fps">
//                 <span className="detect-page__fps-dot" />
//                 {fps} req/s
//               </div>
//             )}
//           </div>

//           {/* Tips */}
//           <div className="detect-page__tips">
//             <p className="detect-page__tips-title">Tips for best results</p>
//             <ul>
//               <li>Ensure good, even lighting</li>
//               <li>Keep your hand fully visible in frame</li>
//               <li>Hold the sign steady for ~1 second</li>
//               <li>Plain background improves accuracy</li>
//             </ul>
//           </div>
//         </div>

//         {/* Prediction column */}
//         <div className="detect-page__pred-col">
//           <PredictionDisplay
//             prediction={prediction}
//             transcript={transcript}
//             isDetecting={isDetecting}
//             onClearTranscript={clearTranscript}
//             onSpeak={speechSupported ? speak : null}
//           />
//         </div>
//       </div>
//     </div>
//   );
// }