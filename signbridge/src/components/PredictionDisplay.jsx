// ============================================================
// PredictionDisplay
// Shows the current sign prediction + rolling transcript
// ============================================================

import './PredictionDisplay.css';

export default function PredictionDisplay({ prediction, transcript, isDetecting, onClearTranscript, onSpeak }) {
  return (
    <div className="pred-display">
      {/* Current prediction */}
      <div className="pred-display__current">
        <div className="pred-display__label">Detected Sign</div>
        <div className={`pred-display__word ${prediction ? 'pred-display__word--active' : ''}`}>
          {prediction || (isDetecting ? '…' : '—')}
        </div>
        {prediction && (
          <button className="btn btn-ghost pred-display__speak-btn" onClick={() => onSpeak(prediction)}>
            🔊 Speak
          </button>
        )}
      </div>

      <hr className="divider" />

      {/* Transcript */}
      <div className="pred-display__transcript-header">
        <span className="pred-display__label">Session Transcript</span>
        {transcript.length > 0 && (
          <button className="pred-display__clear" onClick={onClearTranscript}>
            Clear
          </button>
        )}
      </div>

      <div className="pred-display__transcript">
        {transcript.length === 0 ? (
          <p className="pred-display__empty">Detected words will appear here…</p>
        ) : (
          transcript.map((entry, i) => (
            <span
              key={entry.id}
              className="pred-display__token"
              style={{ animationDelay: `${i * 0.03}s` }}
            >
              {entry.word}
            </span>
          ))
        )}
      </div>

      {/* Copy sentence */}
      {transcript.length > 0 && (
        <button
          className="btn btn-ghost pred-display__copy"
          onClick={() =>
            navigator.clipboard.writeText(transcript.map((e) => e.word).join(' '))
          }
        >
          📋 Copy Transcript
        </button>
      )}
    </div>
  );
}