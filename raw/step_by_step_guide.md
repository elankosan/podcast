# Step-by-Step Guide: Deploying Multi-Lingual Podcast

**Version:** 2.0.0
**Date:** 2026-06-24
**Author:** Selan (Elanko)
**Audience:** Developer deploying and running the application

---

## Overview

This guide walks you through deploying and running the **multi-lingual-podcast** application. It consists of a FastAPI backend, a Next.js frontend, PostgreSQL, Neo4j, and Redis — all orchestrated via Docker Compose. The backend uses the Kimi API (via the `KIMI_API_KEY` environment variable) for LLM-powered research, script generation, and translation.

**Prerequisites:**
- Docker and docker-compose installed
- A Kimi API key (`KIMI_API_KEY`)
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)
- Git

---

## Step 1: Clone the Repository

```bash
git clone <repo-url> /opt/multi-lingual-podcast
cd /opt/multi-lingual-podcast
```

---

## Step 2: Configure Environment Variables

Copy the example environment file and fill in your real values:

```bash
cp .env.example .env
```

Edit `.env` with at least these required values:

```bash
# --- Database ---
POSTGRES_PASSWORD=your-secure-password

# --- Neo4j ---
NEO4J_PASSWORD=your-secure-password

# --- Authentication (JWT) ---
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# --- Kimi LLM (REQUIRED) ---
KIMI_API_KEY=sk-kimi-your-key-here
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_MODEL=moonshot-v1-8k

# --- Cache ---
REDIS_URL=redis://redis:6379/0

# --- Frontend ---
NEXT_PUBLIC_API_URL=http://localhost:8000
ENVIRONMENT=development
LOG_LEVEL=INFO

# --- MAF ---
MAF_WORKFORCE_PATH=/app/workforce.yaml
```

> **Important:** Never commit `.env` to version control. It is already in `.gitignore`.

---

## Step 3: Start Development Infrastructure (Docker Compose)

The development `docker-compose.yml` includes the app, API, PostgreSQL, Neo4j, and Redis. It does **not** include Ollama — the application uses the Kimi API for LLM inference.

```bash
# Start all services
docker-compose up -d

# Verify all services are healthy
docker-compose ps
# Expected: All services show "Up (healthy)" or "Up"

# Check logs if needed
docker-compose logs -f api
docker-compose logs -f app
```

### Development `docker-compose.yml`

```yaml
version: "3.8"

services:
  # --- Frontend (Next.js) ---
  app:
    build: ./app
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - api

  # --- Backend (FastAPI) ---
  api:
    build: ./api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/podcast
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_AUTH=neo4j/podcast_password
      - KIMI_API_KEY=${KIMI_API_KEY}
      - SECRET_KEY=${SECRET_KEY:-your-secret-key-change-me}
      - ALGORITHM=${ALGORITHM:-HS256}
      - ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES:-30}
      - REDIS_URL=redis://redis:6379/0
      - MAF_WORKFORCE_PATH=/app/workforce.yaml
    volumes:
      - ./workforce.yaml:/app/workforce.yaml
      - ./agents:/app/agents
      - ./skills:/app/skills
      - ./policies:/app/policies
      - ./integrations:/app/integrations
    depends_on:
      - postgres
      - neo4j
      - redis

  # --- Database (PostgreSQL) ---
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=podcast
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./api/migrations:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  # --- Knowledge Graph (Neo4j) ---
  neo4j:
    image: neo4j:5.15-community
    environment:
      - NEO4J_AUTH=neo4j/podcast_password
      - NEO4J_dbms_memory_heap_max__size=1G
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - neo4j_data:/data
    ports:
      - "7474:7474"
      - "7687:7687"
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:7474"]
      interval: 10s
      timeout: 5s
      retries: 5

  # --- Cache (Redis) ---
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  neo4j_data:
```

> **Note:** There is no Ollama service. LLM calls are made to the Kimi API using the `KIMI_API_KEY`.

## Production on Shared Host (Existing Traefik + Existing PostgreSQL)

