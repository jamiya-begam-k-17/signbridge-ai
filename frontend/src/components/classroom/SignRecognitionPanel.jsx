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
          <div className="cr-sign-summary__label">Current sign</div>
          <div className="cr-sign-summary__word">
            {currentSign ? formatSignWord(currentSign) : (sessionActive ? 'Detecting sign...' : 'No active session')}
          </div>
          <div className="cr-sign-summary__note">
            {sessionActive
              ? 'Live sign detection appears below the camera preview.'
              : 'Start a session to view live sign detection.'}
          </div>
        </div>

        <div className="cr-sign-history">
          <div className="cr-sign-history__label">Sign sentence</div>
          <p className="cr-sign-history__sentence">
            {signHistory.length > 0
              ? `${signHistory.map((word) => formatSignWord(word)).join(', ')}.`
              : 'Detected signs will form a natural sentence here as students perform new gestures.'}
          </p>
        </div>
      </div>
    </section>
  );
}
