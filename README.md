<div align="center">

# 🩸 RaktSaanchar
### *AI-Powered Blood Donation & Coordination Platform*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19+-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com)
[![Render](https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com)

> **AI4Good Hackathon Project** — Bridging the critical gap between blood donors, patients, blood banks, and coordinators using AI, ML, and real-time communication.

[🌐 Live Demo](https://raktsaanchar-frontend.onrender.com) • [📖 API Docs](https://raktsaanchar-backend.onrender.com/docs) • [🐛 Report Bug](https://github.com/abhinandan202004/AI4Good_RaktSaanchar/issues)

</div>

---

## 🌟 What is RaktSaanchar?

RaktSaanchar (*रक्तसंचार* — "blood circulation" in Sanskrit) is a full-stack, AI-powered platform that intelligently connects **blood donors**, **patients**, **blood banks**, and **coordinators** in real time.

It uses **Machine Learning** for smart donor ranking and blood transfusion scheduling, a **Multilingual RAG Chatbot** for patient/donor guidance, **AWS SNS/SES** for real-time notifications, and an **interactive map** for geo-based coordination — all wrapped in a modern, role-based web application.

---

## ✨ Key Features

### 🤖 AI / ML
| Feature | Details |
|---|---|
| **Smart Donor Ranking** | XGBoost model ranks donors by compatibility, proximity, health history & response rate |
| **Transfusion Scheduler** | XGBoost model predicts optimal transfusion schedules for thalassemia patients |
| **Iron Overload Analysis** | ML-driven iron overload risk detection and monitoring |
| **RAG Chatbot** | Multilingual chatbot (English + Indian languages via Sarvam AI) powered by Mistral AI + LangChain + FAISS vector store |

### 👥 Role-Based Dashboards
| Role | Capabilities |
|---|---|
| **Patient** 🏥 | Submit blood requests, track status, view matched donors, AI transfusion scheduling, chat |
| **Donor** 💉 | View & respond to requests, track donation history, earn badges & leaderboard points |
| **Blood Bank** 🏦 | Manage inventory, validate blood units, generate PDF reports, Uber-style donor matching |
| **Coordinator / Admin** 🎯 | Full oversight, map view of all requests, assign blood banks, manage all users |

### 📡 Real-Time & Notifications
- **WebSocket chat** — real-time messaging between patients, donors, and coordinators
- **AWS SNS** — SMS notifications for urgent blood requests
- **AWS SES** — Email notifications for confirmations and updates
- **Live polling** — dashboards auto-refresh for instant status updates

### 🗺️ Maps & Geo-Location
- **Interactive Leaflet map** — visualize blood requests and donors by location
- **Distance-aware matching** — donors ranked by proximity to patient

### 🏆 Gamification
- **Leaderboard** — donors earn points for every donation
- **Badge system** — achievement badges (First Donor, Life Saver, Champion, etc.)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                │
│   React 19 + TypeScript + Tailwind + Vite                           │
│   Subscribes to real-time ntfy.sh server-sent events (SSE)          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS / WebSocket
┌──────────────────────────────▼──────────────────────────────────────┐
│                    API GATEWAY (Nginx)                              │
│   Exposes port 80, routes traffic based on URL path prefixes        │
└──────┬────────────┬───────────┬──────────┬──────────┬───────────────┘
       │            │           │          │          │
  auth-svc    core-svc   notif-svc   chat-svc   ml-svc   chatbot-svc
   :8001       :8002      :8003       :8004      :8005     :8006
       │            │           │          │          │
       └────────────┴─────┬─────┴──────────┘          │
                          │                           │
                   RabbitMQ (Event Broker)            │
                          │                           │
                ┌─────────┴──────────┐                │
             PostgreSQL            Redis         Local Storage
            (5 schemas)      (caching/pubsub)   (.pkl models)
```

---

## 🚀 Quick Start (Local with Docker)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### 1. Clone the repo
```bash
git clone https://github.com/abhinandan202004/AI4Good_RaktSaanchar.git
cd AI4Good_RaktSaanchar
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env and fill in your API keys:
# MISTRAL_API_KEY, SARVAM_API_KEY
```

### 3. Run everything
```bash
docker compose up --build
```

| Service | URL |
|---|---|
| 🌐 Frontend | http://localhost:5173 |
| ⚙️ API Gateway (API Endpoint) | http://localhost/api/v1 |
| 🔔 ntfy.sh UI (Push messages) | http://localhost:8080 |
| 🐇 RabbitMQ Admin UI | http://localhost:15672 (rakt / rakt) |


---

## 🛠️ Tech Stack

### Frontend
| Technology | Purpose |
|---|---|
| React 19 + TypeScript | UI framework |
| Vite 8 | Build tool |
| Tailwind CSS 3 | Styling |
| React Router v7 | Navigation & role guards |
| Axios | HTTP client |
| React Leaflet | Interactive maps |
| MUI (Material UI) | Component library |
| Lucide React | Icons |

### Backend
| Technology | Purpose |
|---|---|
| FastAPI | REST API framework |
| SQLAlchemy + Alembic | ORM & migrations |
| PostgreSQL 15 | Primary database |
| Redis 7 | Caching & pub/sub |
| python-jose + passlib | JWT auth & password hashing |
| boto3 | AWS SDK (SNS, SES) |
| WebSockets | Real-time chat |

### AI / ML
| Technology | Purpose |
|---|---|
| XGBoost | Donor ranking & transfusion prediction |
| scikit-learn | Feature engineering & preprocessing |
| LangChain + LangGraph | RAG chatbot orchestration |
| Mistral AI | LLM for chatbot responses |
| Sarvam AI | Indian language translation |
| FAISS | Vector similarity search |
| Sentence Transformers | Text embeddings |
| PyTorch | ML inference runtime |

---

## 📁 Project Structure

```
AI4Good_RaktSaanchar/
├── frontend/                    # React + Vite SPA
│   ├── src/
│   │   ├── pages/               # Role dashboards
│   │   │   ├── PatientDashboard.tsx
│   │   │   ├── DonorDashboard.tsx
│   │   │   ├── BloodBankDashboard.tsx
│   │   │   ├── CoordinatorDashboard.tsx
│   │   │   ├── ChatRoom.tsx
│   │   │   └── Leaderboard.tsx
│   │   ├── components/          # Shared components
│   │   │   ├── ChatbotWidget.tsx
│   │   │   ├── Navbar.tsx
│   │   │   └── SubNavbar.tsx
│   │   └── services/api.ts      # Axios instance
│   └── package.json
│
├── services/                    # Microservices
│   ├── auth-service/            # Port 8001 (Auth & Users)
│   ├── core-service/            # Port 8002 (Donors, Patients, Requests, Inventory)
│   ├── notification-service/     # Port 8003 (SMTP & ntfy.sh alerts)
│   ├── chat-service/            # Port 8004 (WebSockets & Rooms)
│   ├── ml-service/              # Port 8005 (XGBoost inference)
│   └── chatbot-service/         # Port 8006 (RAG & Translation assistant)
│
├── infra/                       # Infrastructure configuration
│   ├── nginx.conf               # API Gateway router config
│   ├── init.sql                 # PostgreSQL schemas creation
│   └── Dockerfile               # Nginx gateway Dockerfile
│
├── models/                      # Mounted folder for ML .pkl files
├── Chatbot/                     # Original standalone chatbot code (reference)
├── Iron Analysis/               # Iron overload ML module (reference)
├── Patient_Tranfusion_Schedule_Model/  # Transfusion ML model (reference)
├── docker-compose.yml           # Local dev orchestration
└── render.yaml                  # Render deployment blueprint
```

---

## 🌍 Deployment (Render)

This project is deployed on [Render](https://render.com) using a Blueprint (`render.yaml`) that auto-provisions:

| Resource | Type | Plan |
|---|---|---|
| `raktsaanchar-db` | PostgreSQL 15 | Free |
| `raktsaanchar-redis` | Redis 7 | Free |
| `raktsaanchar-gateway` | Docker Web Service (Gateway) | Free |
| `raktsaanchar-auth-service` | Docker Web Service | Free |
| `raktsaanchar-core-service` | Docker Web Service | Free |
| `raktsaanchar-notification-service` | Docker Web Service | Free |
| `raktsaanchar-chat-service` | Docker Web Service | Free |
| `raktsaanchar-ml-service` | Docker Web Service | Free |
| `raktsaanchar-chatbot-service` | Docker Web Service | Free |
| `raktsaanchar-frontend` | Static Site | Free |

### Deploy your own instance
1. Fork this repository
2. Go to [Render Dashboard → Blueprints](https://dashboard.render.com/blueprints/new)
3. Connect your forked repo — Render auto-detects `render.yaml`
4. Click **Apply**
5. Add sensitive env vars in the Render dashboard:
   ```
   MISTRAL_API_KEY
   SARVAM_API_KEY
   AWS_ACCESS_KEY_ID
   AWS_SECRET_ACCESS_KEY
   AWS_SES_SENDER
   AWS_SNS_TOPIC_ARN
   ```

---

## 🔌 API Reference

Full interactive API docs: **https://raktsaanchar-backend.onrender.com/docs**

| Module | Endpoint Prefix | Description |
|---|---|---|
| Auth | `/api/v1/auth` | Register, login, refresh token |
| Users | `/api/v1/users` | Profile management |
| Donors | `/api/v1/donors` | Donor profiles, availability |
| Patients | `/api/v1/patients` | Patient profiles |
| Blood Requests | `/api/v1/requests` | Create/track blood requests |
| Notifications | `/api/v1/notifications` | In-app alerts |
| Chat | `/api/v1/chat` | WebSocket chat rooms |
| Blood Bank | `/api/v1/blood-bank` | Inventory, units, reports |
| Coordinator | `/api/v1/coordinator` | Admin actions |
| ML | `/api/v1/ml` | Donor ranking inference |
| Leaderboard | `/api/v1/leaderboard` | Points & badges |
| Transfusion | `/api/v1/transfusion` | Thalassemia scheduling |
| Chatbot | `/api/v1/chatbot` | RAG chatbot messages |

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'feat: add some feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 👨‍💻 Team

Built with ❤️ for the **AI4Good Hackathon** — using AI to save lives through smarter blood donation coordination.

---

## 📄 License

This project is licensed under the MIT License.

---

<div align="center">
  <sub>Made with ❤️ to bridge the gap in blood donation | AI4Good 2024</sub>
</div>