If the host already runs shared infrastructure, use existing-infra deployment mode so this project does **not** create a new Traefik or PostgreSQL container.

1. Create `.env` from `.env.podcast.digity.dev.example`.
2. Set `EXTERNAL_DATABASE_URL` to your existing PostgreSQL service.
3. Set `TRAEFIK_DOCKER_NETWORK` to the existing shared Traefik network (default is `proxy`).
4. Deploy with:

```bash
bash scripts/deploy-existing-infra.sh
# or
make deploy-existing-infra
```

This mode uses `docker-compose.existing-infra.yml` and starts only:
- `api`
- `app`
- `neo4j`
- `redis`

It intentionally does not define or launch `traefik` and `postgres` services.

---

## Step 4: Verify the API

Once containers are running, verify the API health and endpoints:

```bash
# Health check
curl http://localhost:8000/health
# Expected: {"status": "healthy", "services": {"api": {...}, "postgres": {...}, "redis": {...}, "neo4j": {...}}}

# Root endpoint
curl http://localhost:8000/
# Expected: {"message": "Multi-Lingual Podcast API", "version": "1.0.0"}
```

---

## Step 5: Log In and Create Content

### 5.1 Bootstrap First Admin (one-time)

Before first login, create the initial admin user:

```bash
cd api
python bootstrap_admin.py \
  --email admin@digity.dev \
  --name "Podcast Admin" \
  --password 'change-me-strong'
```

### 5.2 Authenticate

Once the admin user exists:

```bash
# Log in and get a JWT token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your-email@example.com&password=your-password"
# Expected: {"access_token": "...", "token_type": "bearer"}

export TOKEN="<access_token>"
```

### 5.3 Create a Podcast

```bash
curl -X POST http://localhost:8000/api/podcasts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "Weekly Perspectives",
    "description": "A multi-lingual podcast on global affairs",
    "language": "en",
    "target_languages": ["fr", "es", "ta"]
  }'
# Returns: {"id": "<podcast-uuid>", "title": "Weekly Perspectives"}

export PODCAST_ID="<podcast-uuid>"
```

### 5.4 Create an Episode

```bash
curl -X POST "http://localhost:8000/api/podcasts/${PODCAST_ID}/episodes" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "AI and Democracy",
    "vision": "Discuss the impact of AI on democratic institutions"
  }'
# Returns: {"id": "<episode-uuid>", "title": "AI and Democracy", "status": "draft"}

export EPISODE_ID="<episode-uuid>"
```

---

## Step 6: Trigger Agent Workflows via API

Instead of running `maf run workforce.yaml`, the backend triggers MAF phases internally via FastAPI endpoints.

### 6.1 Trigger Research

```bash
curl -X POST "http://localhost:8000/api/research/${EPISODE_ID}/research" \
  -H "Authorization: Bearer $TOKEN"
# Returns: {"episode_id": "...", "status": "researching", "trace_id": "...", "result": {...}}
```

Check research status:

```bash
curl "http://localhost:8000/api/research/${EPISODE_ID}/research" \
  -H "Authorization: Bearer $TOKEN"
# Returns: {"episode_id": "...", "status": "researching", "vision": "...", "cost": {...}}
```

### 6.2 Generate Script

```bash
curl -X POST "http://localhost:8000/api/scripts/${EPISODE_ID}/script" \
  -H "Authorization: Bearer $TOKEN"
# Returns: {"episode_id": "...", "status": "scripted", "trace_id": "...", "result": {...}}
```

Get the generated script:

```bash
curl "http://localhost:8000/api/scripts/${EPISODE_ID}/script" \
  -H "Authorization: Bearer $TOKEN"
# Returns: {"episode_id": "...", "version_number": 1, "version_type": "script", "content": "..."}
```

### 6.3 Translate Episode

```bash
# Translate to French
curl -X POST "http://localhost:8000/api/translations/${EPISODE_ID}/translate?language=fr" \
  -H "Authorization: Bearer $TOKEN"
# Returns: {"episode_id": "...", "status": "translated", "language": "fr", "trace_id": "...", "result": {...}}

# Get all translations
curl "http://localhost:8000/api/translations/${EPISODE_ID}/translations" \
  -H "Authorization: Bearer $TOKEN"
# Returns: {"episode_id": "...", "translations": [{"version_number": 1, "content_preview": "..."}]}
```

