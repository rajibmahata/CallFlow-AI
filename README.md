# CallFlow AI — AI SDR for Event Attendance

An end-to-end AI Sales Development Representative (SDR) system that drives seminar/webinar attendance for a 50+ demographic using AI-powered outbound calling, intelligent lead scoring, and human-in-the-loop confirmation.

---

## Architecture Overview

```
nginx (80) ──► frontend (React/Vite)  ──► /
           ──► backend (FastAPI)       ──► /api/
           ──► backend WebSocket       ──► /ws/calls
           ──► backend webhooks        ──► /webhook/

backend ──► PostgreSQL (leads, campaigns, call_logs, reminders, users)
        ──► Redis (Celery broker + DND scrub list)
        ──► ChromaDB (RAG knowledge base for event FAQ)
        ──► Retell AI (outbound voice calls)
        ──► Twilio (SMS confirmation + opt-out)

Celery workers:
  - call_tasks:  batch_queue_leads, dispatch_single_call, analyze_transcript_task
  - sms_tasks:   send_confirmation_sms_task
  - beat tasks:  send_due_reminders (15m), retry_scheduled_callbacks (60m)

CrewAI agents (run inside Celery workers):
  1. PersonalizationAgent  — pre-call opener generation
  2. TranscriptAnalyzer    — intent + sentiment classification post-call
  3. FollowUpStrategist    — next action decision with ChromaDB RAG
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI 0.111 + Pydantic v2 |
| DB | PostgreSQL 16 + SQLAlchemy 2.0 async |
| Migrations | Alembic |
| Task Queue | Celery 5.4 + Redis 7 |
| AI Agents | CrewAI 0.55 + LangChain |
| LLMs | OpenAI GPT-4o + DeepSeek (per campaign) |
| Voice | Retell AI |
| SMS | Twilio |
| Voice Synthesis | ElevenLabs (via Retell agent config) |
| Vector DB | ChromaDB |
| Auth | JWT + bcrypt + role-based guards |
| Frontend | Vite + React 18 + TypeScript + Tailwind CSS |
| State Management | Zustand + TanStack Query |
| Charts | Recharts |
| Monitoring | Prometheus + Sentry + structlog |
| Containers | Docker + Docker Compose |

---

## Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/your-org/callflow-ai
cd callflow-ai
cp .env.example .env
# Edit .env — set API keys for OpenAI/DeepSeek, Retell, Twilio
```

### 2. Start with Docker Compose (development)

```bash
docker compose up --build
```

Services started:
- `http://localhost` — Frontend (React dashboard)
- `http://localhost:8000` — Backend API (FastAPI docs at `/docs`)
- `http://localhost:8001` — ChromaDB

### 3. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 4. Create the first admin user

```bash
docker compose exec backend python - <<'EOF'
import asyncio
from app.database import AsyncSessionFactory
from app.models.user import User, UserRole
from app.core.auth import hash_password

async def create_admin():
    async with AsyncSessionFactory() as db:
        user = User(email="admin@example.com", hashed_password=hash_password("changeme"), role=UserRole.ADMIN, full_name="Admin")
        db.add(user)
        await db.commit()
        print("Admin created: admin@example.com / changeme")

asyncio.run(create_admin())
EOF
```

---

## Key Workflows

### Lead Import → Call → Confirm Flow

```
1. Admin uploads CSV → POST /api/leads/upload
2. Admin starts campaign → POST /api/campaigns/{id}/start
3. Celery: batch_queue_leads → dispatch_single_call per lead
4. Retell AI makes outbound call
5. Webhook: call_started → creates CallLog, broadcasts to WebSocket
6. Webhook: call_ended → stores transcript → triggers analyze_transcript_task
7. CrewAI: TranscriptAnalyzer → intent + sentiment
8. CrewAI: FollowUpStrategist → NEEDS_HUMAN_APPROVAL | SCHEDULE_CALLBACK | MARK_NOT_INTERESTED
9. If NEEDS_HUMAN_APPROVAL → lead appears in Confirmation Queue UI
10. Agent approves → lead.status = CONFIRMED → Twilio sends confirmation SMS
11. Celery beat: send_due_reminders → SMS at T-48h, T-24h, T-2h
```

### DND / Compliance

- Upload DND list via `POST /api/leads/upload-dnd-scrub`
- Numbers stored in Redis SET for O(1) lookup
- Calling window enforced (default 9am–7pm in lead's timezone)
- Twilio inbound STOP/UNSUBSCRIBE → sets `do_not_call=True`

---

## Environment Variables

See `.env.example` for the full list. Critical variables:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key (min 32 chars) |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `OPENAI_API_KEY` | OpenAI API key |
| `DEEPSEEK_API_KEY` | DeepSeek API key |
| `RETELL_API_KEY` | Retell AI API key |
| `RETELL_AGENT_ID` | Pre-configured Retell agent |
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_FROM_NUMBER` | Verified Twilio phone number |

---

## User Roles

| Role | Permissions |
|------|-------------|
| `admin` | Full access — create campaigns, approve/reject leads, view all data |
| `agent` | Upload leads, view calls, approve in confirmation queue |
| `viewer` | Read-only access to dashboard and analytics |

---

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest
```

---

## Production Deployment

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Key differences from dev:
- Multi-worker uvicorn (`--workers 4`)
- Celery concurrency raised to 8
- No bind-mount volumes (image baked assets)
- TLS certs from `/etc/letsencrypt` mounted into nginx

---

## API Documentation

Interactive docs available at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc`.

Key endpoints:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Login → JWT |
| GET | `/auth/me` | Current user |
| GET | `/campaigns/` | List campaigns |
| POST | `/campaigns/` | Create campaign |
| POST | `/campaigns/{id}/start` | Launch calling |
| POST | `/leads/upload` | Import CSV |
| GET | `/leads/` | List leads (filterable) |
| POST | `/leads/{id}/approve` | Approve for confirmation |
| POST | `/leads/{id}/reject` | Reject lead |
| GET | `/calls/` | List call logs |
| POST | `/calls/initiate` | Manual call dispatch |
| POST | `/webhook/retell` | Retell AI webhook |
| POST | `/webhook/sms` | Twilio SMS webhook |
| WS | `/ws/calls` | Live call feed |
