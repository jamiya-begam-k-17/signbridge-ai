import { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useAssistiveVoice } from '../context/AssistiveVoiceContext';
import './Navbar.css';

const NAV_LINKS = [
  { to: '/',           label: 'Home'        },
  { to: '/detect',     label: 'Detect'      },
  { to: '/translate',  label: 'Translate'   },
  { to: '/classroom',  label: 'Classroom'   },
  { to: '/history',    label: 'History'     },
  { to: '/assistive',  label: '◉ Vision Assist' },
];

export default function Navbar({ apiHealthy }) {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { voiceActive } = useAssistiveVoice();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => { setMenuOpen(false); }, [location]);

  return (
    <nav className={`navbar ${scrolled ? 'navbar--scrolled' : ''}`}>
      <div className="navbar__inner">
        {/* Logo */}
        <NavLink to="/" className="navbar__logo">
          <span className="navbar__logo-icon">✦</span>
          <span>Sign<span className="text-accent">Bridge</span></span>
        </NavLink>

        {/* Desktop links */}
        <div className="navbar__links">
          {user && NAV_LINKS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `navbar__link ${isActive ? 'navbar__link--active' : ''} ${to === '/assistive' ? 'navbar__link--assistive' : ''}`}
              end={to === '/'}
            >
              {label}
            </NavLink>
          ))}
        </div>

        {/* Right */}
        <div className="navbar__right">
          {user && (
            <span className="navbar__user">{user.username}</span>
          )}

          {/* Voice indicator */}
          {voiceActive && (
            <span className="navbar__voice-dot" title="Voice commands active" aria-label="Voice commands listening">
              🎙
            </span>
          )}

          {/* Theme toggle */}
          <button
            className="navbar__theme-btn"
            onClick={toggleTheme}
            aria-label="Toggle theme"
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? '☀' : '◑'}
          </button>

          <span className={`badge ${apiHealthy ? 'badge-live' : 'badge-offline'}`}>
            {apiHealthy ? 'Online' : 'Offline'}
          </span>

          {user && (
            <button className="btn btn-ghost navbar__logout" onClick={logout}>
              Logout
            </button>
          )}

          <button
            className="navbar__hamburger"
            onClick={() => setMenuOpen(v => !v)}
            aria-label="Toggle menu"
          >
            <span /><span /><span />
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && user && (
        <div className="navbar__mobile-menu fade-in">
          {NAV_LINKS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `navbar__mobile-link ${isActive ? 'navbar__mobile-link--active' : ''}`}
              end={to === '/'}
            >
              {label}
            </NavLink>
          ))}
          <div className="navbar__mobile-actions">
            <button className="navbar__theme-btn" onClick={toggleTheme}>
              {theme === 'dark' ? '☀ Light Mode' : '◑ Dark Mode'}
            </button>
            <button className="btn btn-danger" onClick={logout}>Logout</button>
          </div>
        </div>
      )}
    </nav>
  );
}
