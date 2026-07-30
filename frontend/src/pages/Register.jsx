import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import './Auth.css';

export default function Register() {
  const [username, setUsername] = useState('');
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [role,     setRole]     = useState('student');
  const [error,    setError]    = useState('');
  const [loading,  setLoading]  = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    const result = await register(username, email, password, role);
    setLoading(false);
    if (result.success) navigate('/');
    else setError(result.error);
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <span className="auth-logo-icon">✦</span>
          Sign<span style={{ color: 'var(--accent-primary)' }}>Bridge</span>
        </div>

        <h1 className="auth-title">Create account</h1>
        <p className="auth-sub">Join SignBridge today</p>

        {error && <div className="auth-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="auth-fields">
            <div>
              <label className="auth-label">Username</label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="Choose a username"
                required
              />
            </div>
            <div>
              <label className="auth-label">Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="your@email.com"
                required
              />
            </div>
            <div>
              <label className="auth-label">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Create a password"
                required
              />
            </div>
            <div>
              <label className="auth-label">Role</label>
              <div className="auth-role-group">
                <button
                  type="button"
                  className={`auth-role-btn ${role === 'student' ? 'active' : ''}`}
                  onClick={() => setRole('student')}
                >
                  ◈ Student
                </button>
                <button
                  type="button"
                  className={`auth-role-btn ${role === 'teacher' ? 'active' : ''}`}
                  onClick={() => setRole('teacher')}
                >
                  ◎ Teacher
                </button>
              </div>
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary auth-btn"
            disabled={loading}
          >
            {loading ? 'Creating account…' : '→ Create Account'}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
// import { useState } from 'react';
// import { useAuth } from '../context/AuthContext';
// import { useNavigate, Link } from 'react-router-dom';
// // import { registerVoice } from '../services/api';
// import './Auth.css';

// const PHRASES = [
//   "The quick brown fox jumps over the lazy dog.",
//   "My voice is my passport, verify me.",
//   "SignBridge AI enhances classroom accessibility.",
//   "Real-time sign language recognition is the future.",
//   "Accessibility is a fundamental right, not a feature."
// ];

// export default function Register() {
//   const [username, setUsername] = useState('');
//   const [email,    setEmail]    = useState('');
//   const [password, setPassword] = useState('');
//   const [role,     setRole]     = useState('student');
//   const [step,     setStep]     = useState(1); // 1 for details, 2 for voice
//   const [error,    setError]    = useState('');
//   const [loading,  setLoading]  = useState(false);
//   // const [recording, setRecording] = useState(false);
//   // const [audioBlob, setAudioBlob] = useState(null);
//   // const [phrase] = useState(PHRASES[Math.floor(Math.random() * PHRASES.length)]);
//   // const mediaRecorderRef = useRef(null);
//   const { register } = useAuth();
//   const navigate = useNavigate();

//   const handleSubmit = async (e) => {
//     e.preventDefault();
//     setError('');
//     setLoading(true);
//     const result = await register(username, email, password, role);
//     setLoading(false);
//     if (result.success) navigate('/');
//     else setError(result.error);

//     // if (step === 2 && role === 'teacher') {
//     //   if (!audioBlob) {
//     //     setError('Please record your voice first.');
//     //     setLoading(false);
//     //     return;
//     //   }
//     //   try {
//     //     await registerVoice(audioBlob);
//     //     navigate('/login', { state: { message: 'Voice registered! Please log in.' } });
//     //   } catch (err) {
//     //     setError(err.message || 'Voice registration failed. Please try again.');
//     //   } finally {
//     //     setLoading(false);
//     //   }
//     //   return;
//     // }

//     // const result = await register(username, email, password, role);
//     // setLoading(false);
//     // if (result.success) {
//     //   if (role === 'teacher') {
//     //     setStep(2);
//     //     setError('');
//     //   } else {
//     //     navigate('/');
//     //   }
//     // } else {
//     //   setError(result.error);
//     // }
//   };

//   // const handleStartRecording = async () => {
//   //   try {
//   //     const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
//   //     mediaRecorderRef.current = new MediaRecorder(stream);
//   //     const audioChunks = [];
//   //     mediaRecorderRef.current.ondataavailable = event => {
//   //       audioChunks.push(event.data);
//   //     };
//   //     mediaRecorderRef.current.onstop = () => {
//   //       const blob = new Blob(audioChunks, { type: 'audio/wav' });
//   //       setAudioBlob(blob);
//   //       stream.getTracks().forEach(track => track.stop());
//   //     };
//   //     mediaRecorderRef.current.start();
//   //     setRecording(true);
//   //     setAudioBlob(null);
//   //     setError('');
//   //   } catch (err) {
//   //     setError('Could not access microphone. Please grant permission.');
//   //   }
//   // };

//   // const handleStopRecording = () => {
//   //   mediaRecorderRef.current?.stop();
//   //   setRecording(false);
//   // };

//   return (
//     <div className="auth-page">
//       <div className="auth-card">
//         <div className="auth-logo">
//           <span className="auth-logo-icon">✦</span>
//           Sign<span style={{ color: 'var(--accent-primary)' }}>Bridge</span>
//         </div>

//         <h1 className="auth-title">
//           {step === 1 ? 'Create account' : 'Register Your Voice'}
//         </h1>
//         <p className="auth-sub">Join SignBridge today</p>

//         {error && <div className="auth-error">{error}</div>}

//         <form onSubmit={handleSubmit}>
//           <div className="auth-fields">
//             <div>
//               {step === 1 ? (
//                 <>
//                   <div>
//                     <label className="auth-label">Username</label>
//                     <input type="text" value={username} onChange={e => setUsername(e.target.value)} placeholder="Choose a username" required />
//                   </div>
//                   <div>
//                     <label className="auth-label">Email</label>
//                     <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="your@email.com" required />
//                   </div>
//                   <div>
//                     <label className="auth-label">Password</label>
//                     <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Create a password" required />
//                   </div>
//                   <div>
//                     <label className="auth-label">Role</label>
//                     <div className="auth-role-group">
//                       <button type="button" className={`auth-role-btn ${role === 'student' ? 'active' : ''}`} onClick={() => setRole('student')}>◈ Student</button>
//                       <button type="button" className={`auth-role-btn ${role === 'teacher' ? 'active' : ''}`} onClick={() => setRole('teacher')}>◎ Teacher</button>
//                     </div>
//                   </div>
//                 </>
//               ) : (
//                 <div className="voice-reg">
//                   <p className="voice-reg-instr">Please read the following phrase aloud to register your voiceprint. This helps secure your account in Lecture Mode.</p>
//                   <p className="voice-reg-phrase">"{phrase}"</p>
//                   <div className="voice-reg-controls">
//                     {!recording ? (
//                       <button type="button" className="btn btn-primary" onClick={handleStartRecording} disabled={loading}>🎙️ Start Recording</button>
//                     ) : (
//                       <button type="button" className="btn btn-danger" onClick={handleStopRecording}>■ Stop Recording</button>
//                     )}
//                   </div>
//                   {audioBlob && <div className="voice-reg-feedback">✅ Voice sample captured! Click Finish to complete.</div>}
//                 </div>
//               )}
//               <label className="auth-label">Username</label>
//               <input
//                 type="text"
//                 value={username}
//                 onChange={e => setUsername(e.target.value)}
//                 placeholder="Choose a username"
//                 required
//               />
//             </div>
//             <div>
//               <label className="auth-label">Email</label>
//               <input
//                 type="email"
//                 value={email}
//                 onChange={e => setEmail(e.target.value)}
//                 placeholder="your@email.com"
//                 required
//               />
//             </div>
//             <div>
//               <label className="auth-label">Password</label>
//               <input
//                 type="password"
//                 value={password}
//                 onChange={e => setPassword(e.target.value)}
//                 placeholder="Create a password"
//                 required
//               />
//             </div>
//             <div>
//               <label className="auth-label">Role</label>
//               <div className="auth-role-group">
//                 <button
//                   type="button"
//                   className={`auth-role-btn ${role === 'student' ? 'active' : ''}`}
//                   onClick={() => setRole('student')}
//                 >
//                   ◈ Student
//                 </button>
//                 <button
//                   type="button"
//                   className={`auth-role-btn ${role === 'teacher' ? 'active' : ''}`}
//                   onClick={() => setRole('teacher')}
//                 >
//                   ◎ Teacher
//                 </button>
//               </div>
//             </div>
//           </div>

//           <button
//             type="submit"
//             className="btn btn-primary auth-btn"
//             disabled={loading || (step === 2 && !audioBlob)}
//           >
//             {loading ? (step === 1 ? 'Creating...' : 'Saving...') : (step === 1 ? `→ Next: ${role === 'teacher' ? 'Voice Setup' : 'Finish'}` : '→ Finish Registration')}
//           </button>
//         </form>

//         {step === 1 && (
//           <p className="auth-switch">
//             Already have an account? <Link to="/login">Sign in</Link>
//           </p>
//         )}
//       </div>
//     </div>
//   );
// }
