// ============================================================
// Home Page – Landing / Hero
// ============================================================

import { Link } from 'react-router-dom';
import './Home.css';

const FEATURES = [
  {
    icon: '◈',
    title: 'Real-Time Sign Detection',
    desc: 'MediaPipe hand landmarks + ML classifier recognises signs from your webcam in under a second.',
  },
  {
    icon: '⇄',
    title: 'Bidirectional Translation',
    desc: 'Text-to-sign and sign-to-text translation bridges the gap between all classroom participants.',
  },
  {
    icon: '⊕',
    title: 'Classroom Mode',
    desc: 'Live speech-to-text captioning and sign output — built for inclusive education environments.',
  },
  {
    icon: '◎',
    title: 'Lightweight & Offline-First',
    desc: 'Designed for low-cost school devices. AI model runs locally with no cloud dependency.',
  },
];

const SIGNS = ['hello', 'help', 'water', 'yes', 'no', 'thank you'];

export default function Home({ apiHealthy }) {
  return (
    <div className="home">
      {/* Background grid */}
      <div className="home__grid-bg" aria-hidden="true" />

      {/* Hero */}
      <section className="home__hero fade-up">
        <div className="home__hero-tag badge badge-live">
          {apiHealthy ? 'System Ready' : 'API Offline – Start FastAPI backend'}
        </div>

        <h1 className="home__headline">
          Bridging<br />
          <span className="home__headline-accent">Sign Language</span><br />
          & the Classroom
        </h1>

        <p className="home__sub">
          AI-powered real-time sign language communication for hearing-impaired students.
          Detect signs, generate text, and enable two-way interaction — instantly.
        </p>

        <div className="home__cta">
          <Link to="/detect" className="btn btn-primary">
            ▶ Start Detection
          </Link>
          <Link to="/classroom" className="btn btn-ghost">
            Classroom Mode
          </Link>
        </div>
      </section>

      {/* Supported signs */}
      <section className="home__signs fade-up" style={{ animationDelay: '0.15s' }}>
        <p className="home__signs-label">Supported signs include</p>
        <div className="home__signs-list">
          {SIGNS.map((s) => (
            <span key={s} className="home__sign-chip">{s}</span>
          ))}
          <span className="home__sign-chip home__sign-chip--more">+ more</span>
        </div>
      </section>

      {/* Features grid */}
      <section className="home__features" style={{ animationDelay: '0.25s' }}>
        {FEATURES.map((f, i) => (
          <div
            key={f.title}
            className="home__feature-card fade-up"
            style={{ animationDelay: `${0.1 * i + 0.2}s` }}
          >
            <div className="home__feature-icon">{f.icon}</div>
            <h3 className="home__feature-title">{f.title}</h3>
            <p className="home__feature-desc">{f.desc}</p>
          </div>
        ))}
      </section>

      {/* Tech stack note */}
      <section className="home__stack fade-up" style={{ animationDelay: '0.5s' }}>
        <div className="home__stack-inner">
          <span className="home__stack-label">Built with</span>
          {['MediaPipe', 'scikit-learn', 'FastAPI', 'React + Vite', 'Web Speech API'].map((t) => (
            <span key={t} className="home__stack-chip">{t}</span>
          ))}
        </div>
      </section>
    </div>
  );
}