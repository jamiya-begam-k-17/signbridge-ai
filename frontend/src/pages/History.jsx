// ============================================================
// History.jsx – Teacher session history
// Shows all past conversations: with which student, at what time
// ============================================================

import { useState, useEffect } from 'react';
import { getConversations } from '../services/api';
import { useAuth } from '../context/AuthContext';
import './History.css';

export default function History() {
  const [conversations, setConversations] = useState([]);
  const [loading,       setLoading]       = useState(true);
  const [error,         setError]         = useState('');
  const [expanded,      setExpanded]      = useState(null);
  const { user } = useAuth();

  useEffect(() => {
    getConversations()
      .then(data => {
        // Sort newest first
        const sorted = [...data].sort((a, b) =>
          new Date(b.created_at || 0) - new Date(a.created_at || 0)
        );
        setConversations(sorted);
      })
      .catch(() => setError('Failed to load history'))
      .finally(() => setLoading(false));
  }, []);

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    if (isNaN(d)) return '—';
    return d.toLocaleDateString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric'
    });
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    if (isNaN(d)) return '—';
    return d.toLocaleTimeString('en-IN', {
      hour: '2-digit', minute: '2-digit'
    });
  };

  const parseMessageRole = (content) => {
    if (content?.startsWith('[Teacher]'))       return { role: 'teacher', text: content.replace('[Teacher]', '').trim() };
    if (content?.startsWith('[Student Sign]'))  return { role: 'student', text: content.replace('[Student Sign]', '').trim(), isSign: true };
    if (content?.startsWith('[Student]'))       return { role: 'student', text: content.replace('[Student]', '').trim() };
    return { role: 'student', text: content };
  };

  return (
    <div className="hist-page">
      <div className="hist-header fade-up">
        <h1 className="hist-title">Session History</h1>
        <p className="hist-sub">
          All past classroom sessions — who you taught, when, and what was said.
        </p>
      </div>

      {loading && (
        <div className="hist-loading fade-in">
          <div className="hist-spinner" />
          Loading sessions…
        </div>
      )}
      {error && <div className="hist-error fade-in">⚠ {error}</div>}

      {!loading && !error && conversations.length === 0 && (
        <div className="hist-empty fade-in">
          <div className="hist-empty__icon">◈</div>
          <p>No sessions yet</p>
          <span>Start a classroom session to see history here</span>
        </div>
      )}

      <div className="hist-list fade-up" style={{ animationDelay: '0.1s' }}>
        {conversations.map((conv, i) => {
          const isOpen = expanded === conv.id;
          const msgCount = conv.messages?.length ?? 0;

          return (
            <div
              key={conv.id}
              className={`hist-card ${isOpen ? 'hist-card--open' : ''}`}
              style={{ animationDelay: `${i * 0.04}s` }}
            >
              {/* Card header */}
              <button
                className="hist-card__header"
                onClick={() => setExpanded(isOpen ? null : conv.id)}
              >
                <div className="hist-card__left">
                  <div className="hist-card__avatar">
                    {(conv.student_username || `S${conv.student_id}`)[0].toUpperCase()}
                  </div>
                  <div className="hist-card__info">
                    <span className="hist-card__name">
                      {conv.student_username
                        ? `Session with ${conv.student_username}`
                        : `Session with Student #${conv.student_id}`}
                    </span>
                    <span className="hist-card__meta">
                      <span className="hist-card__date">{formatDate(conv.created_at)}</span>
                      <span className="hist-card__sep">·</span>
                      <span className="hist-card__time">{formatTime(conv.created_at)}</span>
                      <span className="hist-card__sep">·</span>
                      <span className="hist-card__count">{msgCount} message{msgCount !== 1 ? 's' : ''}</span>
                    </span>
                  </div>
                </div>
                <span className={`hist-card__chevron ${isOpen ? 'hist-card__chevron--open' : ''}`}>›</span>
              </button>

              {/* Expanded messages */}
              {isOpen && (
                <div className="hist-messages fade-in">
                  {msgCount === 0 && (
                    <p className="hist-messages__empty">No messages in this session</p>
                  )}
                  {conv.messages?.map(msg => {
                    const { role, text, isSign } = parseMessageRole(msg.content);
                    return (
                      <div key={msg.id} className={`hist-msg hist-msg--${role}`}>
                        <div className="hist-msg__bubble">
                          {isSign && <span className="hist-msg__sign-tag">✋ Sign</span>}
                          <span className="hist-msg__text">{text}</span>
                        </div>
                        <div className="hist-msg__footer">
                          <span className="hist-msg__role">
                            {role === 'teacher' ? '◎ Teacher' : '◈ Student'}
                          </span>
                          <span className="hist-msg__time">{formatTime(msg.timestamp)}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
