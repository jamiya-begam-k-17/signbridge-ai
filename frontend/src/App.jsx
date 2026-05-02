// ============================================================
// App.jsx – Root component
// ============================================================

import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { AssistiveVoiceProvider } from './context/AssistiveVoiceContext';
import Navbar     from './components/Navbar';
import Home       from './pages/Home';
import Detect     from './pages/Detect';
import Translate  from './pages/Translate';
import Classroom  from './pages/Classroom';
import History    from './pages/History';
import Assistive  from './pages/Assistive';
import Login      from './pages/Login';
import Register   from './pages/Register';
import { checkHealth } from './services/api';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center',
      justifyContent: 'center', color: 'var(--text-secondary)',
      fontFamily: 'var(--font-display)'
    }}>
      Loading…
    </div>
  );
  return user ? children : <Navigate to="/login" />;
}

function AppContent() {
  const [apiHealthy, setApiHealthy] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const poll = async () => {
      try {
        const data = await checkHealth();
        if (isMounted) setApiHealthy(data.status === 'healthy' && data.model_loaded);
      } catch {
        if (isMounted) setApiHealthy(false);
      }
    };
    poll();
    const id = setInterval(poll, 15_000);
    return () => { isMounted = false; clearInterval(id); };
  }, []);

  return (
    // AssistiveVoiceProvider must be inside BrowserRouter so it can use useNavigate
    <AssistiveVoiceProvider>
      <Navbar apiHealthy={apiHealthy} />
      <Routes>
        <Route path="/login"     element={<Login />} />
        <Route path="/register"  element={<Register />} />
        <Route path="/"          element={<ProtectedRoute><Home apiHealthy={apiHealthy} /></ProtectedRoute>} />
        <Route path="/detect"    element={<ProtectedRoute><Detect /></ProtectedRoute>} />
        <Route path="/translate" element={<ProtectedRoute><Translate /></ProtectedRoute>} />
        <Route path="/classroom" element={<ProtectedRoute><Classroom /></ProtectedRoute>} />
        <Route path="/history"   element={<ProtectedRoute><History /></ProtectedRoute>} />
        <Route path="/assistive" element={<ProtectedRoute><Assistive /></ProtectedRoute>} />
      </Routes>
    </AssistiveVoiceProvider>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
