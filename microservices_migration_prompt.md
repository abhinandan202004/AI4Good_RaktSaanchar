# 🩸 RaktSaanchar — Microservices Migration Prompt

> **Changelog (applied before sending to LLM):**
> - `chatbot-service` now calls `core-service` REST API for all PlatformAdapter data — **no direct DB access**
> - `chat-service` section expanded with Socket.IO support and explicit donor↔patient room creation trigger
> - `chat-service` now consumes `blood_request.accepted` event to auto-create room and notify both parties

> **Copy this entire document and paste it to any LLM.**
> It contains the complete current architecture, all module details, and precise migration instructions.

---

## TASK FOR THE LLM

You are an expert backend architect. Your task is to migrate the **RaktSaanchar** platform from a monolithic FastAPI application into a **Microservices architecture**. Read every section carefully before producing any output.

**Key constraint:** Replace **AWS SNS** (SMS) and **AWS SES** (email) with **100% free, self-hostable alternatives**.

---

## SECTION 1 — CURRENT PROJECT OVERVIEW

**Project:** RaktSaanchar (*रक्तसंचार* — "blood circulation")
**Domain:** AI-powered blood donation & coordination platform (AI4Good Hackathon project)
**Live:** https://raktsaanchar-frontend.onrender.com

### Roles in the system
| Role | Capabilities |
|---|---|
| **Patient** | Submit blood requests, track status, view matched donors, AI transfusion scheduling, chat |
| **Donor** | View & respond to requests, track donation history, earn badges & leaderboard points |
| **Blood Bank** | Manage inventory, validate blood units, generate PDF reports, Uber-style donor matching |
| **Coordinator/Admin** | Full oversight, map view of all requests, assign blood banks, manage all users |

---

## SECTION 2 — CURRENT MONOLITH ARCHITECTURE

### Tech Stack
- **Backend:** FastAPI (Python 3.12), single Uvicorn process, single `main.py` importing 13 router modules
- **Database:** PostgreSQL 15 (single shared DB, all tables in one schema)
- **Cache/Sessions:** Redis 7 (refresh token TTL, OTP TTL, pub/sub)
- **Auth:** JWT (python-jose), bcrypt passwords (pre-SHA256 hashed), Redis stores refresh tokens
- **Notifications:** AWS SNS (SMS) + AWS SES (email) via `boto3` — currently DISABLED in most deployments (mock mode)
- **ML:** XGBoost `.pkl` model files loaded directly in-process; `donor_ranking_xgboost.pkl` + `thalassemia_units_xgboost.pkl`
- **Chatbot:** Mistral AI LLM + LangChain + FAISS vector store + Sentence Transformers + Sarvam AI (Indian language translation) — all loaded in the same process
- **Real-time:** WebSocket chat (FastAPI WebSocket routes), Redis pub/sub for multi-worker scaling
- **Frontend:** React 19 + TypeScript + Vite + Tailwind CSS + React Leaflet (maps) + MUI

### Current Monolith File Structure
```
backend/
  app/
    main.py                     # ALL 13 routers registered here
    core/
      config.py                 # Pydantic Settings — all env vars
      database.py               # SQLAlchemy engine (single DB)
      security.py               # JWT + bcrypt helpers
      dependencies.py           # get_db, get_current_user, require_roles
      sns_service.py            # AWS SNS SMS + AWS SES email (boto3)
    websocket/
      manager.py                # ConnectionManager (WebSocket rooms)
      pubsub.py                 # Redis pub/sub bridge
    modules/
      auth/                     # routes.py, service.py, schemas.py
      users/                    # routes.py, service.py, models.py
      donors/                   # routes.py, service.py, models.py, repository.py
      patients/                 # routes.py, service.py, models.py, repository.py
      blood_requests/           # routes.py, service.py, models.py, repository.py, schemas.py
      notifications/            # routes.py, service.py, models.py
      chat/                     # routes.py, service.py, models.py (WebSocket)
      blood_bank/               # routes.py, service.py, models.py, repository.py
      coordinator/              # routes.py, service.py
      ml/                       # routes.py, service.py (XGBoost inference)
      leaderboard/              # routes.py, service.py, models.py
      transfusion/              # routes.py, service.py, models.py (thalassemia model)
      chatbot/                  # routes.py, intent_router.py, rag_service.py,
                                #   mistral_service.py, translation_service.py,
                                #   platform_adapter.py, embedding_service.py
                                #   vectorstore/  (FAISS index files)
```

### Current docker-compose.yml (monolith)
```yaml
services:
  db:      # postgres:15, port 5433
  redis:   # redis:7, port 6379
  backend: # single FastAPI container, port 8000
  frontend:# node:20-bullseye, port 5173
```

### Current render.yaml (Render.com deployment)
```yaml
databases:
  - name: raktsaanchar-db   # PostgreSQL free tier
services:
  - type: redis              # Redis free tier
  - type: web                # Single backend Docker container
    name: raktsaanchar-backend
  - type: web (static)       # React SPA
    name: raktsaanchar-frontend
```

---

## SECTION 3 — KEY CODE DETAILS

### 3a. Config (core/config.py)
```python
class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ML_SERVICE_URL: str = "http://ml-service:8002"
    CHATBOT_SERVICE_URL: str = "http://chatbot:8001"
    AWS_ACCESS_KEY_ID: str = "mock"
    AWS_SECRET_ACCESS_KEY: str = "mock"
    AWS_REGION: str = "us-east-1"
    AWS_SNS_TOPIC_ARN: str = ""
    AWS_SNS_ENABLED: bool = False
    AWS_SES_SENDER: str = "no-reply@raktsaanchar.org"
```