---

## Step 7: Use the Web UI

Open the Next.js frontend at `http://localhost:3000`.

### UI Pages & Routes

| Page | Route | Purpose |
|------|-------|---------|
| Home | `/` | Landing page with link to dashboard |
| Login | `/login` | JWT authentication |
| Dashboard | `/dashboard` | List podcasts, create new podcast |
| New Podcast | `/podcasts/new` | Podcast creation form |
| Podcast Detail | `/podcasts/[id]` | Episodes list, podcast settings |
| New Episode | `/episodes/new?podcast=<id>` | Episode creation form |
| Episode Detail | `/episodes/[id]` | Research, script, translations tabs |

### Episode Detail Page (`/episodes/[id]`)

The episode page has three tabs:

1. **Research** — Click "🔍 Research Topic" to trigger research via `/api/research/{id}/research`
2. **Script** — Click "📝 Generate Script" to trigger script generation via `/api/scripts/{id}/script`
3. **Translations** — Click language buttons (`fr`, `es`, `ta`, `de`) to trigger translation via `/api/translations/{id}/translate?language=<lang>`

---

## Step 8: API Workflow (Programmatic)

```python
import requests

BASE_URL = "http://localhost:8000"

# Authenticate
resp = requests.post(f"{BASE_URL}/api/auth/login", data={
    "username": "selan@example.com",
    "password": "..."
})
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Create podcast
resp = requests.post(f"{BASE_URL}/api/podcasts", headers=headers, json={
    "title": "Weekly Perspectives",
    "description": "Global affairs podcast",
    "language": "en",
    "target_languages": ["fr", "es", "ta"]
})
podcast_id = resp.json()["id"]

# Create episode
resp = requests.post(
    f"{BASE_URL}/api/podcasts/{podcast_id}/episodes",
    headers=headers,
    json={"title": "AI and Democracy", "vision": "Discuss the impact of AI on democratic institutions"}
)
episode_id = resp.json()["id"]

# Trigger research
requests.post(f"{BASE_URL}/api/research/{episode_id}/research", headers=headers)

# Generate script
requests.post(f"{BASE_URL}/api/scripts/{episode_id}/script", headers=headers)

# Translate to French
requests.post(f"{BASE_URL}/api/translations/{episode_id}/translate?language=fr", headers=headers)

# Get script
resp = requests.get(f"{BASE_URL}/api/scripts/{episode_id}/script", headers=headers)
script = resp.json()["content"]

# Get translations
resp = requests.get(f"{BASE_URL}/api/translations/{episode_id}/translations", headers=headers)
translations = resp.json()["translations"]
```

---

## Step 9: Connect to Sphere (Neo4j)

### 9.1 Verify Neo4j Connection

```python
# test_neo4j.py
from api.sphere_sync import PodcastSphereSync

sync = PodcastSphereSync()
health = sync.health_check()
print(f"Neo4j health: {health['status']}")
```

### 9.2 Sync Podcast Data to Sphere

```python
# api/sphere_sync.py (already in the project)
from api.sphere_sync import PodcastSphereSync

def sync_podcast_to_sphere(podcast_id: str):
    """Sync a podcast and its episodes to the Neo4j knowledge graph."""
    sync = PodcastSphereSync()
    sync.sync_podcast(podcast_id)
```

### 9.3 Query Cross-Episode Knowledge

```python
# Search for related episodes by topic
def search_episodes_by_topic(topic: str):
    sync = PodcastSphereSync()
    return sync.search_by_topic(topic)
```

---

## Step 10: Monitoring & Maintenance

### Check System Health

```bash
# Combined health check
curl http://localhost:8000/health
# Expected: {"status": "healthy" | "degraded", "services": {"api": {...}, "postgres": {...}, "redis": {...}, "neo4j": {...}}}

# Liveness probe (Kubernetes/Docker Swarm)
curl http://localhost:8000/health/live
# Expected: {"status": "alive", "service": "api"}

# Readiness probe
curl http://localhost:8000/health/ready
# Expected: {"status": "ready" | "not_ready", "services": {...}}

# Metrics
curl http://localhost:8000/api/metrics
```

