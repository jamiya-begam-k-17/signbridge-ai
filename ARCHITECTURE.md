# SignBridge AI - Render Deployment Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Internet Users                          │
└────────────────────┬────────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
   ┌─────────────────┐       ┌─────────────────┐
   │   FRONTEND      │       │  API (REST)     │
   │ Render Static   │◄──────┤  Render Web     │
   │ (React + Vite)  │       │  (FastAPI)      │
   │                 │       │                 │
   │ dist/index.html │       │ /health         │
   │ dist/app.jsx    │       │ /predict        │
   │ (built files)   │       │ /register       │
   └────────────┬────┘       └────────┬────────┘
                │                     │
                │   API calls via     │
                │   VITE_API_URL      │
                │                     │
                │                     │
        ┌───────▼─────────────────────▼──────────┐
        │                                        │
        │       Neon PostgreSQL Database        │
        │    (Cloud-hosted on AWS)              │
        │                                        │
        │  Tables:                              │
        │  - users                              │
        │  - conversations                      │
        │  - messages                           │
        └────────────────────────────────────────┘
```

---

## Deployment Flow

```
Your Computer
     │
     │ git push
     │
     ▼
GitHub Repository
     │
     ├─────────────────────┬──────────────────┐
     │                     │                  │
     │ Render detects      │                  │
     │ new push            │                  │
     │                     │                  │
     ▼                     ▼                  ▼
  Backend Build        Frontend Build      Database
  (Python)            (Node.js/Vite)       (Neon)
     │                     │
     │ pip install         │ npm install
     │ gunicorn            │ npm run build
     │ FastAPI             │
     │                     │
     ▼                     ▼
  Running API          Running Static
  Port: $PORT          Files (dist/)
  URL:                 URL:
  signbridge-api.      signbridge-frontend.
  onrender.com         onrender.com
```

---

## Environment Variables

### Backend (Web Service)
```
┌─────────────────────────────────────┐
│  signbridge-api Service             │
├─────────────────────────────────────┤
│ DATABASE_URL                        │
│ ↓                                   │
│ postgresql://...@neon.tech/neondb   │
├─────────────────────────────────────┤
│ SECRET_KEY                          │
│ ↓                                   │
│ 271ab9436e21b946...                │
├─────────────────────────────────────┤
│ ALLOWED_ORIGINS                     │
│ ↓                                   │
│ https://signbridge-frontend.        │
│ onrender.com                        │
└─────────────────────────────────────┘
```

### Frontend (Static Site)
```
┌─────────────────────────────────────┐
│  signbridge-frontend Service        │
├─────────────────────────────────────┤
│ VITE_API_URL                        │
│ ↓                                   │
│ https://signbridge-api.onrender.com │
└─────────────────────────────────────┘
```

---

## Deployment Timeline

### Week 1: Initial Setup
```
Day 1: Push code to GitHub
Day 2: Deploy Backend
       ├─ Build Docker image
       ├─ Install dependencies
       ├─ Start gunicorn server
       └─ Connect to Neon DB
       
Day 2: Deploy Frontend
       ├─ Build React app
       ├─ Run npm build
       ├─ Deploy to CDN
       └─ Link to backend API
       
Day 3: Test & Verify
       ├─ Test health endpoint
       ├─ Test login flow
       ├─ Test API calls
       └─ Add uptime monitor
```

### Ongoing: Maintenance
```
- Monitor logs (daily)
- Check error rates (weekly)
- Update dependencies (monthly)
- Scale if needed (based on usage)
```

---

## Data Flow Example: Sign Language Prediction

```
User's Browser
(Frontend)
│
│ 1. Captures video frame
│ 2. Sends to backend
├────────────────────────────────┐
│                                │
▼                                │
Frontend                         │
(React Component)                │
│                                │
│ 3. POST /predict               │
│    with image data             │
│                                │
├──────────────────────────────────┐
│                                  │
▼                                  │
Backend API                        │
(FastAPI)                          │
│                                  │
│ 4. Process image                 │
│ 5. Load ML model                 │
│ 6. Detect hand landmarks         │
│ 7. Predict gesture               │
│                                  │
├──────────────────────────────────┐
│                                  │
▼                                  │
Database                           │
(Neon PostgreSQL)                  │
│                                  │
│ 8. Store prediction in          │
│    conversation history          │
│                                  │
│ 9. Return prediction result      │
│                                  │
└──────────────────────────────────┤
│                                  │
▼                                  │
Frontend                           │
│                                  │
│ 10. Display prediction           │
│ 11. Update conversation          │
│                                  │
└──────────────────────────────────┘
```

---

## Security Architecture

```
┌─────────────────────────────────────────────────┐
│  Your Frontend Domain                           │
│  https://signbridge-frontend.onrender.com       │
└────────────────┬────────────────────────────────┘
                 │
        ┌────────▼────────┐
        │  CORS Check     │
        │ (Allow list)    │
        │  ✓ Frontend OK  │
        │  ✗ Other block  │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │ JWT Token Check │
        │ (Authorization) │
        │  ✓ Valid token  │
        │  ✗ Reject       │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │ Process Request │
        │ & Return Data   │
        └────────────────┘

