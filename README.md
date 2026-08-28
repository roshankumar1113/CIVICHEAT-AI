# CIVICHEAT AI

**Autonomous AI Heat-Response System for Government**

> "FortyGuard tells us where the heat is. CIVICHEAT tells government what to do about it."

---

## Hackathon Tracks

- 🟣 **Track 6 — Agentic AI**: Tool-using agent that plans, calls tools, reasons, and decides
- 🏛️ **Track 4 — Government & Environment**: Heat vulnerability, cooling centers, outdoor-worker thresholds

---

## Problem

Extreme heat is a silent public health emergency. Governments can access temperature data, but raw data does not tell them *which neighborhoods to prioritize*, *when to activate cooling centers*, or *how to allocate limited resources*. The gap between data and action costs lives.

## Solution

CIVICHEAT AI is an autonomous decision-support system that:

1. Retrieves real temperature intelligence from **FortyGuard**
2. Calculates a transparent **CIVICHEAT Decision-Support Risk Score**
3. Identifies and ranks **priority geographic zones**
4. Uses **NVIDIA Nemotron** as a tool-using reasoning agent
5. Generates structured **government action plans**
6. Simulates **resource allocation** across interventions
7. Provides a professional **government command-center dashboard**

---

## Why FortyGuard

FortyGuard provides the environmental intelligence layer. Every AI decision in CIVICHEAT is grounded in FortyGuard's temperature data. FortyGuard is not decorative — it is the foundation.

## Why Nemotron

NVIDIA Nemotron serves as the reasoning engine. The agent calls real application tools, inspects results, and produces structured action plans. It is not a chatbot.

---

## Architecture

```
FortyGuard API
     │
     ▼
Heat Analyzer (risk engine + priority engine)
     │
     ▼
Nemotron Agent (plan → call tools → decide)
     │
     ▼
Action Plan (cooling centers / worker safety / public alert)
     │
     ▼
Government Dashboard (React command center)
```

---

## Features

- Live FortyGuard heat intelligence (U.S. locations)
- CIVICHEAT Decision-Support Risk Score (transparent, explainable)
- Priority zone detection and ranking
- Nemotron-powered agentic action planning
- Resource optimization (cooling centers, mobile units, shade structures)
- Government command-center dashboard
- Demo mode / Live mode toggle
- All metrics traceable to source data or clearly labeled as simulation

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, Vite, TypeScript, Tailwind CSS, MapLibre GL JS |
| Backend | Python, FastAPI |
| AI | NVIDIA Nemotron (OpenAI-compatible API) |
| Data | FortyGuard Temperature API, GeoJSON |
| Database | PostgreSQL/PostGIS (Phase 2+) |
| Deployment | Vercel (frontend), Railway (backend) |

## Deployment

Detailed deployment instructions for Vercel, Render, Railway, and Docker are provided in **[DEPLOYMENT.md](DEPLOYMENT.md)**.

---

## Local Setup

### Prerequisites

- Python 3.11
- Node.js 18+
- Git

### Backend

```bash
cd backend
py -3.11 -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your API keys
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `FORTYGUARD_API_KEY` | FortyGuard API key |
| `FORTYGUARD_BASE_URL` | FortyGuard base URL |
| `NEMOTRON_BASE_URL` | Nemotron inference endpoint |
| `NEMOTRON_API_KEY` | Nemotron API key |
| `NEMOTRON_MODEL` | Model identifier |
| `APP_ENV` | `development` or `production` |

### Frontend (`frontend/.env`)

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend URL |

---

## API Documentation

With the backend running, visit:

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

---

## Demo Mode vs Live Mode

| Mode | Description |
|------|-------------|
| **DEMO** | Uses bundled sample FortyGuard responses. No API key required. |
| **LIVE** | Uses real FortyGuard API. Requires valid `FORTYGUARD_API_KEY`. |

The UI clearly indicates which mode is active.

---

## Testing

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

---

## Limitations

- Risk score is a heuristic model, not a medically validated index. It is labeled "CIVICHEAT Decision-Support Risk Score."
- Resource allocation uses demo cost assumptions, clearly labeled.
- Impact simulations are estimates, not measured outcomes.
- FortyGuard API operates on U.S. locations for this demo.

---

## Future Roadmap

- PostgreSQL/PostGIS for historical analysis
- Multi-city comparison
- Automated reassessment scheduling
- Alert integration (SMS/email)
- Public API for government systems
- Audit log for accountability

---

*Built for the CIVICHEAT AI Hackathon — Track 4 & Track 6*
