# SignBridge AI

SignBridge AI is an AI-powered accessibility and communication platform designed to support deaf, hard-of-hearing, and visually impaired individuals in educational environments. The platform enables real-time sign language recognition, speech-to-text interaction, and inclusive classroom communication through computer vision, machine learning, and modern web technologies.

---

## Problem Statement

Hearing-impaired and visually impaired students often face communication barriers in classrooms due to the lack of affordable and real-time accessibility tools. Existing systems are typically expensive, one-directional, hardware-dependent, or difficult to integrate into mainstream educational environments.

These limitations reduce classroom participation, accessibility, and effective communication between students, teachers, and peers.

---

## Solution

SignBridge AI provides a real-time AI-driven accessibility platform that bridges communication gaps inside classrooms and learning environments.

The system combines computer vision, sign language recognition, speech processing, authentication systems, and an interactive web platform to enable seamless two-way communication between sign language users and non-sign language users.

The platform is lightweight, scalable, modular, and accessible through standard webcams and modern browsers.

---

# Key Features

- Real-time sign language recognition using webcam input
- Two-way communication between sign language and text/speech
- Speech-to-text and text-to-speech interaction
- Secure user authentication and authorization
- JWT-based login session management
- Conversation and translation history tracking
- Classroom learning and accessibility mode
- AI-powered hand landmark detection
- Responsive user interface for desktop and mobile devices
- Modular AI model integration for future upgrades
- REST API-based frontend and backend communication

---

# Tech Stack

## Frontend
- React.js
- Vite
- JavaScript
- HTML5
- CSS3

## Backend
- FastAPI
- Python
- REST API Architecture

## Authentication & Security
- JWT (JSON Web Tokens)
- Password Hashing
- User Authentication & Authorization

## AI & Computer Vision
- MediaPipe Hand Landmark Detection
- OpenCV
- Custom Machine Learning Classification Models
- NumPy

## Database & ORM
- PostgreSQL
- SQLAlchemy

## Development Tools
- npm
- pip
- Virtual Environment (venv)
- Git & GitHub

---

# System Architecture

```text
Frontend (React + Vite)
          |
          v
Backend API (FastAPI + JWT Authentication)
          |
          v
AI Processing Layer
(MediaPipe + OpenCV + ML Model)
          |
          v
Prediction & Translation Engine
          |
          v
Database (PostgreSQL)
```

---

# Workflow

1. User logs into the platform securely using JWT authentication
2. Webcam captures hand gestures in real time
3. MediaPipe extracts hand landmarks
4. AI model predicts the corresponding sign
5. Backend processes and stores translation data
6. Frontend displays translated text or speech output
7. Conversation history is saved for future reference

---

# Project Structure

```text
signbridge-ai/
│
├── frontend/              # React frontend
├── backend/               # FastAPI backend
├── ai_model/              # AI models and training scripts
├── database/              # Database-related files
├── README.md
└── requirements.txt
```

---

# Installation & Setup

## Prerequisites

Make sure the following are installed:

- Python 3.8+
- Node.js 16+
- npm
- pip
- PostgreSQL

---

# Backend Setup

Navigate to the backend directory:

```bash
cd backend
```

Create virtual environment:

```bash
python -m venv venv
```

Activate virtual environment:

### Windows
```bash
venv\Scripts\activate
```

### Linux/macOS
```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run backend server:

```bash
python main.py
```

---

# Frontend Setup

Open another terminal and navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start frontend development server:

```bash
npm run dev
```

---

# AI Model Setup

Navigate to AI model directory:

```bash
cd ai_model
```

Use the provided scripts and datasets to train or test sign recognition models.

---

# API Features

- User Registration API
- User Login API
- JWT Token Authentication
- Sign Prediction API
- Translation API
- Conversation History API
- Classroom Session APIs

---

# Future Improvements

- Dynamic sign sentence recognition
- Real-time multilingual translation
- Mobile application support
- OCR integration for visually impaired users
- Voice assistant integration
- Cloud deployment support
- Advanced classroom analytics dashboard
- Transformer-based deep learning models

---

# Team Members

- Jamiya Begam K 17  
  GitHub: https://github.com/jamiya-begam-k17

- Mohamed Afrik  
  GitHub: https://github.com/moh-afrik

- Javid Afzal  
  GitHub: https://github.com/javid-afzal

---

# Important Notes

- AI model files and utilities are located in the `ai_model/` directory
- Frontend source code is inside `frontend/src`
- Backend APIs are inside `backend/`
- Update configuration files before production deployment
- Do not upload `.env`, `venv`, or large model files unnecessarily

---

# License

This project is licensed under the MIT License.

See the `LICENSE` file for more details.
