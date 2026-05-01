// ============================================================
// Classroom.jsx – Redesigned
// Layout: [Camera+Sign Panel] | [Main Sign Display] | [Chatbox]
// Flow: choose student → start session → signs go to chat as
//       student messages; teacher speech goes to chat as
//       teacher messages; both can also type freely.
//       On end session → saved to DB with teacher + student.
// ============================================================

import { useState, useEffect, useRef, useCallback } from 'react';
import { useCamera }  from '../hooks/useCamera';
import { useSpeech }  from '../hooks/useSpeech';
import { predictSign, getUsers, createConversation, sendMessage } from '../services/api';
import CameraFeed from '../components/CameraFeed';
import './Classroom.css';

const PREDICT_INTERVAL_MS = 1000;

export default function Classroom() {
  // ── Camera / sign detection ────────────────────────────────
  const { videoRef, canvasRef, active, error: camError, startCamera, stopCamera, captureFrame } =
    useCamera();
  const { speak } = useSpeech();

  // ── Students list ──────────────────────────────────────────
  const [students,         setStudents]        = useState([]);
  const [selectedStudent,  setSelectedStudent]  = useState('');

  // ── Session state ──────────────────────────────────────────
  const [sessionActive,    setSessionActive]    = useState(false);
  const [convId,           setConvId]           = useState(null);

  // ── Sign detection ─────────────────────────────────────────
  const [currentSign,      setCurrentSign]      = useState('');

  // ── Chat messages: { id, role: 'student'|'teacher', text, time } ──
  const [chatMessages,     setChatMessages]     = useState([]);
  const [teacherInput,     setTeacherInput]     = useState('');
  const chatEndRef = useRef(null);

  // ── Speech recognition ─────────────────────────────────────
  const [speechActive,     setSpeechActive]     = useState(false);
  const [speechSupported,  setSpeechSupported]  = useState(false);
  const [interimCaption,   setInterimCaption]   = useState('');

  const intervalRef    = useRef(null);
  const lastSignRef    = useRef('');
  const recognitionRef = useRef(null);
  const signBufferRef  = useRef([]);

  // ── Load students ──────────────────────────────────────────
  useEffect(() => {
    getUsers()
      .then(setStudents)
      .catch(err => console.error('Could not load students', err));
  }, []);

  // ── Auto-scroll chat ───────────────────────────────────────
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // ── Speech recognition setup ───────────────────────────────
  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { setSpeechSupported(false); return; }
    setSpeechSupported(true);

    const rec = new SR();
    rec.continuous     = true;
    rec.interimResults = true;
    rec.lang           = 'en-US';

    rec.onresult = (event) => {
      let interim = '';
      let final   = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) final += t;
        else interim += t;
      }
      setInterimCaption(interim || final);
      if (final.trim()) {
        const text = final.trim();
        setInterimCaption('');
        addMessage('teacher', text);
        // persist to DB if session active
        if (convId) {
          sendMessage(convId, `[Teacher] ${text}`).catch(() => {});
        }
      }
    };
    rec.onerror = e => console.warn('Speech error:', e.error);
    recognitionRef.current = rec;
    return () => rec.stop();
  }, [convId]);

  // ── Sign prediction loop ───────────────────────────────────
  const runSignPrediction = useCallback(async () => {
    if (!active) return;
    try {
      const blob = await captureFrame();
      if (!blob) return;
      const result = await predictSign(blob);
      const word   = result.prediction;

      if (word && word !== 'No hand detected') {
        setCurrentSign(word);
        if (word !== lastSignRef.current) {
          lastSignRef.current = word;
          // Buffer signs, push to chat as student message
          signBufferRef.current.push(word);
          speak(word);

          // Add sign as student chat message
          addMessage('student', word);

          // Persist to DB
          if (convId) {
            sendMessage(convId, `[Student Sign] ${word}`).catch(() => {});
          }
        }
      } else {
        setCurrentSign('');
      }
    } catch (_) {}
  }, [active, captureFrame, speak, convId]);

  // ── Start session ──────────────────────────────────────────
  const startSession = useCallback(async () => {
    if (!selectedStudent) return;
    try {
      const conv = await createConversation(parseInt(selectedStudent));
      setConvId(conv.id);
    } catch (e) {
      console.error('Could not create conversation', e);
    }
    await startCamera();
    setSessionActive(true);
    setChatMessages([]);
    lastSignRef.current = '';
    signBufferRef.current = [];

    if (speechSupported && recognitionRef.current) {
      try { recognitionRef.current.start(); setSpeechActive(true); }
      catch (_) {}
    }
  }, [selectedStudent, startCamera, speechSupported]);

  // ── Stop session ───────────────────────────────────────────
  const stopSession = useCallback(() => {
    clearInterval(intervalRef.current);
    stopCamera();
    if (recognitionRef.current && speechActive) {
      recognitionRef.current.stop();
      setSpeechActive(false);
    }
    setSessionActive(false);
    setCurrentSign('');
    setInterimCaption('');
    setConvId(null);
  }, [stopCamera, speechActive]);

  // ── Prediction interval ────────────────────────────────────
  useEffect(() => {
    if (active && sessionActive) {
      intervalRef.current = setInterval(runSignPrediction, PREDICT_INTERVAL_MS);
    }
    return () => clearInterval(intervalRef.current);
  }, [active, sessionActive, runSignPrediction]);

  // ── Helpers ────────────────────────────────────────────────
  const addMessage = (role, text) => {
    setChatMessages(prev => [...prev, {
      id: Date.now() + Math.random(),
      role,
      text,
      time: new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
    }]);
  };

  const handleTeacherSend = async () => {
    if (!teacherInput.trim()) return;
    const text = teacherInput.trim();
    setTeacherInput('');
    addMessage('teacher', text);
    if (convId) {
      sendMessage(convId, `[Teacher] ${text}`).catch(() => {});
    }
  };

  const handleStudentType = async (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const text = e.target.value.trim();
      if (!text) return;
      e.target.value = '';
      addMessage('student', text);
      if (convId) {
        sendMessage(convId, `[Student] ${text}`).catch(() => {});
      }
    }
  };

  const selectedStudentName = students.find(s => String(s.id) === String(selectedStudent))?.username;

  return (
    <div className="cr-page">
      {/* ── Header ─────────────────────────────────────────── */}
      <div className="cr-header fade-up">
        <div className="cr-header__left">
          <h1 className="cr-title">Classroom</h1>
          {sessionActive && (
            <span className="badge badge-live">LIVE · {selectedStudentName}</span>
          )}
        </div>
        <p className="cr-sub">
          Student signs are detected and shown in the chat. Teacher speech is captioned automatically.
        </p>
      </div>

      {camError && <div className="cr-error fade-in">⚠ {camError}</div>}

      {/* ── Controls bar ───────────────────────────────────── */}
      <div className="cr-controls fade-up" style={{ animationDelay: '0.08s' }}>
        {/* Student selector – always visible, disabled during session */}
        <div className="cr-student-select">
          <label className="cr-select-label">Student</label>
          <select
            value={selectedStudent}
            onChange={e => setSelectedStudent(e.target.value)}
            disabled={sessionActive}
            className="cr-select"
          >
            <option value="">— Choose a student —</option>
            {students.map(s => (
              <option key={s.id} value={s.id}>{s.username}</option>
            ))}
          </select>
        </div>

        {!sessionActive ? (
          <button
            className="btn btn-primary"
            onClick={startSession}
            disabled={!selectedStudent}
          >
            ◉ Start Session
          </button>
        ) : (
          <button className="btn btn-danger" onClick={stopSession}>
            ■ End Session
          </button>
        )}

        {!speechSupported && (
          <span className="cr-warn">⚠ Speech recognition not supported</span>
        )}
      </div>

      {/* ── Three-column layout ────────────────────────────── */}
      <div className="cr-layout fade-up" style={{ animationDelay: '0.16s' }}>

        {/* LEFT: Camera + sign transcript */}
        <div className="cr-panel cr-panel--left">
          <div className="cr-panel__head">
            <span className="cr-panel__icon">◈</span>
            <span className="cr-panel__title">Student Camera</span>
          </div>

          <CameraFeed videoRef={videoRef} canvasRef={canvasRef} active={active} />

          {/* Interim speech banner */}
          {interimCaption && (
            <div className="cr-interim">
              <span className="cr-interim__label">Teacher saying:</span>
              <span className="cr-interim__text">{interimCaption}</span>
            </div>
          )}

          {!sessionActive && (
            <div className="cr-cam-placeholder">
              {selectedStudent
                ? 'Press Start Session to begin'
                : 'Choose a student first'}
            </div>
          )}
        </div>

        {/* CENTRE: Big current sign display */}
        <div className="cr-panel cr-panel--centre">
          <div className="cr-panel__head">
            <span className="cr-panel__icon">◎</span>
            <span className="cr-panel__title">Current Sign</span>
          </div>

          <div className="cr-sign-stage">
            {currentSign ? (
              <>
                <div className="cr-sign-word fade-in">{currentSign}</div>
                <div className="cr-sign-sub">Detected sign</div>
              </>
            ) : (
              <div className="cr-sign-empty">
                {sessionActive ? 'Waiting for sign…' : 'No active session'}
              </div>
            )}
          </div>

          {/* Teacher speech current caption */}
          <div className={`cr-caption-box ${interimCaption ? 'cr-caption-box--active' : ''}`}>
            {interimCaption
              ? <p className="cr-caption-text">{interimCaption}</p>
              : <p className="cr-caption-placeholder">
                  {speechActive ? '🎤 Listening…' : 'Teacher speech caption appears here'}
                </p>
            }
          </div>
        </div>

        {/* RIGHT: Chat box */}
        <div className="cr-panel cr-panel--chat">
          <div className="cr-panel__head">
            <span className="cr-panel__icon">⊕</span>
            <span className="cr-panel__title">
              Session Chat
              {selectedStudentName && (
                <span className="cr-chat-partner"> · {selectedStudentName}</span>
              )}
            </span>
          </div>

          {/* Messages */}
          <div className="cr-messages">
            {chatMessages.length === 0 && (
              <div className="cr-messages__empty">
                Messages will appear here once the session starts
              </div>
            )}
            {chatMessages.map(msg => (
              <div key={msg.id} className={`cr-msg cr-msg--${msg.role}`}>
                <div className="cr-msg__bubble">
                  <span className="cr-msg__text">{msg.text}</span>
                </div>
                <div className="cr-msg__meta">
                  <span className="cr-msg__role">
                    {msg.role === 'teacher' ? '◎ Teacher' : '◈ Student'}
                  </span>
                  <span className="cr-msg__time">{msg.time}</span>
                </div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          {/* Input area — teacher types */}
          <div className="cr-chat-input">
            <input
              type="text"
              placeholder={sessionActive ? 'Teacher: type a message…' : 'Start session to chat'}
              value={teacherInput}
              onChange={e => setTeacherInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') { e.preventDefault(); handleTeacherSend(); }
              }}
              disabled={!sessionActive}
              className="cr-chat-input__field"
            />
            <button
              className="btn btn-primary cr-chat-input__send"
              onClick={handleTeacherSend}
              disabled={!sessionActive || !teacherInput.trim()}
            >
              ↑
            </button>
          </div>

          {/* Student manual input */}
          <div className="cr-chat-input cr-chat-input--student">
            <input
              type="text"
              placeholder="Student: type a message…"
              onKeyDown={handleStudentType}
              disabled={!sessionActive}
              className="cr-chat-input__field"
            />
          </div>
        </div>

      </div>
    </div>
  );
}
