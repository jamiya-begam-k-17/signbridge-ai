import CameraFeed from '../CameraFeed';
import '../../pages/Classroom.css';

export default function SignRecognitionPanel({
  videoRef,
  canvasRef,
  active,
  sessionActive,
  currentSign,
  signHistory,
  formatSignWord,
  placeholderText,
}) {
  return (
    <section className="cr-panel cr-panel--left">
      <div className="cr-panel-head">
        <span className="cr-panel-icon">◈</span>
        <span className="cr-panel-title">Sign Language Recognition</span>
      </div>

      <div className="cr-recognition-grid">
        <div className="cr-recognition-video">
          <CameraFeed videoRef={videoRef} canvasRef={canvasRef} active={active} />
          {!sessionActive && (
            <div className="cr-cam-placeholder">{placeholderText}</div>
          )}
        </div>

        <div className="cr-sign-summary">
          <div className="cr-sign-summary__label">Detected Sign</div>
          <div className="cr-sign-summary__word">
            {currentSign ? formatSignWord(currentSign) : (sessionActive ? 'Detecting sign...' : 'No active session')}
          </div>
          <div className="cr-sign-summary__note">
            {sessionActive
              ? 'Real-time sign text updates as detection occurs.'
              : 'Start a session to view live sign detection.'}
          </div>
        </div>

        <div className="cr-sign-history">
          <div className="cr-sign-history__label">Recent detected signs</div>
          <div className="cr-sign-history__list">
            {signHistory.length > 0 ? (
              signHistory.map((word, index) => (
                <span key={`${word}-${index}`} className="cr-sign-history__word">
                  {formatSignWord(word)}
                </span>
              ))
            ) : (
              <span className="cr-sign-history__empty">
                Detected signs appear here as a sentence stream.
              </span>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
