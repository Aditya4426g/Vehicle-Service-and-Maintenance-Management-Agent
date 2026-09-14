# 🚢 Production Deployment & Handover Guide

## Vehicle Service & Maintenance Management Agent
**Engine**: `openai/gpt-oss-120b` via Groq  
**Interface**: Streamlit Web Dashboard & CLI Demo  
**Database**: Supabase PostgreSQL  

---

## 1. Pre-Deployment Verification Checklist

Before deploying this application to staging or production, verify each item:

- [x] **Strict Model Constraint**: Only `openai/gpt-oss-120b` is referenced across `config.py`, `agent.py`, `demo.py`, and `app.py`. Zero fallback models exist.
- [x] **Loop Ceiling**: 12-iteration tool execution safety ceiling enforced in `agent.py`.
- [x] **Collision Constraint**: PostgreSQL composite unique constraint `uq_appointment_slot` defined on `(service_center_id, appointment_date, appointment_time)`.
- [x] **Deterministic Separation**: Math, date differences, threshold logic, and coordinate calculations run strictly in Python, not inside LLM prompts.
- [x] **Secrets Sanitization**: No raw API keys, passwords, or production credentials are committed to version control.
- [x] **Git Exclusions**: `.env`, `venv/`, `__pycache__/`, and `.pytest_cache/` properly ignored in `.gitignore`.
- [x] **Automated Tests**: 100% pass rate across all 70 unit, integration, and reliability tests.

---

## 2. Deploying to Streamlit Community Cloud

Streamlit Community Cloud provides a seamless, zero-cost production hosting platform.

### Step 1: Push to GitHub
Ensure all tracked project files are committed and pushed to your remote repository:
```bash
git add .
git commit -m "feat: release v1.0.0 production deployment ready"
git push origin main
```

### Step 2: Connect Repository to Streamlit Cloud
1. Navigate to [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account.
2. Click **"New app"**.
3. Select your repository: `your-username/vehicle-maintenance-agent`.
4. Set **Branch** to `main` (or `master`).
5. Set **Main file path** to `app.py`.

### Step 3: Configure Cloud Secrets
In the Streamlit Cloud deployment dashboard, open **Advanced Settings** $\to$ **Secrets** and paste:
```toml
GROQ_API_KEY = "gsk_your_live_groq_api_key"
GROQ_MODEL = "openai/gpt-oss-120b"
NOMINATIM_USER_AGENT = "vehicle_maintenance_agent_production"

# Optional: Supabase PostgreSQL credentials (leave blank for local seed store)
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-supabase-service-role-key"
```
Click **Save** and **Deploy**.

---

## 3. Containerized Deployment (Docker)

For Kubernetes, AWS ECS, GCP Cloud Run, or Azure App Service, use the following Docker configuration:

### Dockerfile
```dockerfile
FROM python:3.11-slim

# Set system environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose Streamlit default port
EXPOSE 8501

# Healthcheck for container orchestration
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Launch application
CMD ["streamlit", "run", "app.py"]
```

### Build & Run Commands
```bash
# Build image
docker build -t vehicle-maintenance-agent:v1.0.0 .

# Run container with environment variables
docker run -d \
  -p 8501:8501 \
  -e GROQ_API_KEY="gsk_your_live_groq_api_key" \
  -e GROQ_MODEL="openai/gpt-oss-120b" \
  --name maintenance-agent \
  vehicle-maintenance-agent:v1.0.0
```

---

## 4. Production Supabase PostgreSQL Setup

To connect to a live Supabase production database:

1. Create a new project at [supabase.com](https://supabase.com/).
2. Open the **SQL Editor** in the Supabase Dashboard.
3. Paste and execute the contents of [`database/schema.sql`](database/schema.sql).
4. Paste and execute the contents of [`database/seed.sql`](database/seed.sql) for initial personas and demo vehicles.
5. Copy your **Project URL** and **Service Role API Key** from **Project Settings $\to$ API**.
6. Set `SUPABASE_URL` and `SUPABASE_KEY` in your production environment.

---

## 5. Operational Runbook & Troubleshooting

| Scenario | Indicator | Action Required |
|---|---|---|
| **Groq 429 Rate Limit** | Agent log shows `RateLimitError` | Built-in exponential backoff retries automatically. If persistent, increase Groq tier or adjust token limits. |
| **OSM Overpass Timeout** | `Overpass 504 Gateway Timeout` | Built-in fallback retrieves verified local directory records (`osm_101`, `osm_102`, `osm_103`) without impacting user flow. |
| **Slot Collision** | Booking returns `FAILED` | Normal behavior. Inform user slot is taken and propose alternative time slot. |
| **App Startup Failure** | Streamlit shows error on startup | Verify Python version is $\ge 3.10$ and `requirements.txt` installed. |

---

## 6. Handover Summary

- **Codebase Health**: 100% functional, fully tested (70/70 passing tests).
- **Core Orchestrator**: [`agent.py`](agent.py) with typed tool calling and deterministic routing.
- **Frontend Dashboard**: [`app.py`](app.py) with 4-tab modern UI and quick prompts.
- **Automated Verification**: [`demo.py`](demo.py) providing self-contained terminal verification.
- **Primary Maintainer Contacts**: Engineering Team (Members 1, 2, 3, 4).
