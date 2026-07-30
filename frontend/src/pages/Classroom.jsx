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
import { useAuth } from '../context/AuthContext';
import { useAssistiveVoice } from '../context/AssistiveVoiceContext';
import { predictSign, getUsers, createConversation, sendMessage} from '../services/api';
// import { predictSign, getUsers, createConversation, sendMessage, verifySpeaker } from '../services/api';
import CameraFeed from '../components/CameraFeed';
import './Classroom.css';

const PREDICT_INTERVAL_MS = 1000;

export default function Classroom() {
  const { videoRef, canvasRef, active, error: camError, startCamera, stopCamera, captureFrame } =
    useCamera();
  const { user } = useAuth();
  const { speak } = useSpeech();
  const { enableCommands, disableCommands } = useAssistiveVoice();

  // Students
  const [students,        setStudents]       = useState([]);
  const [selectedStudent, setSelectedStudent] = useState('');

  // Session
  const [sessionActive,   setSessionActive]  = useState(false);
  const [convId,          setConvId]         = useState(null);
  const [teacherVoiceSample, setTeacherVoiceSample] = useState(null);

  // Sign detection
  const [currentSign,     setCurrentSign]    = useState('');
  const [signHistory,     setSignHistory]    = useState([]);

  // Chat: { id, role: 'student'|'teacher', text, time }
  const [chatMessages,    setChatMessages]   = useState([]);
  const [teacherInput,    setTeacherInput]   = useState('');
  const [studentInput,    setStudentInput]   = useState('');
  const [chatOpen,        setChatOpen]        = useState(false);
  const [speechMode,      setSpeechMode]      = useState('lecture');
  const [speechPaused,    setSpeechPaused]    = useState(false);
  const [pushToTalkActive,setPushToTalkActive]= useState(false);
  const [finalCaption,    setFinalCaption]    = useState('');
  const chatEndRef = useRef(null);

  // Speech
  const [speechActive,    setSpeechActive]   = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [interimCaption,  setInterimCaption]  = useState('');

  const intervalRef    = useRef(null);
  const verificationIntervalRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const lastSignRef    = useRef('');
  const recognitionRef = useRef(null);

  // On mount, ensure global commands are enabled if user navigates away
  // without stopping a session.
  // useEffect(() => {
  //   return () => {
  //     enableCommands();
  //   };
  // }, [enableCommands]);


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

  const stopSpeechRecognition = useCallback(() => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
    } catch (_) {}
    setSpeechActive(false);
  }, []);

  const handleVerificationAndTranscription = useCallback(async () => {
    if (speechMode !== 'lecture' || !user?.voice_embedding) {
      // In discussion mode or if teacher has no voice embedding, transcribe directly.
      if (recognitionRef.current && !speechActive) {
        try {
          recognitionRef.current.start();
          setSpeechActive(true);
        } catch (_) {}
      }
      return;
    }

    // In lecture mode, perform verification
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorderRef.current = new MediaRecorder(stream);
    const audioChunks = [];
    mediaRecorderRef.current.ondataavailable = event => audioChunks.push(event.data);
    mediaRecorderRef.current.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
      try {
        const { verified } = await verifySpeaker(audioBlob);
        if (verified) {
          if (recognitionRef.current && !speechActive) recognitionRef.current.start();
          setSpeechActive(true);
        } else {
          console.warn("Speaker verification failed. Not transcribing.");
        }
      } catch (error) {
        console.error("Error during speaker verification:", error);
      }
    };
    mediaRecorderRef.current.start();
    setTimeout(() => mediaRecorderRef.current.stop(), 1500); // Verify with a 1.5s clip
  }, [speechMode, user, speechActive]);
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

      const filterKeyword = (text) => {
        if (speechMode !== 'lecture') return text.trim();
        // Prevents "capture image" from showing in chat, even though global
        // command is disabled.
        return text.replace(/capture image/gi, '').trim();
      };

      const interimText = filterKeyword(interim);
      const finalText   = filterKeyword(final);
      const captionRole = speechMode === 'discussion' ? 'student' : 'teacher';

      setInterimCaption(interimText || finalText);
      if (finalText) {
        setFinalCaption(finalText);
        setInterimCaption('');
        addMessage(captionRole, finalText);
        if (convId) {
          sendMessage(convId, `[${captionRole === 'teacher' ? 'Teacher' : 'Student'}] ${finalText}`).catch(() => {});
        }
      }
    };
    rec.onerror = e => console.warn('Speech error:', e.error);
    recognitionRef.current = rec;
    return () => rec.stop();
  }, [convId, speechMode, stopSpeechRecognition]);

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
          setSignHistory(prev => [...prev, word].slice(-12));
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
    disableCommands(); // Disable global voice commands
    try {
      // Assuming createConversation returns teacher's voice embedding
      const { conversation: conv, teacher_embedding } = await createConversation(parseInt(selectedStudent));
      setConvId(conv.id);
      setTeacherVoiceSample(teacher_embedding); // Store for verification
    } catch (e) {
      console.error('Could not create conversation', e);
    }
    await startCamera();
    setSessionActive(true);
    setChatMessages([]);
    setSignHistory([]);
    setFinalCaption('');
    lastSignRef.current = '';

  }, [selectedStudent, startCamera, disableCommands]);

  const startLectureSpeaking = () => {
    if (!sessionActive || !speechSupported || speechMode !== 'lecture') return;
    setSpeechPaused(false);
    // handleVerificationAndTranscription will start recognition, so we don't
    // need to call it separately here.
    handleVerificationAndTranscription();
  };

  const pauseLectureSpeaking = () => {
    if (!speechSupported) return;
    stopSpeechRecognition();
    setSpeechPaused(true);
  };

  const endSpeechSession = () => {
    stopSpeechRecognition();
    setSpeechPaused(false);
    setPushToTalkActive(false);
    setInterimCaption('');
    setFinalCaption('');
  };

  const startPushToTalk = () => {
    if (!sessionActive || !speechSupported || speechMode !== 'discussion') return;
    setPushToTalkActive(true);
    if (recognitionRef.current && !speechActive) {
      try {
        recognitionRef.current.start();
        setSpeechActive(true);
      } catch (_) {}
    }
  };

  const stopPushToTalk = () => {
    if (!speechSupported) return;
    setPushToTalkActive(false);
    stopSpeechRecognition();
  };

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
    setSignHistory([]);
    setInterimCaption('');
    setFinalCaption('');
    setSpeechPaused(false);
    setPushToTalkActive(false);
    setConvId(null);
    setTeacherVoiceSample(null);
    enableCommands(); // Re-enable global voice commands
  }, [stopCamera, speechActive, enableCommands]);

  // Prediction interval
  useEffect(() => {
    if (active && sessionActive) {
      intervalRef.current = setInterval(runSignPrediction, PREDICT_INTERVAL_MS);
    }
    return () => clearInterval(intervalRef.current);
  }, [active, sessionActive, runSignPrediction, handleVerificationAndTranscription]);

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

  const formatSignWord = (word) => {
    if (!word) return '';
    const normalized = String(word).trim();
    if (normalized.length <= 12) return normalized;
    const chunks = normalized.match(/.{1,10}/g) || [normalized];
    return chunks.join('_');
  };

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
            Choose a student, start the session, and communicate through sign language & live captions.
          </p>
        </div>
      </div>

      {camError && <div className="banner-error fade-in">⚠ {camError}</div>}

      {/* ── Controls bar ─────────────────────────────────────── */}
      <div className="cr-controls fade-up" style={{ animationDelay: '0.06s' }}>
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

      {/* ── Two-panel classroom layout ────────────────────────── */}
      <div className="cr-layout fade-up" style={{ animationDelay: '0.14s' }}>

        {/* LEFT: Sign Language Recognition */}
        <section className="cr-panel cr-panel--left">
          <div className="cr-panel-head">
            <span className="cr-panel-icon">◈</span>
            <span className="cr-panel-title">Sign Language Recognition</span>
          </div>

          <div className="cr-recognition-grid">
            <div className="cr-recognition-video">
              <CameraFeed videoRef={videoRef} canvasRef={canvasRef} active={active} />
              {!sessionActive && (
                <div className="cr-cam-placeholder">
                  {selectedStudent ? 'Press Start Session to begin' : 'Choose a student first'}
                </div>
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

        {/* RIGHT: Speech Translation */}
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
                onClick={startLectureSpeaking}
              >
                Start Speaking
              </button>
              <button
                type="button"
                className="btn btn-ghost cr-speech-action"
                disabled={!sessionActive || !speechSupported || !speechActive}
                onClick={pauseLectureSpeaking}
              >
                Pause
              </button>
            </div>
          ) : (
            <div className="cr-ptt-panel">
              <button
                type="button"
                className={`cr-ptt-button ${pushToTalkActive ? 'cr-ptt-button--active' : ''}`}
                onMouseDown={startPushToTalk}
                onMouseUp={stopPushToTalk}
                onMouseLeave={pushToTalkActive ? stopPushToTalk : undefined}
                onTouchStart={startPushToTalk}
                onTouchEnd={stopPushToTalk}
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
            <div className="cr-translation-history__heading">Session captions</div>
            <div className="cr-translation-history__item">
              {finalCaption ? finalCaption : 'Finalized captions appear here after each detected phrase.'}
            </div>
          </div>
        </section>

      </div>

      <button
        className={`cr-chat-toggle${chatOpen ? ' cr-chat-toggle--open' : ''}`}
        onClick={() => setChatOpen(prev => !prev)}
        aria-expanded={chatOpen}
        aria-controls="cr-chat-panel"
        type="button"
      >
        <span className="cr-chat-toggle__icon">💬</span>
        <span className="cr-chat-toggle__label">
          {chatOpen ? 'Hide Classroom Chat' : 'Open Classroom Chat'}
        </span>
      </button>

      <aside
        id="cr-chat-panel"
        className={`cr-chat-widget${chatOpen ? ' cr-chat-widget--open' : ''}`}
        aria-hidden={!chatOpen}
      >
        <div className="cr-chat-header">
          <div>
            <p className="cr-chat-title">Classroom Conversation</p>
          </div>
          <button
            className="cr-chat-close"
            onClick={() => setChatOpen(false)}
            type="button"
            aria-label="Close chat panel"
          >
            ✕
          </button>
        </div>

        <div className="cr-chat-status">
          {selectedStudentName ? `Active student: ${selectedStudentName}` : 'Select a student to begin session.'}
        </div>

        <div className="cr-messages cr-chat-messages">
          {chatMessages.length === 0 && (
            <div className="cr-messages-empty">
              {sessionActive
                ? 'Start signing or speaking — classroom conversation will appear here.'
                : 'Session messages will appear here.'}
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

        <div className="cr-input-stack">
          <div className="cr-input-group">
            <span className="cr-input-label">Teacher</span>
            <div className="cr-input-row">
              <input
                type="text"
                className="cr-input-field"
                placeholder={sessionActive ? 'Type a teacher message…' : 'Start session to chat'}
                value={teacherInput}
                onChange={e => setTeacherInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleTeacherSend(); } }}
                disabled={!sessionActive}
              />
              <button
                className="btn btn-primary cr-send-btn"
                onClick={handleTeacherSend}
                disabled={!sessionActive || !teacherInput.trim()}
                type="button"
              >↑</button>
            </div>
          </div>

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
                type="button"
              >↑</button>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
