// ============================================================
// App.jsx – Root component
// Sets up routing + API health polling
// ============================================================

import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar    from './components/Navbar';
import Home      from './pages/Home';
import Detect    from './pages/Detect';
import Translate from './pages/Translate';
import Classroom from './pages/Classroom';
import { checkHealth } from './services/api';

export default function App() {
  const [apiHealthy, setApiHealthy] = useState(false);

  // Poll backend health every 15 seconds
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
    <BrowserRouter>
      <Navbar apiHealthy={apiHealthy} />
      <Routes>
        <Route path="/"          element={<Home apiHealthy={apiHealthy} />} />
        <Route path="/detect"    element={<Detect />} />
        <Route path="/translate" element={<Translate />} />
        <Route path="/classroom" element={<Classroom />} />
      </Routes>
    </BrowserRouter>
  );
}