### Check Logs

```bash
# API logs
docker-compose logs -f api

# App logs
docker-compose logs -f app

# All services
docker-compose logs -f
```

### Rebuild After Code Changes

```bash
# Rebuild a specific service
docker-compose build --no-cache api
docker-compose up -d api

# Rebuild everything
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## Step 11: Production Deployment to Hetzner VPS

### 11.1 Provision the VPS

1. Create a new Ubuntu 22.04/24.04 server on Hetzner Cloud
2. Add your SSH key to the server
3. Note the server IP address

### 11.2 Run the Server Bootstrap Script

SSH into the server as `root` and run the setup script:

```bash
# Copy the script to the server
scp scripts/setup-server.sh root@<your-vps-ip>:/root/

# SSH in and run it
ssh root@<your-vps-ip>
chmod +x /root/setup-server.sh
/root/setup-server.sh
```

What `scripts/setup-server.sh` does:
- Updates system packages
- Installs Docker, Docker Compose, git, jq, UFW, fail2ban, logrotate
- Configures UFW (allows 22, 80, 443)
- Configures fail2ban for SSH brute-force protection
- Creates the `podcast` app user and `/opt/multi-lingual-podcast` directory
- Sets up log rotation
- Enables Docker on boot

### 11.3 Configure the Application

Switch to the `podcast` user and clone the repository:

```bash
su - podcast
mkdir -p /opt/multi-lingual-podcast
cd /opt/multi-lingual-podcast
git clone <repo-url> .

# Copy and edit the production environment file
cp .env.example .env
nano .env
```

Set these production values in `.env`:

```bash
# --- Production Domain ---
DOMAIN=your-domain.com
ACME_EMAIL=admin@your-domain.com

# --- Database ---
POSTGRES_PASSWORD=<strong-unique-password>

# --- Neo4j ---
NEO4J_PASSWORD=<strong-unique-password>

# --- Kimi LLM ---
KIMI_API_KEY=sk-kimi-your-production-key

# --- JWT ---
SECRET_KEY=$(openssl rand -hex 32)

# --- Frontend ---
NEXT_PUBLIC_API_URL=https://api.your-domain.com
ENVIRONMENT=production
```

### 11.4 Deploy with `scripts/deploy.sh`

```bash
cd /opt/multi-lingual-podcast
./scripts/deploy.sh
```

What `scripts/deploy.sh` does:
1. Loads environment variables from `.env`
2. Validates required variables (`DOMAIN`, `POSTGRES_PASSWORD`, `NEO4J_PASSWORD`, `KIMI_API_KEY`, `SECRET_KEY`, `ACME_EMAIL`)
3. Pulls the latest Git changes
4. Tags current Docker images for rollback
5. Builds and starts services using `docker-compose.prod.yml`
6. Performs a health check against `https://api.${DOMAIN}/health`
7. **Auto-rollback** if the health check fails after 30 retries
8. Cleans up old images

### 11.5 Production Architecture (`docker-compose.prod.yml`)

The production compose includes:
- **Traefik** — Reverse proxy + Let's Encrypt SSL termination
- **API** — FastAPI with health checks, exposed via `api.${DOMAIN}`
- **App** — Next.js standalone server, exposed via `${DOMAIN}`
- **PostgreSQL** — With health checks and persistent volume
- **Neo4j** — With APOC plugin and health checks
- **Redis** — With AOF persistence and health checks

All services communicate over isolated Docker networks (`frontend`, `backend`).

### 11.6 DNS Configuration

Point these DNS A records to your Hetzner VPS IP:

```
your-domain.com     A  <vps-ip>
api.your-domain.com A  <vps-ip>
traefik.your-domain.com A <vps-ip>  (optional, for Traefik dashboard)
```

SSL certificates are automatically provisioned by Let's Encrypt via Traefik.

