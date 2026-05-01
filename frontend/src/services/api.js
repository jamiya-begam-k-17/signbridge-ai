// ============================================================
// SignBridge API Service
// Communicates with FastAPI backend (backend/main.py)
//
// Endpoints consumed:
//   GET  /health   → { status, service, model_loaded }
//   POST /predict  → { prediction } | { error }
//   POST /register → { access_token, token_type }
//   POST /token    → { access_token, token_type }
//   POST /conversations → ConversationResponse
//   GET  /conversations → list[ConversationResponse]
//   POST /conversations/{id}/messages → MessageResponse
//   GET  /conversations/{id}/messages → list[MessageResponse]
//
// In dev, Vite proxies /api → http://localhost:8000
// In prod, set VITE_API_URL env variable
// ============================================================

import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL
  : '/api'; // uses Vite proxy in dev (see vite.config.js)

const api = axios.create({
  baseURL: BASE_URL,
});

// Add token to requests if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Health Check ────────────────────────────────────────────
// GET /health
// Checks if FastAPI server and model are ready.
// Returns: { status: "healthy"|"unhealthy", service: string, model_loaded: bool }
export async function checkHealth() {
  try {
    const res = await api.get('/health');
    return res.data;
  } catch (err) {
    throw new Error('Backend timeout – is FastAPI running?');
  }
}

// ── Auth Functions ──────────────────────────────────────────
export async function register(username, email, password, role = 'student') {
  const res = await api.post('/register', { username, email, password, role });
  return res.data;
}

// export async function login(username, password) {
//   const formData = new FormData();
//   formData.append('username', username);
//   formData.append('password', password);
//   const res = await api.post('/token', formData);
//   return res.data;
// }

export async function login(username, password) {
  const params = new URLSearchParams();
  params.append('username', username);
  params.append('password', password);

  const res = await api.post('/token', params, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });

  return res.data;
}

// ── Conversation Functions ───────────────────────────────────
export async function createConversation(studentId) {
  const res = await api.post('/conversations', { student_id: studentId });
  return res.data;
}

export async function getConversations() {
  const res = await api.get('/conversations');
  return res.data;
}

export async function sendMessage(conversationId, content) {
  const res = await api.post(`/conversations/${conversationId}/messages`, { content });
  return res.data;
}

export async function getMessages(conversationId) {
  const res = await api.get(`/conversations/${conversationId}/messages`);
  return res.data;
}

// ── Sign Prediction ─────────────────────────────────────
export async function predictSign(imageBlob) {
  const formData = new FormData();
  formData.append('file', imageBlob, 'frame.jpg');
  const res = await api.post('/predict', formData);
  return res.data;
}

// ── User Functions ───────────────────────────────────
export async function getUsers() {
  const res = await api.get('/users');
  return res.data;
}

