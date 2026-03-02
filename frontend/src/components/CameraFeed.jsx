// ============================================================
// CameraFeed – renders webcam video + hidden canvas for capture
// ============================================================

import './CameraFeed.css';

export default function CameraFeed({ videoRef, canvasRef, active }) {
  return (
    <div className={`camera-feed ${active ? 'camera-feed--active' : ''}`}>
      {/* Hidden canvas used by useCamera.captureFrame() */}
      <canvas ref={canvasRef} className="camera-feed__canvas" />

      {/* Webcam video */}
      <video
        ref={videoRef}
        className="camera-feed__video"
        muted
        playsInline
        autoPlay
      />

      {/* Overlay elements (only when active) */}
      {active && (
        <>
          {/* Corner brackets */}
          <div className="camera-feed__corner camera-feed__corner--tl" />
          <div className="camera-feed__corner camera-feed__corner--tr" />
          <div className="camera-feed__corner camera-feed__corner--bl" />
          <div className="camera-feed__corner camera-feed__corner--br" />

          {/* Scan line animation */}
          <div className="camera-feed__scanline" />

          {/* Live label */}
          <div className="camera-feed__live-badge">
            <span className="badge badge-live">LIVE</span>
          </div>
        </>
      )}

      {/* Idle placeholder */}
      {!active && (
        <div className="camera-feed__placeholder">
          <div className="camera-feed__placeholder-icon">◈</div>
          <p>Camera inactive</p>
          <span>Click "Start Detection" to begin</span>
        </div>
      )}
    </div>
  );
}