### 3b. SNS/SES Service (core/sns_service.py) — TO BE REPLACED
The `SnsService.send_sns_notification()` method is called in:
1. **`auth/service.py`** — OTP email on register & resend_otp
2. **`notifications/service.py`** — SMS + email alerts to:
   - Coordinators (new request created)
   - Matched donors (urgent + normal requests)
   - Blood banks (urgent proximity alerts, inventory match alerts)

Call signature:
```python
SnsService.send_sns_notification(
    phone="+91XXXXXXXXXX",   # optional E.164 format
    email="user@example.com", # optional
    subject="RaktSaanchar: ...",
    message="fallback text",
    sms_message="short SMS text",
    email_body="long email body"
)
```

### 3c. Auth Flow
1. `POST /api/v1/auth/register` → create User + seed Patient/Donor profile + generate OTP → store in Redis (`verify:{email}` key, 600s TTL) → send OTP via email
2. `POST /api/v1/auth/verify` → check Redis OTP → mark `user.is_verified = True`
3. `POST /api/v1/auth/login` → verify password → create JWT access + refresh tokens → store refresh in Redis (`refresh:{user_id}`)
4. `POST /api/v1/auth/refresh` → verify refresh token from Redis → issue new access token
5. `POST /api/v1/auth/logout` → delete Redis key

### 3d. ML Service (modules/ml/service.py)
- Loads `donor_ranking_xgboost.pkl` + `feature_columns.pkl` at startup
- `rank_donors(db, blood_group, urgency, units, city, lat, lon, limit)` → returns ranked list of donors
- Also provides `get_geojson_map_data(db)` for the coordinator map view
- Called from `notifications/service.py` synchronously on every blood request creation

### 3e. Chatbot (modules/chatbot/)
- `TranslationService.translate_to_english(text)` → Sarvam AI API call
- `IntentRouter.get_intent(text)` → classifies to PLATFORM | RAG | GENERAL
- PLATFORM actions: DONOR_PROFILE, PATIENT_PROFILE, MY_REQUESTS, DONOR_LEADERBOARD, VALIDATION_REPORTS, NOTIFICATIONS, INVENTORY, NEAREST_BLOOD_BANK, DASHBOARD, ACTIVE_REQUESTS
- `PlatformAdapter.{action}(db, user_id)` → fetches live DB data
- `rag_service.get_response(text)` → FAISS vector search + Mistral LLM
- `generate_response(prompt)` → direct Mistral LLM call
- `TranslationService.translate_from_english(text, lang)` → Sarvam AI back to user language

### 3f. Notification Logic (notifications/service.py)
On `notify_request_created(request)`:
1. Notify patient (in-app)
2. Notify all coordinators (in-app + email + SMS)
3. Run ML ranking to get top 10 donors
4. Notify each matched donor (in-app + email + SMS), filtering by distance for urgent
5. If urgent: notify blood banks within 100km (in-app + email + SMS)
6. If not urgent: check nearby bank inventory, notify bank with stock (in-app + email + SMS)

### 3g. WebSocket Chat
- Route: `WS /api/v1/chat/ws/{room_id}?token={jwt}`
- `ConnectionManager` holds in-memory dict: `room_id → Set[WebSocket]`
- Redis pub/sub used to bridge multiple Uvicorn workers
- Chat rooms auto-created when donor accepts blood request

### 3h. Database Models (all in single PostgreSQL DB)
Tables: `users`, `donors`, `patients`, `blood_requests`, `notifications`, `chat_rooms`, `chat_messages`, `badges`, `donor_badges`, `blood_inventory`, `blood_units`, `blood_validation_reports`, `blood_bank_profiles`, `transfusion_predictions`

---

## SECTION 4 — MIGRATION TARGET: MICROSERVICES ARCHITECTURE

### 4.1 Service Decomposition