### 11.7 GitHub Actions CI/CD

The repository includes `.github/workflows/deploy.yml` for automatic deployment on every push to `main`:

```yaml
name: CD
on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.VPS_SSH_KEY }}" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          ssh-keyscan -H ${{ secrets.VPS_HOST }} >> ~/.ssh/known_hosts
      - name: Deploy to server
        run: |
          ssh -i ~/.ssh/deploy_key ${{ secrets.VPS_USER }}@${{ secrets.VPS_HOST }} \
            'cd /opt/multi-lingual-podcast && ./deploy.sh'
```

Required GitHub Secrets:
- `VPS_SSH_KEY` — Private SSH key for the `podcast` user
- `VPS_HOST` — Your Hetzner VPS IP address
- `VPS_USER` — Usually `podcast`

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `docker-compose up` fails | Port conflicts or Docker daemon not running | Check `docker ps`, free ports 3000, 8000, 5432, 7474, 7687, 6379 |
| Missing `tsconfig.json` | Next.js build fails without TypeScript config | Ensure `app/tsconfig.json` exists and extends `@tsconfig/node20` or similar |
| Wrong TypeScript version | `next build` throws type errors | Use TypeScript `~5.4` or compatible with Next.js 14. Check `package.json` |
| Hardcoded API URLs | Frontend calls wrong backend in production | Set `NEXT_PUBLIC_API_URL` correctly in `.env` and rebuild |
| API returns 401 | JWT token missing or expired | Re-authenticate at `/login`, check `localStorage.token` in browser dev tools |
| API returns 404 | Wrong endpoint path | Verify exact path: `/api/research/{id}/research`, `/api/scripts/{id}/script`, etc. |
| Research returns no output | `KIMI_API_KEY` missing or invalid | Check `.env` has `KIMI_API_KEY`, verify API key with a manual curl to Kimi |
| Translation fails | Episode has no script yet | Generate script first via `/api/scripts/{id}/script`, then translate |
| Neo4j connection refused | Container not healthy or wrong credentials | Check `docker-compose ps`, verify `NEO4J_AUTH` matches `.env` |
| Frontend blank page | Next.js build error or API unreachable | Check `docker-compose logs app`, verify `NEXT_PUBLIC_API_URL` is reachable from browser |
| Cost exceeds budget | Too many LLM calls or large context | Check `/api/metrics`, review `KIMI_MODEL` (use `moonshot-v1-8k` instead of `128k` if possible) |
| Health check fails in production | Traefik not routing, or SSL issue | Verify DNS A records, check `DOMAIN` in `.env`, inspect Traefik logs |
| Deployment rollback triggers | New build fails health check | Check `docker-compose logs api` on the server, fix the error, re-run `./deploy.sh` |

---

## Summary

The actual deployment process for the multi-lingual podcast application is:

1. **Clone** the repository
2. **Configure** `.env` with `KIMI_API_KEY`, database passwords, and JWT secret
3. **Start** development stack with `docker-compose up -d`
4. **Authenticate** via `/api/auth/login` to get a JWT token
5. **Create** podcasts and episodes via REST API (`curl` or UI)
6. **Trigger** agent workflows via FastAPI endpoints:
   - `/api/research/{id}/research` — Research
   - `/api/scripts/{id}/script` — Script generation
   - `/api/translations/{id}/translate?language=fr` — Translation
7. **Browse** the UI at `http://localhost:3000` (routes: `/dashboard`, `/podcasts/[id]`, `/episodes/[id]`)
8. **Deploy** to Hetzner VPS using `scripts/setup-server.sh` + `scripts/deploy.sh`
9. **Monitor** with `/health`, `/health/live`, `/health/ready`, and `/api/metrics`

The backend uses the **Kimi API** (`KIMI_API_KEY`) for all LLM inference. There is no local Ollama instance. The MAF workforce is triggered internally by the FastAPI routers, not via `maf run` CLI commands.

---

**Next Step:** Copy `.env.example` to `.env`, fill in your `KIMI_API_KEY`, and run `docker-compose up -d`.
