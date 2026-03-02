// ============================================================
// useCamera – manages webcam stream + JPEG frame capture
// Used by: SignDetector page
// ============================================================

import { useRef, useState, useCallback } from 'react';

export function useCamera() {
  const videoRef   = useRef(null);
  const canvasRef  = useRef(null);
  const streamRef  = useRef(null);

  const [active, setActive]   = useState(false);
  const [error,  setError]    = useState(null);

  // ── Start camera ─────────────────────────────────────────
  const startCamera = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
        audio: false,
      });
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        // Wait for metadata so videoWidth/videoHeight are set
        await new Promise((res, rej) => {
          videoRef.current.onloadedmetadata = res;
          videoRef.current.onerror = rej;
        });
        await videoRef.current.play();
      }
      setActive(true);
    } catch (err) {
      const msg =
        err.name === 'NotAllowedError'
          ? 'Camera permission denied. Please allow access and retry.'
          : err.name === 'NotFoundError'
          ? 'No camera found on this device.'
          : `Camera error: ${err.message}`;
      setError(msg);
    }
  }, []);

  // ── Stop camera ──────────────────────────────────────────
  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setActive(false);
    setError(null);
  }, []);

  // ── Capture frame → JPEG Blob ────────────────────────────
  // Returns a Promise<Blob|null>
  const captureFrame = useCallback(() => {
    const video  = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < 2) return Promise.resolve(null);

    const w = video.videoWidth  || 640;
    const h = video.videoHeight || 480;
    canvas.width  = w;
    canvas.height = h;

    const ctx = canvas.getContext('2d');
    // Mirror the frame (matches backend/dev/testcamera.py: cv2.flip(frame, 1))
    ctx.save();
    ctx.scale(-1, 1);
    ctx.drawImage(video, -w, 0, w, h);
    ctx.restore();

    return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.85));
  }, []);

  return { videoRef, canvasRef, active, error, startCamera, stopCamera, captureFrame };
}