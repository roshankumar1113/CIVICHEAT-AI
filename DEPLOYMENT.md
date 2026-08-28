# 🚀 CIVICHEAT AI Deployment Guide

Complete step-by-step instructions to deploy **CIVICHEAT AI** to free-tier cloud platforms.

---

## 🏗️ Architecture Overview

```
Frontend (Vercel)  ── HTTPS / REST API ──▶  Backend (Render / Railway)
(React + Vite SPA)                           (FastAPI + Python 3.11)
```

---

## Part 1: Deploy Backend (Render / Railway)

### Option A: Render (Free Tier)

1. **Push your code to GitHub**:
   Make sure your repo is committed and pushed to your GitHub account.

2. **Sign in to Render**:
   - Go to [render.com](https://render.com/) and sign in with GitHub.

3. **Create New Web Service**:
   - Click **New +** → **Web Service**.
   - Connect your **CIVICHEAT AI** repository.
   - Configure the following settings:
     - **Name**: `civicheat-backend`
     - **Region**: Select closest to your users (e.g., Oregon or Frankfurt).
     - **Root Directory**: `backend` *(Crucial!)*
     - **Environment**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
     - **Instance Type**: `Free`

4. **Add Environment Variables** (under *Advanced* or *Environment* tab):
   | Key | Value | Notes |
   |-----|-------|-------|
   | `APP_ENV` | `production` | Enables production mode |
   | `FORTYGUARD_API_KEY` | *Your FortyGuard key* | Optional in demo mode |
   | `FORTYGUARD_BASE_URL` | `https://api.fortyguard.com` | Default |
   | `NEMOTRON_BASE_URL` | *Your Nemotron URL* | Optional |
   | `NEMOTRON_API_KEY` | *Your Nemotron key* | Optional |
   | `NEMOTRON_MODEL` | `nvidia/nemotron-3-nano-30b-a3b` | Default |

5. **Deploy & Get URL**:
   - Click **Create Web Service**.
   - Once deployed, copy your backend URL (e.g., `https://civicheat-backend.onrender.com`).
   - Test it by opening `https://civicheat-backend.onrender.com/api/health` or `/api/docs`.

---

### Option B: Railway (Alternative)

1. Go to [railway.app](https://railway.app/) and sign in with GitHub.
2. Click **New Project** → **Deploy from GitHub repo**.
3. Select your repository.
4. In the settings:
   - Set **Root Directory** to `/backend`.
   - Railway will auto-detect the `backend/Dockerfile` or `backend/Procfile`.
5. Under **Variables**, add the same environment variables listed above.
6. Under **Settings** → **Networking**, click **Generate Domain** to get your public URL (e.g., `https://civicheat-backend.up.railway.app`).

---

## Part 2: Deploy Frontend (Vercel)

1. **Sign in to Vercel**:
   - Go to [vercel.com](https://vercel.com/) and sign in with GitHub.

2. **Import Project**:
   - Click **Add New...** → **Project**.
   - Select your **CIVICHEAT AI** GitHub repository.

3. **Configure Project**:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click *Edit* and select `frontend` *(Crucial!)*
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `dist` (default)
   - **Install Command**: `npm install` (default)

4. **Add Environment Variables**:
   | Variable | Value | Example |
   |----------|-------|---------|
   | `VITE_API_URL` | Your deployed backend URL (no trailing slash) | `https://civicheat-backend.onrender.com` |

5. **Deploy**:
   - Click **Deploy**.
   - Vercel will build and deploy your app in ~30 seconds.
   - Click the generated domain (e.g., `https://civicheat-ai.vercel.app`) to open the live dashboard!

---

## Part 3: Verify Deployment

1. Open your live frontend URL on Vercel.
2. Check the header status pill — it should show `🟢 System Operational` or `Live / Demo`.
3. Try clicking:
   - **Heatmap & Analysis**: Ensure FortyGuard heat tiles load on the map.
   - **Ask CIVICHEAT**: Verify AI agent planning responds.
   - **Action Plan**: Test generating actionable cooling center recommendations.
   - **HeatWatch**: Verify continuous monitoring comparison.

---

## 🐳 Optional: Run with Docker Compose (Local or VPS)

To run both frontend and backend on any VPS or local machine:

```bash
# 1. Clone repo
git clone https://github.com/your-repo/civicheat-ai.git
cd civicheat-ai

# 2. Set environment variables (optional)
export FORTYGUARD_API_KEY="your-key"
export NEMOTRON_API_KEY="your-key"

# 3. Start containers
docker-compose up --build -d
```

- Frontend available at: `http://localhost:3000`
- Backend API available at: `http://localhost:8000`
- API Docs at: `http://localhost:8000/api/docs`
