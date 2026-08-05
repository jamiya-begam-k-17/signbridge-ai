import { useMemo, useState } from 'react';
import { useSpeech } from '../hooks/useSpeech';
import './Translate.css';

const MODEL_SIGNS = ['how_are_you', 'library', 'team', 'technology', 'thank_you'];

const LOCAL_VIDEO_PATHS = {
  how_are_you: '/videos/how_are_you_001.MOV',
  library: '/videos/library_002.MOV',
  team: '/videos/team_014.MP4',
  technology: '/videos/technology_011.MOV',
  thank_you: '/videos/thank_you_020.MOV',
};

const PHRASE_NORMALIZATIONS = {
  'how are you': 'how_are_you',
  'thank you': 'thank_you',
};

function getVideoUrl(word) {
  return LOCAL_VIDEO_PATHS[word] || '#';
}

function normalizeInputText(text) {
  const tokens = text.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const parsed = [];

  for (let i = 0; i < tokens.length; i += 1) {
    const twoWord = i + 1 < tokens.length ? `${tokens[i]} ${tokens[i + 1]}` : null;
    if (twoWord && PHRASE_NORMALIZATIONS[twoWord]) {
      parsed.push(PHRASE_NORMALIZATIONS[twoWord]);
      i += 1;
      continue;
    }

    parsed.push(tokens[i].replace(/\s+/g, '_'));
  }

  return parsed;
}


export default function Translate() {
  const [inputText, setInputText]   = useState('');
  const [words,     setWords]       = useState([]);
  const [selected,  setSelected]    = useState(null);
  const [activeVideo, setActiveVideo] = useState(null);
  const { speak, supported }        = useSpeech();

  const handleTranslate = () => {
    const parsed = normalizeInputText(inputText);
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

  const activeVideoUrl = useMemo(() => {
    if (!activeVideo) return null;
    return getVideoUrl(activeVideo);
  }, [activeVideo]);

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
          placeholder="Type your message here… (e.g. how_are_you library team technology thank_you)"
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

      {/* Sign card grid with video preview */}
      {knownWords.length > 0 && (
        <div className="translate-page__cards-container fade-up" style={{ animationDelay: '0.15s' }}>
          <div className="translate-page__cards">
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
                  <button
                    type="button"
                    className="btn btn-ghost translate-page__sign-ref-btn"
                    onClick={() => setActiveVideo(w)}
                  >
                    {activeVideo === w ? 'Playing…' : 'Play video →'}
                  </button>
                </div>
              </div>
            ))}
          </div>

          {activeVideoUrl && (
            <div className="translate-page__video-player">
              <div className="translate-page__video-header">
                <h3 className="translate-page__video-title">Preview: {activeVideo}</h3>
                <button
                  type="button"
                  className="btn btn-ghost translate-page__video-close"
                  onClick={() => setActiveVideo(null)}
                >
                  Close
                </button>
              </div>
              <video
                key={activeVideoUrl}
                className="translate-page__video"
                controls
                autoPlay
                playsInline
                preload="metadata"
              >
                <source src={activeVideoUrl} type="video/mp4" />
                <source src={activeVideoUrl} />
                Your browser does not support the video tag.
              </video>
            </div>
          )}
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