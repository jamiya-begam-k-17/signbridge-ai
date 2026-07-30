import '../../pages/Classroom.css';

export default function ClassroomChatPanel({
  chatOpen,
  setChatOpen,
  selectedStudentName,
  sessionActive,
  chatMessages,
  teacherInput,
  setTeacherInput,
  studentInput,
  setStudentInput,
  onTeacherSend,
  onStudentSend,
  chatEndRef,
}) {
  return (
    <>
      <button
        className={`cr-chat-toggle${chatOpen ? ' cr-chat-toggle--open' : ''}`}
        onClick={() => setChatOpen((prev) => !prev)}
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
          {chatMessages.map((msg) => (
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
                onChange={(e) => setTeacherInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    onTeacherSend();
                  }
                }}
                disabled={!sessionActive}
              />
              <button
                className="btn btn-primary cr-send-btn"
                onClick={onTeacherSend}
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
                onChange={(e) => setStudentInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    onStudentSend();
                  }
                }}
                disabled={!sessionActive}
              />
              <button
                className="btn btn-ghost cr-send-btn"
                onClick={onStudentSend}
                disabled={!sessionActive || !studentInput.trim()}
                type="button"
              >↑</button>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