Environment Variables:
┌──────────────────────────────────────┐
│ Sensitive data in Render UI, NOT:    │
│ ✗ In code (git)                      │
│ ✗ In version control                 │
│ ✓ In Render Environment Variables    │
│ ✓ Encrypted at rest                  │
└──────────────────────────────────────┘
```

---

## URL Routes After Deployment

### Frontend URLs
```
https://signbridge-frontend.onrender.com/
  ├─ /                (Home page)
  ├─ /login           (Login)
  ├─ /register        (Registration)
  ├─ /detect          (Sign detection)
  ├─ /translate       (Translation)
  ├─ /classroom       (Learning mode)
  ├─ /assistive       (Assistive features)
  └─ /history         (Conversation history)
```

### Backend API Routes
```
https://signbridge-api.onrender.com/
  ├─ GET  /health              (Health check)
  ├─ POST /register            (User registration)
  ├─ POST /token               (User login)
  ├─ POST /conversations       (Create conversation)
  ├─ GET  /conversations       (Get conversations)
  ├─ POST /conversations/{id}/messages  (Send message)
  ├─ GET  /conversations/{id}/messages  (Get messages)
  └─ POST /predict             (Sign prediction)
```

---

## Performance Metrics

### Expected Performance (Free Tier)
```
┌──────────────────────────────────────┐
│  Backend Service                     │
├──────────────────────────────────────┤
│ CPU:           Shared (0.5 vCPU)     │
│ Memory:        512 MB                │
│ Concurrent:    ~50 users             │
│ Response time: ~200-500ms            │
│ Uptime:        ~99.9% (with monitor) │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│  Frontend (Static)                   │
├──────────────────────────────────────┤
│ Load time:     ~1-2 seconds          │
│ Time-to-paint: ~500ms                │
│ CDN cached:    Yes                   │
│ Uptime:        99.99%                │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│  Database (Neon Free)                │
├──────────────────────────────────────┤
│ Storage:       5 GB                  │
│ Connections:   100 concurrent        │
│ Query speed:   ~50-100ms             │
│ Uptime:        99.99%                │
└──────────────────────────────────────┘
```

---

## Scaling Path (When Needed)

```
Step 1: Current (Free)
├─ Backend: Free tier ($0)
├─ Frontend: Free tier ($0)
└─ Database: Neon free (5GB)

        ↓ (When traffic increases)

Step 2: Growth
├─ Backend: Starter plan ($7/month)
├─ Frontend: Still free
└─ Database: Neon growth plan

        ↓ (When more storage needed)

Step 3: Scale
├─ Backend: Standard plan ($12-25/month)
├─ Frontend: Custom domain + CDN
└─ Database: Neon business plan

        ↓ (Enterprise)

Step 4: Enterprise
├─ Backend: Multiple instances
├─ Frontend: Global CDN + Edge cache
├─ Database: Dedicated cluster
└─ Monitoring: Datadog/New Relic
```

---

## Monitoring & Logging

### Render Dashboard
```
┌─────────────────────────────────────┐
│  Real-time Metrics                  │
├─────────────────────────────────────┤
│ ✓ Deployment status                 │
│ ✓ Service health                    │
│ ✓ Error logs                        │
│ ✓ CPU/Memory usage                  │
│ ✓ Request count                     │
│ ✓ Response times                    │
│ ✓ Uptime history                    │
└─────────────────────────────────────┘
```

### Optional: External Monitoring
```
- Uptime Robot (API health checks)
- Sentry (Error tracking)
- Datadog (Performance monitoring)
- LogRocket (Frontend session replay)
```

---

## Disaster Recovery

### If Backend Goes Down
```
1. Check Render dashboard
   ├─ View logs for errors
   ├─ Restart service
   └─ Check environment variables

2. If database issue:
   ├─ Verify DATABASE_URL
   ├─ Check Neon status page
   └─ Try reconnecting

3. If code issue:
   ├─ Rollback in Git
   ├─ Push new code
   └─ Render auto-redeploys
```

### If Frontend Goes Down
```
1. Check Render dashboard
   ├─ View build logs
   ├─ Verify build command
   └─ Check environment variables

2. If build fails:
   ├─ Fix code locally
   ├─ Push to GitHub
   └─ Render auto-rebuilds

3. If static files issue:
   ├─ Verify Publish Directory
   ├─ Check dist/ folder size
   └─ Clear cache (Render auto-clears)
```

---

## Summary

```
Your Application is now:
✓ Cloud-deployed (Render)
✓ Globally accessible
✓ Auto-scaling ready
✓ Secure (CORS, JWT)
✓ Production-ready
✓ Monitored & logged
✓ Zero-cost MVP
✓ Easy to maintain
```

**Total Setup Time**: ~30 minutes
**Monthly Cost**: $0 (free tier)
**Users Supported**: 50-100 concurrent (free tier)

---

## Quick Links

- **Render Dashboard**: https://dashboard.render.com
- **Your Frontend**: https://signbridge-frontend.onrender.com
- **Your Backend API**: https://signbridge-api.onrender.com
- **GitHub Repo**: [Your repo URL]
- **Database (Neon)**: https://console.neon.tech

Good luck! 🚀
