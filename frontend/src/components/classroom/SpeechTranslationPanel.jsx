import '../../pages/Classroom.css';

export default function SpeechTranslationPanel({
  speechMode,
  setSpeechMode,
  sessionActive,
  speechSupported,
  speechActive,
  pushToTalkActive,
  interimCaption,
  finalCaption,
  teacherCaptions,
  onStartLecture,
  onPauseLecture,
  onStartPushToTalk,
  onStopPushToTalk,
}) {
  return (
    <section className="cr-panel cr-panel--right">
      <div className="cr-panel-head">
        <span className="cr-panel-icon">🎙</span>
        <span className="cr-panel-title">Speech Translation</span>
      </div>

      <div className="cr-mode-switch">
        <button
          className={`cr-mode-button ${speechMode === 'lecture' ? 'cr-mode-button--active' : ''}`}
          onClick={() => setSpeechMode('lecture')}
          type="button"
        >
          Lecture Mode
        </button>
        <button
          className={`cr-mode-button ${speechMode === 'discussion' ? 'cr-mode-button--active' : ''}`}
          onClick={() => setSpeechMode('discussion')}
          type="button"
        >
          Discussion Mode
        </button>
      </div>

      {speechMode === 'lecture' ? (
        <div className="cr-speech-controls">
          <button
            type="button"
            className="btn btn-primary cr-speech-action"
            disabled={!sessionActive || !speechSupported || speechActive}
            onClick={onStartLecture}
          >
            Start Speaking
          </button>
          <button
            type="button"
            className="btn btn-ghost cr-speech-action"
            disabled={!sessionActive || !speechSupported || !speechActive}
            onClick={onPauseLecture}
          >
            Pause
          </button>
        </div>
      ) : (
        <div className="cr-ptt-panel">
          <button
            type="button"
            className={`cr-ptt-button ${pushToTalkActive ? 'cr-ptt-button--active' : ''}`}
            onMouseDown={onStartPushToTalk}
            onMouseUp={onStopPushToTalk}
            onMouseLeave={pushToTalkActive ? onStopPushToTalk : undefined}
            onTouchStart={onStartPushToTalk}
            onTouchEnd={onStopPushToTalk}
            disabled={!sessionActive || !speechSupported}
          >
            {pushToTalkActive ? 'Speaking...' : 'Push to Talk'}
          </button>
          <div className="cr-ptt-hint">
            Hold the button to capture participant speech.
          </div>
        </div>
      )}

      <div className="cr-translation-box">
        <div className="cr-translation-box__header">Live Caption</div>
        <p className="cr-translation-box__content">
          {interimCaption || finalCaption || (sessionActive ? 'Listening for speech...' : 'Start a session to view captions.')}
        </p>
      </div>

      <div className="cr-caption-info">
        {speechMode === 'lecture'
          ? 'Lecture mode suppresses the trigger phrase and captures the remaining speech as live caption.'
          : 'Discussion mode captures all detected speech normally.'}
      </div>

      <div className="cr-translation-history">
        <div className="cr-translation-history__heading">Finalized Captions</div>
        {teacherCaptions.length > 0 ? (
          <ul className="cr-caption-list">
            {teacherCaptions.map((caption, index) => (
              <li key={index} className="cr-caption-list__item">
                {caption}
              </li>
            ))}
          </ul>
        ) : (
          <div className="cr-translation-history__item">
            Finalized captions appear here after each detected phrase.
          </div>
        )}
      </div>
    </section>
  );
}