Decompose into **6 microservices** + 1 message broker + shared infrastructure:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                │
│   React SPA (unchanged frontend)                                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS / WebSocket
┌──────────────────────────────▼──────────────────────────────────────┐
│                       API GATEWAY (Nginx or Traefik)                │
│   Route /api/v1/auth/*       → auth-service:8001                   │
│   Route /api/v1/users/*      → auth-service:8001                   │
│   Route /api/v1/donors/*     → core-service:8002                   │
│   Route /api/v1/patients/*   → core-service:8002                   │
│   Route /api/v1/requests/*   → core-service:8002                   │
│   Route /api/v1/notifications/* → notification-service:8003        │
│   Route /api/v1/chat/*       → chat-service:8004 (WS upgrade too)  │
│   Route /api/v1/blood-bank/* → core-service:8002                   │
│   Route /api/v1/coordinator/*→ core-service:8002                   │
│   Route /api/v1/ml/*         → ml-service:8005                     │
│   Route /api/v1/leaderboard/*→ core-service:8002                   │
│   Route /api/v1/transfusion/*→ ml-service:8005                     │
│   Route /api/v1/chatbot/chat → chatbot-service:8006                │
└─────┬────────────┬───────────┬──────────┬──────────┬───────────────┘
      │            │           │          │          │
 auth-svc    core-svc   notif-svc   chat-svc   ml-svc   chatbot-svc
  :8001       :8002      :8003       :8004      :8005     :8006
      │            │           │          │          │
      └────────────┴─────┬─────┴──────────┘          │
                         │                           │
                 RabbitMQ / Redis Streams             │
                  (Message Broker)                    │
                         │                           │
               ┌─────────┴──────────┐               │
          PostgreSQL            PostgreSQL        PostgreSQL
          (auth DB)           (core/notif DB)    (ml/chatbot DB)
```

### 4.2 The 6 Microservices

#### SERVICE 1: `auth-service` (port 8001)
**Owns:** auth + users modules
**Endpoints:**
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/verify`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/resend-otp`
- `GET/PUT /api/v1/users/me`
- `GET /api/v1/users/{id}` (internal use)
**DB Tables:** `users`
**Redis:** OTP keys, refresh token keys
**Publishes events to broker:**
  - `user.registered` → `{user_id, email, phone, full_name, role}`
  - `otp.send` → `{email, otp_code, full_name}` (triggers notification-service to send email)
**Dependencies:** Redis, PostgreSQL (auth DB)
**Note:** On startup, publish a `user.registered` event; other services cache basic user info. Auth service is the **token issuer** — all other services validate JWT locally (shared `SECRET_KEY`).

#### SERVICE 2: `core-service` (port 8002)
**Owns:** donors, patients, blood_requests, blood_bank, coordinator, leaderboard modules
**Endpoints:** All `/api/v1/donors/*`, `/api/v1/patients/*`, `/api/v1/requests/*`, `/api/v1/blood-bank/*`, `/api/v1/coordinator/*`, `/api/v1/leaderboard/*`
**DB Tables:** `donors`, `patients`, `blood_requests`, `blood_bank_profiles`, `blood_inventory`, `blood_units`, `blood_validation_reports`, `badges`, `donor_badges`
**Calls to other services (HTTP):**
  - `ml-service:8005 GET /internal/rank-donors` — to get ranked donors on request creation
**Publishes events to broker:**
  - `blood_request.created` → `{request_id, blood_group, urgency, units, patient_id, patient_city, patient_lat, patient_lon, hospital}`
  - `blood_request.matched` → `{request_id, donor_user_id, patient_user_id}`
  - `blood_request.accepted` → `{request_id, donor_user_id, patient_user_id}`
  - `blood_request.fulfilled` → `{request_id, donor_user_id, patient_user_id, donor_id}`
  - `badge.awarded` → `{donor_user_id, badge_name, badge_icon}`
**Consumes events from broker:**
  - `user.registered` → cache basic user info locally (email, phone, role)

#### SERVICE 3: `notification-service` (port 8003)
**Owns:** notifications module
**Endpoints:** `GET/POST /api/v1/notifications/*`
**DB Tables:** `notifications`
**Consumes events from broker:**
  - `blood_request.created` → triggers donor/coordinator/blood_bank alerts (in-app + email + SMS)
  - `blood_request.matched` → in-app notifications
  - `blood_request.accepted` → in-app notifications
  - `blood_request.fulfilled` → in-app notifications
  - `badge.awarded` → in-app notification
  - `otp.send` → sends OTP email
**Free notification stack (replaces AWS SNS + SES):**
  - **Email:** SMTP via `aiosmtplib` / `smtplib` using Gmail SMTP (free), Brevo free tier, or Mailpit (local)
  - **SMS/Push:** `ntfy.sh` (free hosted push, no account needed) or self-hosted Gotify
**Dependencies:** PostgreSQL (notifications DB), message broker

#### SERVICE 4: `chat-service` (port 8004)
**Owns:** chat module + real-time connection manager
**Endpoints:**
  - `POST /api/v1/chat/rooms` — create a chat room
  - `GET /api/v1/chat/rooms` — list user's rooms
  - `GET /api/v1/chat/rooms/{room_id}/messages` — message history
  - `WS /api/v1/chat/ws/{room_id}?token={jwt}` — WebSocket (existing)
  - `POST /api/v1/chat/internal/create-room` — internal endpoint called by core-service or RabbitMQ consumer
**DB Tables:** `chat_rooms`, `chat_messages`
**Redis:** pub/sub for multi-worker WebSocket bridge (already implemented in current codebase via `websocket/pubsub.py`)
**JWT validation:** Decode JWT locally using shared `SECRET_KEY` (no auth-service call needed)

**⚠️ Socket.IO note:** The standalone `Chatbot/requirements.txt` has `python-socketio` + `fastapi-socketio`. This means the original chatbot used Socket.IO, not raw WebSockets. For the `chat-service`, you have two options:
- **Option A (Recommended):** Keep raw FastAPI WebSocket (already in `backend/app/modules/chat/`) — simpler, no extra deps
- **Option B:** Migrate to Socket.IO (`python-socketio`) for rooms, namespaces, and reconnection support — better mobile/browser compatibility

If choosing Option B, add to `requirements.txt`: `python-socketio[asyncio_client]`, `fastapi-socketio`

**🔑 Key flow — Donor Accepts → Chat Room Auto-Created:**

This is the critical integration point. When a **donor accepts** a blood request, a private chat room must be auto-created between the donor and patient so they can coordinate.

```
[core-service]                     [chat-service]                    [Users]
    │                                    │
    │ donor calls POST /requests/{id}/accept
    │ → updates DB: status=accepted      │
    │ → publishes to RabbitMQ:           │
    │   event=blood_request.accepted     │
    │   { request_id, donor_user_id,     │
    │     patient_user_id,               │
    │     donor_name, patient_name }     │
    │                                    │
    │                          [consumer.py listens]
    │                                    │
    │                          Creates chat_room row:
    │                          { request_id, donor_user_id,
    │                            patient_user_id, created_at }
    │                                    │
    │                          Sends in-app push (ntfy.sh)
    │                          to both donor + patient:
    │                          "💬 Chat room opened! Coordinate
    │                           your donation here."
    │                                    │
    │               Donor opens WS /chat/ws/{room_id}?token=...
    │               Patient opens WS /chat/ws/{room_id}?token=...
    │                          Real-time messaging begins ✅
```

**RabbitMQ consumer in chat-service:**
```python
# chat-service/app/messaging/consumer.py
async def handle_blood_request_accepted(event: dict):
    request_id = event["request_id"]
    donor_user_id = event["donor_user_id"]
    patient_user_id = event["patient_user_id"]

    # Idempotent: don't create duplicate rooms
    existing = db.query(ChatRoom).filter(
        ChatRoom.request_id == request_id
    ).first()
    if existing:
        return

    room = ChatRoom(
        request_id=request_id,
        donor_user_id=donor_user_id,
        patient_user_id=patient_user_id,
    )
    db.add(room)
    db.commit()

    # Push notification to both parties via ntfy.sh
    PushService.send_push(
        user_id=donor_user_id,
        title="💬 Chat Room Ready",
        message=f"A chat room has been opened with your patient. Open the app to coordinate!"
    )
    PushService.send_push(
        user_id=patient_user_id,
        title="💬 Donor is Ready to Chat",
        message=f"Your matched donor has accepted. Open the app to chat and coordinate!"
    )
```

**Consumes events from broker:**
  - `blood_request.accepted` → **auto-create chat room for donor ↔ patient + push notification to both**

#### SERVICE 5: `ml-service` (port 8005)
**Owns:** ml module + transfusion module
**Endpoints:**
  - `GET /api/v1/ml/rank-donors` (public, auth required)
  - `GET /api/v1/ml/map-data` (coordinator map GeoJSON)
  - `POST /api/v1/transfusion/predict`
  - `GET /internal/rank-donors` (internal, no auth — only callable from core-service)
**DB Access:** Read-only access to `donors`, `patients`, `blood_requests` tables (via core DB connection string)
**Model files:** `donor_ranking_xgboost.pkl`, `feature_columns.pkl`, `thalassemia_units_xgboost.pkl`
**Dependencies:** PostgreSQL (read-only), XGBoost, scikit-learn, pandas

#### SERVICE 6: `chatbot-service` (port 8006)
**Owns:** chatbot module
**Endpoints:**
  - `POST /api/v1/chatbot/chat`
**DB Access:** ❌ **NO direct DB access.** All platform data is fetched via HTTP calls to `core-service` REST API.
**External APIs:** Mistral AI, Sarvam AI
**Local models:** FAISS vector store, Sentence Transformers
**Dependencies:** Redis (optional response caching), mistralai, sarvamai, langchain, faiss-cpu, sentence-transformers, httpx

**PlatformAdapter redesign (API-based, not DB-based):**
```python
# chatbot-service/app/platform_adapter.py
import httpx
import os

CORE_SERVICE_URL = os.getenv("CORE_SERVICE_URL", "http://core-service:8002")

class PlatformAdapter:
    @staticmethod
    async def _get(path: str, token: str) -> dict:
        """Calls core-service with the user's JWT — preserves auth context."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{CORE_SERVICE_URL}{path}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    async def get_donor_profile(token: str) -> dict:
        return await PlatformAdapter._get("/api/v1/donors/me", token)

    @staticmethod
    async def get_patient_profile(token: str) -> dict:
        return await PlatformAdapter._get("/api/v1/patients/me", token)

    @staticmethod
    async def get_my_requests(token: str) -> dict:
        return await PlatformAdapter._get("/api/v1/requests/my", token)

    @staticmethod
    async def get_donor_leaderboard(token: str) -> dict:
        return await PlatformAdapter._get("/api/v1/leaderboard/", token)

    @staticmethod
    async def get_notifications(token: str) -> dict:
        return await PlatformAdapter._get("/api/v1/notifications/", token)

    @staticmethod
    async def get_inventory(token: str) -> dict:
        return await PlatformAdapter._get("/api/v1/blood-bank/inventory", token)

    @staticmethod
    async def get_nearest_blood_banks(token: str) -> dict:
        return await PlatformAdapter._get("/api/v1/blood-bank/nearest", token)

    @staticmethod
    async def get_active_requests(token: str) -> dict:
        return await PlatformAdapter._get("/api/v1/requests/active", token)

    @staticmethod
    async def get_validation_reports(token: str) -> dict:
        return await PlatformAdapter._get("/api/v1/blood-bank/reports/my", token)

    @staticmethod
    async def get_dashboard(token: str) -> dict:
        return await PlatformAdapter._get("/api/v1/coordinator/dashboard", token)
```

**Updated chatbot route (pass JWT through):**
```python
# chatbot-service/app/modules/chatbot/routes.py
@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
):
    token = credentials.credentials  # forward JWT to core-service
    # ... intent routing ...
    if intent == "PLATFORM":
        if action == "DONOR_PROFILE":
            data = await PlatformAdapter.get_donor_profile(token)
        elif action == "MY_REQUESTS":
            data = await PlatformAdapter.get_my_requests(token)
        # ... etc
```

> **Why API over DB?** The chatbot-service forwards the user's JWT to core-service, so all existing role checks and business logic are automatically respected. No need to duplicate auth logic or maintain a second DB connection string.

---

## SECTION 5 — FREE ALTERNATIVES FOR AWS SNS + SES

### Replace with this free notification stack:

#### EMAIL (replaces AWS SES)
Use **SMTP with Gmail** (free, 500 emails/day) or **Brevo** free tier (300 emails/day):

```python
# notification-service/app/email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

class EmailService:
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "your-gmail@gmail.com")
    SMTP_PASS = os.getenv("SMTP_PASS", "your-app-password")  # Gmail App Password
    SENDER_NAME = os.getenv("SENDER_NAME", "RaktSaanchar")

    @classmethod
    def send_email(cls, to: str, subject: str, body: str) -> bool:
        try:
            msg = MIMEMultipart()
            msg["From"] = f"{cls.SENDER_NAME} <{cls.SMTP_USER}>"
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            with smtplib.SMTP(cls.SMTP_HOST, cls.SMTP_PORT) as server:
                server.starttls()
                server.login(cls.SMTP_USER, cls.SMTP_PASS)
                server.sendmail(cls.SMTP_USER, to, msg.as_string())
            return True
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Email send failed: {e}")
            return False
```

**Setup for Gmail:** Enable 2FA → Generate App Password → set `SMTP_PASS=<16-char app password>`
**Alternative:** Brevo (formerly Sendinblue) — 300 emails/day free, no credit card, supports SMTP relay

#### SMS/PUSH (replaces AWS SNS)
Use **ntfy.sh** (free, open-source, no account required):

```python
# notification-service/app/push_service.py
import httpx
import os

class PushService:
    NTFY_BASE_URL = os.getenv("NTFY_BASE_URL", "https://ntfy.sh")
    NTFY_TOPIC_PREFIX = os.getenv("NTFY_TOPIC_PREFIX", "raktsaanchar")

    @classmethod
    def send_push(cls, user_id: int, title: str, message: str, priority: str = "default") -> bool:
        """
        Send push notification via ntfy.sh.
        Each user subscribes to topic: raktsaanchar-{user_id}
        Frontend uses ntfy.js or native browser push to subscribe.
        """
        topic = f"{cls.NTFY_TOPIC_PREFIX}-{user_id}"
        try:
            response = httpx.post(
                f"{cls.NTFY_BASE_URL}/{topic}",
                content=message,
                headers={
                    "Title": title,
                    "Priority": priority,  # "urgent", "high", "default", "low", "min"
                    "Tags": "drop_of_blood",
                },
                timeout=5.0
            )
            return response.status_code == 200
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Push send failed: {e}")
            return False

    @classmethod
    def send_urgent(cls, user_id: int, title: str, message: str) -> bool:
        return cls.send_push(user_id, title, message, priority="urgent")
```

**Frontend ntfy subscription (React):**
```typescript
// In React: subscribe user to their personal topic
useEffect(() => {
  const userId = currentUser?.id;
  if (!userId) return;
  const eventSource = new EventSource(
    `https://ntfy.sh/raktsaanchar-${userId}/sse`
  );
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Show browser notification or in-app toast
    showNotification(data.title, data.message);
  };
  return () => eventSource.close();
}, [currentUser]);
```

**Self-hosting ntfy (optional, fully free):**
```yaml
# In docker-compose.yml
ntfy:
  image: binwiederhier/ntfy
  command: serve
  ports:
    - "8080:80"
  volumes:
    - ./ntfy-data:/var/lib/ntfy
  environment:
    NTFY_BASE_URL: http://ntfy:80
```

#### UNIFIED NOTIFICATION SERVICE
```python
# notification-service/app/notifier.py
class Notifier:
    @staticmethod
    def send(
        user_id: int = None,
        email: str = None,
        subject: str = "",
        email_body: str = "",
        push_title: str = "",
        push_message: str = "",
        priority: str = "default"
    ):
        if email and email_body:
            EmailService.send_email(to=email, subject=subject, body=email_body)
        if user_id and push_title:
            PushService.send_push(user_id=user_id, title=push_title, message=push_message, priority=priority)
```

---

## SECTION 6 — MESSAGE BROKER DESIGN

Use **RabbitMQ** (free, Docker image `rabbitmq:3-management`). Alternative: **Redis Streams** (already in the stack).

### Event Schema

All events are JSON published to topic exchanges:

```python
# shared/events.py

# blood_request.created
{
    "event": "blood_request.created",
    "request_id": int,
    "blood_group": str,          # "A+", "O-", etc.
    "urgency": str,              # "low"|"medium"|"high"|"critical"
    "units_required": int,
    "patient_id": int,
    "patient_user_id": int,
    "patient_city": str | None,
    "patient_lat": float | None,
    "patient_lon": float | None,
    "hospital": str,
    "top_donors": list[dict]     # pre-ranked by ml-service (injected by core-service)
}

# otp.send
{
    "event": "otp.send",
    "user_id": int,
    "email": str,
    "full_name": str,
    "otp_code": str
}

# blood_request.fulfilled
{
    "event": "blood_request.fulfilled",
    "request_id": int,
    "donor_user_id": int,
    "patient_user_id": int,
    "donor_id": int
}
```

### RabbitMQ Config
```yaml
rabbitmq:
  image: rabbitmq:3-management
  ports:
    - "5672:5672"    # AMQP
    - "15672:15672"  # Management UI (admin/admin)
  environment:
    RABBITMQ_DEFAULT_USER: rakt
    RABBITMQ_DEFAULT_PASS: rakt
```

Use `aio-pika` (async) in Python services:
```python
# pip install aio-pika
import aio_pika
import json

async def publish_event(exchange_name: str, routing_key: str, payload: dict):
    connection = await aio_pika.connect_robust("amqp://rakt:rakt@rabbitmq/")
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(exchange_name, aio_pika.ExchangeType.TOPIC, durable=True)
        await exchange.publish(
            aio_pika.Message(body=json.dumps(payload).encode()),
            routing_key=routing_key
        )
```

---

## SECTION 7 — DATABASE STRATEGY

### Option A: Shared Database, Separate Schemas (Recommended for this project size)
Keep ONE PostgreSQL instance but use separate schemas per service:
- `auth` schema → `users`
- `core` schema → `donors`, `patients`, `blood_requests`, `blood_bank_profiles`, `blood_inventory`, `blood_units`, `blood_validation_reports`, `badges`, `donor_badges`
- `notifications` schema → `notifications`
- `chat` schema → `chat_rooms`, `chat_messages`
- `ml` schema → `transfusion_predictions`

Each service gets its own DB connection string:
```
DATABASE_URL=postgresql://user:pass@db:5432/rakt?options=-csearch_path=auth
```

### Option B: Separate Databases per Service (Full isolation)
```yaml
db-auth:  postgres:15, POSTGRES_DB=rakt_auth
db-core:  postgres:15, POSTGRES_DB=rakt_core
db-notif: postgres:15, POSTGRES_DB=rakt_notif
db-chat:  postgres:15, POSTGRES_DB=rakt_chat
db-ml:    postgres:15, POSTGRES_DB=rakt_ml
```

**Recommendation: Use Option A** for this project to avoid cross-service joins and simplify migration. The ML service and chatbot-service can still use read-only connections to the core schema.

---

## SECTION 8 — FULL docker-compose.yml (TARGET)

```yaml
version: "3.9"

networks:
  rakt-net:
    driver: bridge

volumes:
  db_data:
  rabbitmq_data:
  ntfy_data:

services:
  # ── Infrastructure ────────────────────────────────────────────────────────
  
  db:
    image: postgres:15
    networks: [rakt-net]
    environment:
      POSTGRES_USER: rakt
      POSTGRES_PASSWORD: rakt
      POSTGRES_DB: raktsaanchar
    volumes:
      - db_data:/var/lib/postgresql/data
      - ./infra/init.sql:/docker-entrypoint-initdb.d/init.sql  # creates schemas
    ports:
      - "5433:5432"

  redis:
    image: redis:7-alpine
    networks: [rakt-net]
    ports:
      - "6379:6379"

  rabbitmq:
    image: rabbitmq:3-management
    networks: [rakt-net]
    environment:
      RABBITMQ_DEFAULT_USER: rakt
      RABBITMQ_DEFAULT_PASS: rakt
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    ports:
      - "5672:5672"
      - "15672:15672"   # RabbitMQ management UI

  ntfy:
    image: binwiederhier/ntfy
    command: serve
    networks: [rakt-net]
    volumes:
      - ntfy_data:/var/lib/ntfy
    ports:
      - "8080:80"

  # ── API Gateway ────────────────────────────────────────────────────────────
  
  gateway:
    image: nginx:alpine
    networks: [rakt-net]
    ports:
      - "80:80"
    volumes:
      - ./infra/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - auth-service
      - core-service
      - notification-service
      - chat-service
      - ml-service
      - chatbot-service

  # ── Microservices ────────────────────────────────────────────────────────
  
  auth-service:
    build:
      context: ./services/auth-service
      dockerfile: Dockerfile
    networks: [rakt-net]
    environment:
      DATABASE_URL: postgresql://rakt:rakt@db:5432/raktsaanchar?options=-csearch_path=auth,public
      REDIS_URL: redis://redis:6379
      RABBITMQ_URL: amqp://rakt:rakt@rabbitmq/
      SECRET_KEY: ${SECRET_KEY}
      ALGORITHM: HS256
      SMTP_HOST: smtp.gmail.com
      SMTP_PORT: "587"
      SMTP_USER: ${SMTP_USER}
      SMTP_PASS: ${SMTP_PASS}
    depends_on: [db, redis, rabbitmq]
    ports:
      - "8001:8001"

  core-service:
    build:
      context: ./services/core-service
      dockerfile: Dockerfile
    networks: [rakt-net]
    environment:
      DATABASE_URL: postgresql://rakt:rakt@db:5432/raktsaanchar?options=-csearch_path=core,public
      REDIS_URL: redis://redis:6379
      RABBITMQ_URL: amqp://rakt:rakt@rabbitmq/
      SECRET_KEY: ${SECRET_KEY}
      ML_SERVICE_URL: http://ml-service:8005
    depends_on: [db, redis, rabbitmq, ml-service]
    ports:
      - "8002:8002"

  notification-service:
    build:
      context: ./services/notification-service
      dockerfile: Dockerfile
    networks: [rakt-net]
    environment:
      DATABASE_URL: postgresql://rakt:rakt@db:5432/raktsaanchar?options=-csearch_path=notifications,public
      CORE_DB_URL: postgresql://rakt:rakt@db:5432/raktsaanchar?options=-csearch_path=core,public
      RABBITMQ_URL: amqp://rakt:rakt@rabbitmq/
      SECRET_KEY: ${SECRET_KEY}
      SMTP_HOST: smtp.gmail.com
      SMTP_PORT: "587"
      SMTP_USER: ${SMTP_USER}
      SMTP_PASS: ${SMTP_PASS}
      NTFY_BASE_URL: http://ntfy:80
      NTFY_TOPIC_PREFIX: raktsaanchar
    depends_on: [db, rabbitmq, ntfy]
    ports:
      - "8003:8003"

  chat-service:
    build:
      context: ./services/chat-service
      dockerfile: Dockerfile
    networks: [rakt-net]
    environment:
      DATABASE_URL: postgresql://rakt:rakt@db:5432/raktsaanchar?options=-csearch_path=chat,public
      REDIS_URL: redis://redis:6379
      RABBITMQ_URL: amqp://rakt:rakt@rabbitmq/
      SECRET_KEY: ${SECRET_KEY}
    depends_on: [db, redis, rabbitmq]
    ports:
      - "8004:8004"

  ml-service:
    build:
      context: ./services/ml-service
      dockerfile: Dockerfile
    networks: [rakt-net]
    environment:
      DATABASE_URL: postgresql://rakt:rakt@db:5432/raktsaanchar?options=-csearch_path=core,public
      SECRET_KEY: ${SECRET_KEY}
    depends_on: [db]
    ports:
      - "8005:8005"
    volumes:
      - ./models:/app/models:ro   # .pkl files

  chatbot-service:
    build:
      context: ./services/chatbot-service
      dockerfile: Dockerfile
    networks: [rakt-net]
    environment:
      DATABASE_URL: postgresql://rakt:rakt@db:5432/raktsaanchar?options=-csearch_path=core,public
      REDIS_URL: redis://redis:6379
      SECRET_KEY: ${SECRET_KEY}
      MISTRAL_API_KEY: ${MISTRAL_API_KEY}
      SARVAM_API_KEY: ${SARVAM_API_KEY}
    depends_on: [db, redis]
    ports:
      - "8006:8006"

  # ── Frontend ──────────────────────────────────────────────────────────────
  
  frontend:
    image: node:20-bullseye
    working_dir: /app
    networks: [rakt-net]
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "5173:5173"
    command: sh -c "npm install --legacy-peer-deps && npm run dev -- --host 0.0.0.0"
    environment:
      VITE_API_BASE_URL: http://localhost/api/v1
      VITE_WS_URL: ws://localhost/api/v1/chat/ws
    depends_on: [gateway]
```

---

## SECTION 9 — NGINX GATEWAY CONFIG

```nginx
# infra/nginx.conf
events { worker_connections 1024; }

http {
    upstream auth     { server auth-service:8001; }
    upstream core     { server core-service:8002; }
    upstream notif    { server notification-service:8003; }
    upstream chat     { server chat-service:8004; }
    upstream ml       { server ml-service:8005; }
    upstream chatbot  { server chatbot-service:8006; }

    server {
        listen 80;

        location /api/v1/auth/         { proxy_pass http://auth/api/v1/auth/; }
        location /api/v1/users/        { proxy_pass http://auth/api/v1/users/; }
        location /api/v1/donors/       { proxy_pass http://core/api/v1/donors/; }
        location /api/v1/patients/     { proxy_pass http://core/api/v1/patients/; }
        location /api/v1/requests/     { proxy_pass http://core/api/v1/requests/; }
        location /api/v1/blood-bank/   { proxy_pass http://core/api/v1/blood-bank/; }
        location /api/v1/coordinator/  { proxy_pass http://core/api/v1/coordinator/; }
        location /api/v1/leaderboard/  { proxy_pass http://core/api/v1/leaderboard/; }
        location /api/v1/notifications/ { proxy_pass http://notif/api/v1/notifications/; }
        location /api/v1/ml/           { proxy_pass http://ml/api/v1/ml/; }
        location /api/v1/transfusion/  { proxy_pass http://ml/api/v1/transfusion/; }
        location /api/v1/chatbot/      { proxy_pass http://chatbot/api/v1/chatbot/; }

        # WebSocket upgrade for chat
        location /api/v1/chat/ws {
            proxy_pass http://chat/api/v1/chat/ws;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 3600;
        }
        location /api/v1/chat/         { proxy_pass http://chat/api/v1/chat/; }
    }
}
```

---

## SECTION 10 — SERVICE FOLDER STRUCTURE (TARGET)

```
AI4Good_RaktSaanchar/
├── services/
│   ├── auth-service/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/ (config.py, database.py, security.py)
│   │   │   ├── modules/auth/ (routes.py, service.py, schemas.py)
│   │   │   ├── modules/users/ (routes.py, service.py, models.py)
│   │   │   └── messaging/ (publisher.py — publishes otp.send, user.registered)
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── core-service/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/
│   │   │   ├── modules/
│   │   │   │   ├── donors/
│   │   │   │   ├── patients/
│   │   │   │   ├── blood_requests/
│   │   │   │   ├── blood_bank/
│   │   │   │   ├── coordinator/
│   │   │   │   └── leaderboard/
│   │   │   └── messaging/ (publisher.py, consumer.py)
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── notification-service/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/
│   │   │   ├── modules/notifications/ (routes.py, service.py, models.py)
│   │   │   ├── email_service.py       # SMTP (Gmail/Brevo)
│   │   │   ├── push_service.py        # ntfy.sh
│   │   │   ├── notifier.py            # unified send()
│   │   │   └── messaging/ (consumer.py — listens to all events)
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── chat-service/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/
│   │   │   ├── modules/chat/ (routes.py, service.py, models.py)
│   │   │   └── websocket/ (manager.py, pubsub.py)
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── ml-service/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/
│   │   │   ├── modules/ml/ (routes.py, service.py — XGBoost)
│   │   │   └── modules/transfusion/ (routes.py, service.py — thalassemia)
│   │   ├── models/
│   │   │   ├── donor_ranking_xgboost.pkl
│   │   │   ├── feature_columns.pkl
│   │   │   └── thalassemia_units_xgboost.pkl
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── chatbot-service/
│       ├── app/
│       │   ├── main.py
│       │   ├── core/
│       │   └── modules/chatbot/
│       │       ├── routes.py
│       │       ├── intent_router.py
│       │       ├── rag_service.py
│       │       ├── mistral_service.py
│       │       ├── translation_service.py
│       │       ├── platform_adapter.py  # queries core DB read-only
│       │       └── vectorstore/
│       ├── requirements.txt
│       └── Dockerfile
│
├── infra/
│   ├── nginx.conf
│   ├── init.sql           # CREATE SCHEMA auth, core, notifications, chat, ml;
│   └── rabbitmq/
│
├── models/                # Shared .pkl model files (mounted into ml-service)
│   ├── donor_ranking_xgboost.pkl
│   ├── feature_columns.pkl
│   └── thalassemia_units_xgboost.pkl
│
├── frontend/              # Unchanged React SPA
├── docker-compose.yml     # New microservices compose
└── .env                   # Secrets: SECRET_KEY, SMTP_USER, SMTP_PASS, MISTRAL_API_KEY, SARVAM_API_KEY
```

---

## SECTION 11 — ENV VARIABLES SUMMARY (.env)

```bash
# Shared auth secret (ALL services must share this for JWT validation)
SECRET_KEY=change-me-use-a-very-long-random-string

# Email (free SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-gmail@gmail.com
SMTP_PASS=your-16-char-app-password  # Gmail App Password (not your account password)

# ntfy.sh (free push — no key needed for public topics, or use self-hosted)
NTFY_BASE_URL=https://ntfy.sh         # or http://ntfy:80 for self-hosted
NTFY_TOPIC_PREFIX=raktsaanchar-prod   # change per environment

# AI APIs
MISTRAL_API_KEY=your-mistral-api-key
SARVAM_API_KEY=your-sarvam-api-key

# RabbitMQ
RABBITMQ_USER=rakt
RABBITMQ_PASS=rakt

# Remove all AWS vars — no longer needed
```

---

## SECTION 12 — MIGRATION PLAN (STEP-BY-STEP)

### Phase 1: Prepare (no code changes)
1. Add `infra/init.sql` to create PostgreSQL schemas
2. Copy shared security.py and JWT logic to a `shared/` library or duplicate across services
3. Document which DB tables go to which schema

### Phase 2: Extract ML Service first (easiest, no auth needed)
1. Create `services/ml-service/` from `backend/app/modules/ml/` and `backend/app/modules/transfusion/`
2. Add `/internal/rank-donors` endpoint (no auth, internal-only, protected by network)
3. Update `core-service` to call `ML_SERVICE_URL` via `httpx` instead of direct import
4. Test with existing monolith calling the new ML service via HTTP

### Phase 3: Extract Chatbot Service
1. Create `services/chatbot-service/` from `backend/app/modules/chatbot/`
2. Configure read-only DB access to core schema
3. Test chatbot routes independently

### Phase 4: Extract Auth Service
1. Create `services/auth-service/` from `backend/app/modules/auth/` and `backend/app/modules/users/`
2. Replace `SnsService.send_sns_notification()` calls with `EmailService.send_email()` (SMTP)
3. Replace OTP SMS with ntfy.sh push notification
4. Add RabbitMQ publisher for `otp.send`, `user.registered` events

### Phase 5: Extract Notification Service
1. Create `services/notification-service/` from `backend/app/modules/notifications/`
2. Implement RabbitMQ consumer for all events
3. Implement `EmailService` + `PushService` (ntfy.sh)
4. Remove all `boto3` / `SnsService` calls

### Phase 6: Extract Chat Service
1. Create `services/chat-service/` from `backend/app/modules/chat/` + WebSocket manager
2. Add RabbitMQ consumer for `blood_request.accepted` (auto-create room)

### Phase 7: Core Service (remaining modules)
1. The remaining monolith becomes `core-service`
2. Remove chatbot, ml, auth, notification, chat modules
3. Add RabbitMQ publisher for blood request lifecycle events

### Phase 8: Add API Gateway
1. Deploy Nginx with routing config
2. Update frontend `VITE_API_BASE_URL` to point to gateway
3. Test all routes through gateway

### Phase 9: Cleanup
1. Remove `boto3` from all requirements.txt
2. Remove all AWS environment variables
3. Update render.yaml (or k8s manifests) for each service
4. Update README.md

---

## SECTION 13 — WHAT TO GENERATE

Based on everything above, please generate the following files (one at a time, in order):

1. **`infra/init.sql`** — PostgreSQL schema creation script
2. **`infra/nginx.conf`** — Complete Nginx API gateway configuration
3. **`docker-compose.yml`** — Full microservices docker-compose
4. **`.env.example`** — All environment variables with comments
5. **`services/auth-service/app/main.py`** — FastAPI app with auth + users routers
6. **`services/auth-service/app/email_service.py`** — SMTP email (replaces SES)
7. **`services/auth-service/app/messaging/publisher.py`** — RabbitMQ event publisher
8. **`services/auth-service/requirements.txt`**
9. **`services/auth-service/Dockerfile`**
10. **`services/core-service/app/main.py`** — FastAPI app with all core routers
11. **`services/core-service/app/messaging/publisher.py`** — Publishes blood_request events
12. **`services/core-service/requirements.txt`**
13. **`services/notification-service/app/main.py`**
14. **`services/notification-service/app/email_service.py`** — SMTP email
15. **`services/notification-service/app/push_service.py`** — ntfy.sh push
16. **`services/notification-service/app/notifier.py`** — Unified notifier
17. **`services/notification-service/app/messaging/consumer.py`** — RabbitMQ consumer
18. **`services/notification-service/requirements.txt`**
19. **`services/chat-service/app/main.py`**
20. **`services/chat-service/requirements.txt`**
21. **`services/ml-service/app/main.py`**
22. **`services/ml-service/requirements.txt`**
23. **`services/chatbot-service/app/main.py`**
24. **`services/chatbot-service/requirements.txt`**
25. **`frontend/src/hooks/useNtfyPush.ts`** — React hook for ntfy.sh SSE subscription

---

## SECTION 14 — IMPORTANT CONSTRAINTS

1. **JWT is shared**: All services decode JWT using the same `SECRET_KEY` and `ALGORITHM=HS256`. Only `auth-service` issues tokens.
2. **No circular service calls**: Services communicate via RabbitMQ events, not direct HTTP (except `core-service → ml-service` for synchronous ranking).
3. **The frontend does NOT change** its API call structure — the Nginx gateway absorbs all routing. `VITE_API_BASE_URL` just points to the gateway instead of the single backend.
4. **ntfy.sh topics are per-user**: Each user subscribes to `raktsaanchar-{user_id}`. This is the free replacement for SMS/push. The frontend React app must add the `useNtfyPush` hook in `App.tsx`.
5. **Gmail SMTP free tier**: 500 emails/day is sufficient for this use case. Use Gmail App Password, NOT account password.
6. **The ML .pkl model files** stay as files on disk — they are NOT stored in the database. Mount them as Docker volumes.
7. **The FAISS vector store** for the chatbot stays as local files — mount as Docker volume into `chatbot-service`.
8. **Database migration**: Keep ONE PostgreSQL instance with multiple schemas. Do NOT create separate DB servers per service for this project size.
9. **Remove boto3 entirely** from all requirements.txt.
10. **Blood compatibility logic** (`_COMPATIBLE_REVERSE`, `_haversine_distance`) should live in a `shared/` Python package or be duplicated in `core-service` and `notification-service`.
