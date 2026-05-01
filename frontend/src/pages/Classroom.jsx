// ============================================================
// Classroom.jsx – Redesigned
// Layout: [Camera Panel LEFT] | [Current Sign CENTRE] | [Chat RIGHT]
// Flow:
//   1. Choose student from dropdown (required before starting)
//   2. Start session → camera opens, sign detection begins
//   3. Detected signs appear in chat as student messages
//   4. Teacher speech (mic) appears as teacher messages
//   5. Teacher and student can also type manually
//   6. End session → conversation saved to DB
// ============================================================

import { useState, useEffect, useRef, useCallback } from 'react';
import { useCamera }  from '../hooks/useCamera';
import { useSpeech }  from '../hooks/useSpeech';
import { predictSign, getUsers, createConversation, sendMessage } from '../services/api';
import CameraFeed from '../components/CameraFeed';
import './Classroom.css';

const PREDICT_INTERVAL_MS = 1000;

export default function Classroom() {
  const { videoRef, canvasRef, active, error: camError, startCamera, stopCamera, captureFrame } =
    useCamera();
  const { speak } = useSpeech();

  // Students
  const [students,        setStudents]       = useState([]);
  const [selectedStudent, setSelectedStudent] = useState('');

  // Session
  const [sessionActive,   setSessionActive]  = useState(false);
  const [convId,          setConvId]         = useState(null);

  // Sign detection
  const [currentSign,     setCurrentSign]    = useState('');

  // Chat: { id, role: 'student'|'teacher', text, time }
  const [chatMessages,    setChatMessages]   = useState([]);
  const [teacherInput,    setTeacherInput]   = useState('');
  const [studentInput,    setStudentInput]   = useState('');
  const chatEndRef = useRef(null);

  // Speech
  const [speechActive,    setSpeechActive]   = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [interimCaption,  setInterimCaption]  = useState('');

  const intervalRef    = useRef(null);
  const lastSignRef    = useRef('');
  const recognitionRef = useRef(null);

  // Load students
  useEffect(() => {
    getUsers()
      .then(setStudents)
      .catch(err => console.error('Could not load students', err));
  }, []);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // Speech recognition setup
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
        if (convId) {
          sendMessage(convId, `[Teacher] ${text}`).catch(() => {});
        }
      }
    };
    rec.onerror = e => console.warn('Speech error:', e.error);
    recognitionRef.current = rec;
    return () => rec.stop();
  }, [convId]);

  // Sign prediction loop
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
          speak(word);
          addMessage('student', word, true);
          if (convId) {
            sendMessage(convId, `[Student Sign] ${word}`).catch(() => {});
          }
        }
      } else {
        setCurrentSign('');
      }
    } catch (_) {}
  }, [active, captureFrame, speak, convId]);

  // Start session
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

    if (speechSupported && recognitionRef.current) {
      try { recognitionRef.current.start(); setSpeechActive(true); }
      catch (_) {}
    }
  }, [selectedStudent, startCamera, speechSupported]);

  // Stop session
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

  // Prediction interval
  useEffect(() => {
    if (active && sessionActive) {
      intervalRef.current = setInterval(runSignPrediction, PREDICT_INTERVAL_MS);
    }
    return () => clearInterval(intervalRef.current);
  }, [active, sessionActive, runSignPrediction]);

  // Helper: add message to chat
  const addMessage = (role, text, isSign = false) => {
    setChatMessages(prev => [...prev, {
      id: Date.now() + Math.random(),
      role,
      text,
      isSign,
      time: new Date().toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
      })
    }]);
  };

  // Teacher send (typed)
  const handleTeacherSend = async () => {
    if (!teacherInput.trim()) return;
    const text = teacherInput.trim();
    setTeacherInput('');
    addMessage('teacher', text);
    if (convId) {
      sendMessage(convId, `[Teacher] ${text}`).catch(() => {});
    }
  };

  // Student send (typed)
  const handleStudentSend = async () => {
    if (!studentInput.trim()) return;
    const text = studentInput.trim();
    setStudentInput('');
    addMessage('student', text);
    if (convId) {
      sendMessage(convId, `[Student] ${text}`).catch(() => {});
    }
  };

  const selectedStudentName = students.find(
    s => String(s.id) === String(selectedStudent)
  )?.username;

  return (
    <div className="cr-page">

      {/* ── Header ───────────────────────────────────────────── */}
      <div className="cr-header fade-up">
        <div className="cr-header-row">
          <div className="cr-header-left">
            <h1 className="page-title">Classroom</h1>
            {sessionActive && (
              <span className="badge badge-live">LIVE · {selectedStudentName}</span>
            )}
          </div>
          <p className="page-sub">
            Choose a student, start the session, and communicate through sign language.
          </p>
        </div>
      </div>

      {camError && <div className="banner-error fade-in">⚠ {camError}</div>}

      {/* ── Controls bar ─────────────────────────────────────── */}
      <div className="cr-controls card fade-up" style={{ animationDelay: '0.06s' }}>
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

        <div className="cr-controls-actions">
          {!speechSupported && (
            <span className="cr-warn">⚠ Speech recognition unavailable</span>
          )}
          {!sessionActive ? (
            <button
              className="btn btn-primary"
              onClick={startSession}
              disabled={!selectedStudent}
              title={!selectedStudent ? 'Select a student first' : ''}
            >
              ▶ Start Session
            </button>
          ) : (
            <button className="btn btn-danger" onClick={stopSession}>
              ■ End Session
            </button>
          )}
        </div>
      </div>

      {/* ── Three-column layout ──────────────────────────────── */}
      <div className="cr-layout fade-up" style={{ animationDelay: '0.14s' }}>

        {/* LEFT: Camera */}
        <div className="cr-panel">
          <div className="cr-panel-head">
            <span className="cr-panel-icon">◈</span>
            <span className="cr-panel-title">Student Camera</span>
          </div>

          <CameraFeed videoRef={videoRef} canvasRef={canvasRef} active={active} />

          {!sessionActive && (
            <div className="cr-cam-placeholder">
              {selectedStudent ? 'Press Start Session to begin' : 'Choose a student first'}
            </div>
          )}

          {interimCaption && (
            <div className="cr-interim fade-in">
              <span className="cr-interim-label">Teacher saying</span>
              <span className="cr-interim-text">{interimCaption}</span>
            </div>
          )}
        </div>

        {/* CENTRE: Current sign (main display) */}
        <div className="cr-panel">
          <div className="cr-panel-head">
            <span className="cr-panel-icon">◎</span>
            <span className="cr-panel-title">Current Sign</span>
          </div>

          <div className="cr-sign-stage">
            {currentSign ? (
              <>
                <div className="cr-sign-word fade-in">{currentSign}</div>
                <div className="cr-sign-label">Detected Sign</div>
              </>
            ) : (
              <div className="cr-sign-empty">
                {sessionActive ? 'Waiting for sign…' : 'No active session'}
              </div>
            )}
          </div>

          {/* Speech caption box */}
          <div className={`cr-caption-box ${interimCaption ? 'cr-caption-box--active' : ''}`}>
            {interimCaption
              ? <p className="cr-caption-text">{interimCaption}</p>
              : <p className="cr-caption-placeholder">
                  {speechActive ? '🎤 Listening for teacher speech…' : 'Teacher speech caption will appear here'}
                </p>
            }
          </div>
        </div>

        {/* RIGHT: Chat */}
        <div className="cr-panel cr-panel--chat">
          <div className="cr-panel-head">
            <span className="cr-panel-icon">⊕</span>
            <span className="cr-panel-title">
              Session Chat
              {selectedStudentName && (
                <span className="cr-chat-partner"> · {selectedStudentName}</span>
              )}
            </span>
          </div>

          {/* Messages list */}
          <div className="cr-messages">
            {chatMessages.length === 0 && (
              <div className="cr-messages-empty">
                {sessionActive
                  ? 'Start signing or speaking — messages appear here'
                  : 'Session messages will appear here'}
              </div>
            )}
            {chatMessages.map(msg => (
              <div key={msg.id} className={`cr-msg cr-msg--${msg.role}`}>
                <div className="cr-msg-bubble">
                  {msg.isSign && <span className="cr-msg-sign-tag">✋ Sign</span>}
                  <span className="cr-msg-text">{msg.text}</span>
                </div>
                <div className="cr-msg-meta">
                  <span className="cr-msg-role">
                    {msg.role === 'teacher' ? '◎ Teacher' : '◈ Student'}
                  </span>
                  <span className="cr-msg-time">{msg.time}</span>
                </div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          {/* Teacher input */}
          <div className="cr-input-group">
            <span className="cr-input-label">Teacher</span>
            <div className="cr-input-row">
              <input
                type="text"
                className="cr-input-field"
                placeholder={sessionActive ? 'Type a message…' : 'Start session to chat'}
                value={teacherInput}
                onChange={e => setTeacherInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleTeacherSend(); } }}
                disabled={!sessionActive}
              />
              <button
                className="btn btn-primary cr-send-btn"
                onClick={handleTeacherSend}
                disabled={!sessionActive || !teacherInput.trim()}
              >↑</button>
            </div>
          </div>

          {/* Student input */}
          <div className="cr-input-group cr-input-group--student">
            <span className="cr-input-label">Student</span>
            <div className="cr-input-row">
              <input
                type="text"
                className="cr-input-field"
                placeholder={sessionActive ? 'Student types here…' : 'Start session to chat'}
                value={studentInput}
                onChange={e => setStudentInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleStudentSend(); } }}
                disabled={!sessionActive}
              />
              <button
                className="btn btn-ghost cr-send-btn"
                onClick={handleStudentSend}
                disabled={!sessionActive || !studentInput.trim()}
              >↑</button>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
