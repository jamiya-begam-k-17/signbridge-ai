// ============================================================
// Classroom.jsx – redesigned with smaller feature modules
// ============================================================

import { useState, useEffect, useRef, useCallback } from 'react';
import { useCamera } from '../hooks/useCamera';
import { useSpeech } from '../hooks/useSpeech';
import { useAssistiveVoice } from '../context/AssistiveVoiceContext';
import { predictSign, getUsers, createConversation, sendMessage } from '../services/api';
import SignRecognitionPanel from '../components/classroom/SignRecognitionPanel';
import SpeechTranslationPanel from '../components/classroom/SpeechTranslationPanel';
import ClassroomChatPanel from '../components/classroom/ClassroomChatPanel';
import './Classroom.css';

const PREDICT_INTERVAL_MS = 1000;

export default function Classroom() {
  const { videoRef, canvasRef, active, error: camError, startCamera, stopCamera, captureFrame } = useCamera();
  const { speak } = useSpeech();
  const { enableCommands, disableCommands } = useAssistiveVoice();

  const [students, setStudents] = useState([]);
  const [selectedStudent, setSelectedStudent] = useState('');
  const [sessionActive, setSessionActive] = useState(false);
  const [convId, setConvId] = useState(null);
  const [currentSign, setCurrentSign] = useState('');
  const [signHistory, setSignHistory] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);
  const [teacherInput, setTeacherInput] = useState('');
  const [studentInput, setStudentInput] = useState('');
  const [chatOpen, setChatOpen] = useState(false);
  const [speechMode, setSpeechMode] = useState('lecture');
  const [pushToTalkActive, setPushToTalkActive] = useState(false);
  const [finalCaption, setFinalCaption] = useState('');
  const [speechActive, setSpeechActive] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [interimCaption, setInterimCaption] = useState('');

  const chatEndRef = useRef(null);
  const intervalRef = useRef(null);
  const lastSignRef = useRef('');
  const recognitionRef = useRef(null);
  const speechActiveRef = useRef(false);

  useEffect(() => {
    getUsers()
      .then(setStudents)
      .catch((err) => console.error('Could not load students', err));
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  useEffect(() => {
    speechActiveRef.current = speechActive;
  }, [speechActive]);

  const stopSpeechRecognition = useCallback(() => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
    } catch (error) {
      console.warn('Could not stop speech recognition:', error);
    }
    setSpeechActive(false);
    speechActiveRef.current = false;
  }, []);

  const addMessage = useCallback((role, text, isSign = false) => {
    setChatMessages((prev) => [...prev, {
      id: Date.now() + Math.random(),
      role,
      text,
      isSign,
      time: new Date().toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      }),
    }]);
  }, []);

  const startSpeechRecognition = useCallback(() => {
    if (!recognitionRef.current || speechActiveRef.current) return;
    try {
      recognitionRef.current.start();
      setSpeechActive(true);
      speechActiveRef.current = true;
    } catch (err) {
      console.warn('Could not start speech recognition:', err);
    }
  }, []);

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setSpeechSupported(false);
      return;
    }

    setSpeechSupported(true);
    const rec = new SR();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = 'en-US';

    rec.onresult = (event) => {
      let interim = '';
      let final = '';
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) final += transcript;
        else interim += transcript;
      }

      const filterKeyword = (text) => {
        if (speechMode !== 'lecture') return text.trim();
        return text.replace(/capture image/gi, '').trim();
      };

      const interimText = filterKeyword(interim);
      const finalText = filterKeyword(final);
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

    rec.onerror = (e) => {
      if (e.error === 'no-speech' || e.error === 'aborted') return;
      console.warn('Speech error:', e.error);
    };

    rec.onend = () => {
      if (speechActiveRef.current) {
        try {
          rec.start();
        } catch (error) {
          console.warn('Could not restart speech recognition:', error);
        }
      }
    };

    recognitionRef.current = rec;
    return () => {
      rec.onend = null;
      try {
        rec.stop();
      } catch (_) {}
    };
  }, [addMessage, convId, speechMode]);

  const runSignPrediction = useCallback(async () => {
    if (!active) return;
    try {
      const blob = await captureFrame();
      if (!blob) return;
      const result = await predictSign(blob);
      const word = result.prediction;

      if (word && word !== 'No hand detected') {
        setCurrentSign(word);
        if (word !== lastSignRef.current) {
          lastSignRef.current = word;
          speak(word);
          addMessage('student', word, true);
          setSignHistory((prev) => [...prev, word].slice(-12));
          if (convId) {
            sendMessage(convId, `[Student Sign] ${word}`).catch(() => {});
          }
        }
      } else {
        setCurrentSign('');
      }
    } catch (error) {
      console.warn('Could not run sign prediction:', error);
    }
  }, [active, addMessage, captureFrame, convId, speak]);

  const startSession = useCallback(async () => {
    if (!selectedStudent) return;
    disableCommands();
    try {
      const { conversation: conv } = await createConversation(parseInt(selectedStudent, 10));
      setConvId(conv.id);
    } catch (e) {
      console.error('Could not create conversation', e);
    }

    await startCamera();
    setSessionActive(true);
    setChatMessages([]);
    setSignHistory([]);
    setFinalCaption('');
    setInterimCaption('');
    setPushToTalkActive(false);
    lastSignRef.current = '';
  }, [disableCommands, selectedStudent, startCamera]);

  const startLectureSpeaking = () => {
    if (!sessionActive || !speechSupported || speechMode !== 'lecture') return;
    startSpeechRecognition();
  };

  const pauseLectureSpeaking = () => {
    if (!speechSupported) return;
    stopSpeechRecognition();
  };

  const startPushToTalk = () => {
    if (!sessionActive || !speechSupported || speechMode !== 'discussion') return;
    setPushToTalkActive(true);
    startSpeechRecognition();
  };

  const stopPushToTalk = () => {
    if (!speechSupported) return;
    setPushToTalkActive(false);
    stopSpeechRecognition();
  };

  const stopSession = useCallback(() => {
    clearInterval(intervalRef.current);
    stopCamera();
    stopSpeechRecognition();
    setSessionActive(false);
    setCurrentSign('');
    setSignHistory([]);
    setInterimCaption('');
    setFinalCaption('');
    setPushToTalkActive(false);
    setConvId(null);
    enableCommands();
  }, [enableCommands, stopCamera, stopSpeechRecognition]);

  useEffect(() => {
    if (active && sessionActive) {
      intervalRef.current = setInterval(runSignPrediction, PREDICT_INTERVAL_MS);
    }
    return () => clearInterval(intervalRef.current);
  }, [active, runSignPrediction, sessionActive]);

  const handleTeacherSend = () => {
    if (!teacherInput.trim()) return;
    const text = teacherInput.trim();
    setTeacherInput('');
    addMessage('teacher', text);
    if (convId) {
      sendMessage(convId, `[Teacher] ${text}`).catch(() => {});
    }
  };

  const handleStudentSend = () => {
    if (!studentInput.trim()) return;
    const text = studentInput.trim();
    setStudentInput('');
    addMessage('student', text);
    if (convId) {
      sendMessage(convId, `[Student] ${text}`).catch(() => {});
    }
  };

  const selectedStudentName = students.find((s) => String(s.id) === String(selectedStudent))?.username;

  const formatSignWord = (word) => {
    if (!word) return '';
    const normalized = String(word).trim();
    if (normalized.length <= 12) return normalized;
    const chunks = normalized.match(/.{1,10}/g) || [normalized];
    return chunks.join('_');
  };

  return (
    <div className="cr-page">
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

      <div className="cr-controls fade-up" style={{ animationDelay: '0.06s' }}>
        <div className="cr-student-select">
          <label className="cr-select-label">Student</label>
          <select
            value={selectedStudent}
            onChange={(e) => setSelectedStudent(e.target.value)}
            disabled={sessionActive}
            className="cr-select"
          >
            <option value="">— Choose a student —</option>
            {students.map((s) => (
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

      <div className="cr-layout fade-up" style={{ animationDelay: '0.14s' }}>
        <SignRecognitionPanel
          videoRef={videoRef}
          canvasRef={canvasRef}
          active={active}
          sessionActive={sessionActive}
          currentSign={currentSign}
          signHistory={signHistory}
          formatSignWord={formatSignWord}
          placeholderText={selectedStudent ? 'Press Start Session to begin' : 'Choose a student first'}
        />

        <SpeechTranslationPanel
          speechMode={speechMode}
          setSpeechMode={setSpeechMode}
          sessionActive={sessionActive}
          speechSupported={speechSupported}
          speechActive={speechActive}
          pushToTalkActive={pushToTalkActive}
          interimCaption={interimCaption}
          finalCaption={finalCaption}
          onStartLecture={startLectureSpeaking}
          onPauseLecture={pauseLectureSpeaking}
          onStartPushToTalk={startPushToTalk}
          onStopPushToTalk={stopPushToTalk}
        />
      </div>

      <ClassroomChatPanel
        chatOpen={chatOpen}
        setChatOpen={setChatOpen}
        selectedStudentName={selectedStudentName}
        sessionActive={sessionActive}
        chatMessages={chatMessages}
        teacherInput={teacherInput}
        setTeacherInput={setTeacherInput}
        studentInput={studentInput}
        setStudentInput={setStudentInput}
        onTeacherSend={handleTeacherSend}
        onStudentSend={handleStudentSend}
        chatEndRef={chatEndRef}
      />
    </div>
  );
}
