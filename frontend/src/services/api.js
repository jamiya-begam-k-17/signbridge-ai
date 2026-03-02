// ============================================================
// SignBridge API Service
// Communicates with FastAPI backend (backend/main.py)
//
// Endpoints consumed:
//   GET  /health   → { status, service, model_loaded }
//   POST /predict  → { prediction } | { error }
//
// In dev, Vite proxies /api → http://localhost:8000
// In prod, set VITE_API_URL env variable
// ============================================================

const BASE_URL = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL
  : '/api'; // uses Vite proxy in dev (see vite.config.js)

// ── Health Check ────────────────────────────────────────────
// GET /health
// Checks if FastAPI server and model are ready.
// Returns: { status: "healthy"|"unhealthy", service: string, model_loaded: bool }
export async function checkHealth() {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5000);

  try {
    const res = await fetch(`${BASE_URL}/health`, {
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    clearTimeout(timer);
    if (err.name === 'AbortError') throw new Error('Backend timeout – is FastAPI running?');
    throw err;
  }
}

// ── Predict Sign ─────────────────────────────────────────────
// POST /predict  (multipart/form-data, field name: "file")
// Sends a JPEG frame blob captured from the webcam.
// Returns: { prediction: string } | { error: string }
//
// Matches backend/main.py:
//   async def predict(file: UploadFile = File(...)):
//       frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
//       prediction = predict_sign(frame)
//       return {"prediction": prediction}
export async function predictSign(imageBlob) {
  const formData = new FormData();
  // Backend reads this as UploadFile named "file"
  formData.append('file', imageBlob, 'frame.jpg');

  const res = await fetch(`${BASE_URL}/predict`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }

  return res.json();
  // { prediction: "hello" }   ← happy path
  // { error: "..." }          ← backend error
}