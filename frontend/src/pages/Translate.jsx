// ============================================================
// Translate Page – Text → Sign Language
// Reverse communication: non-signers type text, hearing-impaired
// students receive it as sign language visual references.
//
// Since the backend does not have a text-to-sign video endpoint,
// this page uses a well-known public ASL dictionary URL pattern
// to show sign reference images/GIFs per word.
// ============================================================

import { useState } from 'react';
import { useSpeech } from '../hooks/useSpeech';
import './Translate.css';

// Supported signs that the model was trained on
// (matches SIGNS list in ai_model/create_landmark_dataset.py)
const MODEL_SIGNS = ['hello', 'help', 'no', 'water', 'yes', 'thank you'];

// ASL SigningSavvy GIF URL (free public resource for ASL signs)
// Pattern: https://www.signingsavvy.com/sign/{WORD}
// We use Handspeak for embeddable images
function getSignUrl(word) {
  return `https://www.handspeak.com/word/search/index.php?id=${encodeURIComponent(word)}`;
}

export default function Translate() {
  const [inputText, setInputText]   = useState('');
  const [words,     setWords]       = useState([]);
  const [selected,  setSelected]    = useState(null);
  const { speak, supported }        = useSpeech();

  const handleTranslate = () => {
    const parsed = inputText
      .trim()
      .toLowerCase()
      .split(/\s+/)
      .filter(Boolean);
    setWords(parsed);
    setSelected(null);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleTranslate();
    }
  };

  const knownWords   = words.filter((w) => MODEL_SIGNS.includes(w));
  const unknownWords = words.filter((w) => !MODEL_SIGNS.includes(w));

  return (
    <div className="translate-page">
      <div className="translate-page__header fade-up">
        <h1 className="translate-page__title">Text → Sign</h1>
        <p className="translate-page__sub">
          Type a message to translate into sign language visuals. Hearing-impaired
          students can see each sign reference and follow along.
        </p>
      </div>

      {/* Input */}
      <div className="translate-page__input-area fade-up" style={{ animationDelay: '0.1s' }}>
        <textarea
          className="translate-page__textarea"
          placeholder="Type your message here… (e.g. hello yes thank you)"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={3}
        />
        <div className="translate-page__input-actions">
          <span className="translate-page__hint">
            Supported signs: {MODEL_SIGNS.join(', ')}
          </span>
          <div style={{ display: 'flex', gap: '10px' }}>
            {supported && inputText && (
              <button className="btn btn-ghost" onClick={() => speak(inputText)}>
                🔊 Read Aloud
              </button>
            )}
            <button
              className="btn btn-primary"
              onClick={handleTranslate}
              disabled={!inputText.trim()}
            >
              Translate →
            </button>
          </div>
        </div>
      </div>

      {/* Unknown words notice */}
      {unknownWords.length > 0 && words.length > 0 && (
        <div className="translate-page__warn fade-in">
          ⚠ Words not in sign model:{' '}
          <strong>{unknownWords.join(', ')}</strong>. Shown as text only.
        </div>
      )}

      {/* Word chips */}
      {words.length > 0 && (
        <div className="translate-page__chips fade-up">
          {words.map((w, i) => (
            <button
              key={i}
              className={`translate-page__chip ${
                MODEL_SIGNS.includes(w) ? 'translate-page__chip--known' : 'translate-page__chip--unknown'
              } ${selected === i ? 'translate-page__chip--active' : ''}`}
              onClick={() => MODEL_SIGNS.includes(w) && setSelected(i)}
            >
              {w}
              {MODEL_SIGNS.includes(w) && (
                <span className="translate-page__chip-badge">ASL</span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Sign card grid */}
      {knownWords.length > 0 && (
        <div className="translate-page__cards fade-up" style={{ animationDelay: '0.15s' }}>
          {knownWords.map((w, i) => (
            <div
              key={`${w}-${i}`}
              className={`translate-page__sign-card ${
                selected !== null && words[selected] === w ? 'translate-page__sign-card--selected' : ''
              }`}
            >
              {/* Visual reference */}
              <div className="translate-page__sign-visual">
                <div className="translate-page__sign-letter">{w[0].toUpperCase()}</div>
                <div className="translate-page__sign-label">{w}</div>
              </div>

              <div className="translate-page__sign-info">
                <p className="translate-page__sign-name">{w}</p>
                <p className="translate-page__sign-note">
                  Show this sign to communicate "{w}" in ASL
                </p>
                <a
                  href={getSignUrl(w)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-ghost translate-page__sign-ref-btn"
                >
                  View reference →
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {words.length === 0 && (
        <div className="translate-page__empty fade-in">
          <div className="translate-page__empty-icon">⇄</div>
          <p>Enter text above to see sign language translations</p>
        </div>
      )}
    </div>
  );
}