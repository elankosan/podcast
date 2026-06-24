# Multi-Lingual Podcast — Architecture

**Project:** multi-lingual-podcast
**Date:** 2026-06-24
**Author:** Selan (Elanko)
**Status:** Architecture Document — Reflects ACTUAL Built Application

---

## System Architecture

The application is built on three layers: **MAF Agent Layer**, **Application Service Layer**, and **Presentation Layer**. The sphere knowledge infrastructure provides the persistent knowledge graph.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER (UI)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Home        │  │  Login       │  │  Dashboard   │  │  Podcast     │    │
│  │  (/)         │  │  (/login)    │  │  (/dashboard)│  │  Detail      │    │
│  │              │  │              │  │              │  │  (/podcasts) │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                       │
│  │  New Podcast │  │  Episode     │  │  New Episode │                       │
│  │  (/podcasts/ │  │  Detail      │  │  (/episodes/ │                       │
│  │   new)       │  │  (/episodes) │  │   new)       │                       │
│  └──────────────┘  └──────────────┘  └──────────────┘                       │
│                                                                             │
│  Auth: Local JWT │ Role-based access control │ Multi-language UI            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼ HTTP / WebSocket
┌─────────────────────────────────────────────────────────────────────────────┐
│                      APPLICATION SERVICE LAYER (FastAPI)                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  REST API                                                           │   │
│  │  ├── /api/auth            (login, me)                               │   │
│  │  ├── /api/admin           (users, roles)                            │   │
│  │  ├── /api/podcasts        (CRUD, episodes)                          │   │
│  │  ├── /api/episodes        (CRUD, versions)                          │   │
│  │  ├── /api/research        (trigger, status)                         │   │
│  │  ├── /api/scripts         (generate, get)                         │   │
│  │  ├── /api/translations    (translate, list)                       │   │
│  │  ├── /api/sphere          (sync, related, knowledge)              │   │
│  │  ├── /api/metrics         (Prometheus metrics)                    │   │
│  │  └── /health, /health/live, /health/ready                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  MAF Integration Layer                                              │   │
│  │  ├── PodcastWorkforce  → loads workforce.yaml, executes phases     │   │
│  │  ├── ResearchAgent     → web research + synthesis                  │   │
│  │  ├── ScriptAgent       → script generation + style enhancement   │   │
│  │  └── TranslationAgent  → multi-language translation + polishing  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Domain Services                                                    │   │
│  │  ├── PodcastService      → manages podcast lifecycle               │   │
│  │  ├── EpisodeService      → manages episodes, versions             │   │
│  │  ├── AuthService         → local auth, JWT, RBAC                  │   │
│  │  └── SphereSyncService   → Neo4j knowledge graph sync              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼ SQL / Cypher / MCP
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA & KNOWLEDGE LAYER                            │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐    │
│  │  PostgreSQL        │  │  Neo4j (sphere)    │  │  File Storage      │    │
│  │  (Relational)      │  │  (Knowledge Graph) │  │  (Local traces)    │    │
│  │  ├── users         │  │  ├── Podcast nodes │  │  ├── runtime_logs  │    │
│  │  ├── podcasts      │  │  ├── Episode nodes │  │  └── workforce.yaml│    │
│  │  ├── episodes      │  │  ├── Topic nodes   │  │                    │    │
│  │  └── versions      │  │  └── Citation edges│  │                    │    │
│  └────────────────────┘  └────────────────────┘  └────────────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  MCP Servers (External Tools)                                       │   │
│  │  ├── llm-mcp         → generate content (Kimi API)                 │   │
│  │  └── neo4j_state     → persist agent state and traces             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼ HTTP / API
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL DATA SOURCES                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│  │  Kimi    │  │  sphere  │  │  Web     │  │  sphere  │                    │
│  │  API     │  │  KG      │  │  Search  │  │  KG      │                    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Detail

### 1. Frontend (Next.js)

| Route | Purpose | Access |
|-------|---------|--------|
| `/` | Landing page — links to dashboard | Public |
| `/login` | Local authentication — email/password + JWT | Public |
| `/dashboard` | Podcast dashboard — list all podcasts, create new | All authenticated |
| `/podcasts/[id]` | Podcast detail — episodes list, create new episode | All authenticated |
| `/podcasts/new` | Create new podcast | All authenticated |
| `/episodes/[id]` | Episode editor — **tabs** for research, script, and translations | All authenticated |
| `/episodes/new` | Create new episode from vision | All authenticated |

> **Note:** The episode detail page (`/episodes/[id]`) uses a **tabbed UI** with three tabs: `research`, `script`, and `translations`. These are NOT separate pages. The user switches between tabs on the same page to trigger research, generate scripts, and request translations.

### 2. Backend (FastAPI)

#### API Endpoints

```python
# Auth (local JWT)
POST   /api/auth/login              → local login (email/password), returns JWT
GET    /api/auth/me                 → current user info

# Admin (admin only)
GET    /api/admin/users             → list all users
POST   /api/admin/users             → create new user
PUT    /api/admin/users/{id}       → update user role
GET    /api/admin/roles             → list hardcoded roles + permissions

# Podcasts
GET    /api/podcasts                → list all podcasts (for current user)
POST   /api/podcasts                → create new podcast
GET    /api/podcasts/{id}           → get podcast detail + episodes
PUT    /api/podcasts/{id}           → update podcast
DELETE /api/podcasts/{id}           → delete podcast
POST   /api/podcasts/{id}/episodes  → create episode under podcast

# Episodes
GET    /api/episodes                → list all episodes
GET    /api/episodes/{id}           → get episode detail
PUT    /api/episodes/{id}           → update episode
DELETE /api/episodes/{id}           → delete episode
GET    /api/episodes/{id}/versions   → list versions for episode
POST   /api/episodes/{id}/versions   → create new version

# Research
POST   /api/research/{id}/research  → trigger MAF research workflow
GET    /api/research/{id}/research   → get research status and cost report

# Scripts
POST   /api/scripts/{id}/script     → trigger MAF script generation
GET    /api/scripts/{id}/script      → get latest script version

# Translations
POST   /api/translations/{id}/translate?language=fr → trigger translation
GET    /api/translations/{id}/translations           → list all translations

# Sphere (Knowledge Graph)
POST   /api/sphere/{id}/sync        → sync episode to Neo4j sphere
GET    /api/sphere/related?topic=... → find related episodes by topic
GET    /api/sphere/{id}/knowledge   → get knowledge graph data for episode
GET    /api/sphere/health           → check Neo4j health

# Metrics & Health
GET    /api/metrics                 → Prometheus metrics (text/plain)
GET    /health                      → combined health check (postgres, redis, neo4j)
GET    /health/live                 → liveness probe (API process running)
GET    /health/ready                → readiness probe (all dependencies healthy)
```

#### MAF Integration

```python
from api.maf_integration import PodcastWorkforce

# The workforce loads workforce.yaml and executes phases
workforce = PodcastWorkforce()

# Phase 3: Research
result = workforce.execute_phase(
    phase="3",
    episode_id=str(episode_id),
    vision=episode.vision,
    podcast_id=str(podcast_id),
)

# Phase 4: Script generation
result = workforce.execute_phase(
    phase="4",
    episode_id=str(episode_id),
    vision=episode.vision,
)

# Phase 5: Translation
result = workforce.execute_phase(
    phase="5",
    episode_id=str(episode_id),
    vision=episode.vision,
    language=language,
)

# Traces are stored in runtime_logs/ for audit
```

### 3. Database Schema (PostgreSQL)

Actual schema as defined by SQLAlchemy models and Alembic migration `0001_initial`:

```sql
-- Users (role is a string, NOT a foreign key to a roles table)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    hashed_password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'host',  -- host, researcher, translator, reader, admin
    created_at TIMESTAMP DEFAULT NOW()
);

-- Podcasts
CREATE TABLE podcasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    language TEXT NOT NULL DEFAULT 'en',
    target_languages JSONB,
    owner_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Episodes
CREATE TABLE episodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    podcast_id UUID NOT NULL REFERENCES podcasts(id),
    title TEXT NOT NULL,
    vision TEXT,
    status TEXT NOT NULL DEFAULT 'draft',  -- draft, researching, scripting, translating, published
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Versions (stores research, script, and translation content — unified table)
CREATE TABLE versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id UUID NOT NULL REFERENCES episodes(id),
    version_number INTEGER NOT NULL,
    version_type TEXT NOT NULL,  -- 'research', 'script', 'translation'
    content JSONB,
    metadata JSONB,  -- e.g. {"language": "fr"}
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

> **Key changes from planned schema:**
> - `users.role` is a **string** column, not a `role_id` foreign key. There is NO separate `roles` table.
> - `versions.version_type` is used, not `versions.type`.
> - There are **NO separate tables** for `research_results`, `scripts`, or `translations`. All content is stored in the unified `versions` table with `version_type` distinguishing the kind.
> - There is NO `activity_log`, `permissions`, or `roles` table.

### 4. Knowledge Graph (Neo4j / sphere)

```cypher
// Podcast nodes
CREATE (p:Podcast {id: 'pod_001', title: 'Weekly Perspectives', language: 'en'})

// Episode nodes
CREATE (e:Episode {id: 'ep_001', title: 'AI and Democracy', status: 'published'})
CREATE (p)-[:HAS_EPISODE]->(e)

// Topic nodes
CREATE (t:Topic {name: 'Artificial Intelligence', category: 'technology'})
CREATE (t2:Topic {name: 'Democracy', category: 'politics'})
CREATE (e)-[:COVERS_TOPIC]->(t)
CREATE (e)-[:COVERS_TOPIC]->(t2)

// Source nodes
CREATE (s:Source {url: 'https://example.com/ai-democracy', title: 'AI and Democratic Institutions', source_type: 'article'})
CREATE (e)-[:CITES_SOURCE]->(s)

// Argument nodes
CREATE (a:Argument {text: 'AI can enhance democratic participation through better information access', stance: 'pro'})
CREATE (a2:Argument {text: 'AI risks centralizing power in the hands of those who control the algorithms', stance: 'con'})
CREATE (e)-[:PRESENTS_ARGUMENT]->(a)
CREATE (e)-[:PRESENTS_ARGUMENT]->(a2)

// Cross-episode knowledge
CREATE (e2:Episode {id: 'ep_002', title: 'Digital Surveillance and Privacy'})
CREATE (e)-[:RELATED_TO {relationship: 'topic_overlap'}]->(e2)
```

---

## Agent Architecture

The application uses a **domain-specific MAF workforce** with exactly **3 agents** that extend the base MAF agents with podcast-specific capabilities.

```
User Vision → PodcastWorkforce → ResearchAgent → ScriptAgent → TranslationAgent → Output
                                      ↓              ↓                ↓
                                runtime_logs   runtime_logs     runtime_logs
```

| Agent | Role | Skills | Podcast Specialization |
|-------|------|--------|------------------------|
| **ResearchAgent** | Research topic and synthesize findings | `synthesis`, `fact_checking` | Uses Kimi API to produce comprehensive research briefs with key facts, arguments, context, quotes, and angles |
| **ScriptAgent** | Format research into polished podcast script | `script_formatting`, `style_enhancement`, `narrative_structure` | Creates structured scripts with INTRO, SEGMENTS, OUTRO; adds [PAUSE], [SFX] markers; applies style enhancement |
| **TranslationAgent** | Translate and culturally adapt scripts | `translation`, `cultural_adaptation`, `linguistic_polishing` | Supports `fr`, `es`, `ta`, `de` with language-specific prompts; extracts cultural notes; two-step translate + polish |

> **Note:** The originally planned agents (Planner, Synthesizer, Stylist, Reviewer, Test Agent, Cost Agent, Governance) are **not implemented**. The 3 agents above cover research, script, and translation end-to-end.

---

## Security Architecture

### Authentication

- **Local auth only** — email/password with bcrypt hashing
- **JWT tokens** (OAuth2PasswordBearer flow) with configurable expiry
- No external OAuth2 providers (Google, GitHub, etc.) are implemented
- Token is stored in `localStorage` on the frontend and sent as `Authorization: Bearer <token>`

### Authorization

- **Role-based access control (RBAC)** via string `role` column on `users` table
- Roles are **hardcoded** in the API (no `roles` / `permissions` tables):

| Role | Podcasts | Episodes | Research | Scripts | Translations | Admin |
|------|----------|----------|----------|---------|--------------|-------|
| **host** | CRUD own | CRUD own | CRUD own | CRUD own | CRUD own | — |
| **researcher** | R | R | CRUD | R | — | — |
| **translator** | R | R | — | R | CRUD | — |
| **reader** | R | R | — | R | R | — |
| **admin** | CRUD all | CRUD all | CRUD all | CRUD all | CRUD all | CRUD |

> **Note:** There is no separate `roles` or `permissions` database table. Roles and their permission definitions are returned by `GET /api/admin/roles` as static JSON.

### Data Protection
- Passwords hashed with bcrypt via `passlib`
- JWT signed with `SECRET_KEY` (HS256)
- All endpoints (except `/` and `/api/auth/login`) require authentication
- Admin endpoints protected by `get_current_admin_user` dependency

---

## Deployment Architecture

Production deployment uses **Traefik v3.1** as a reverse proxy with **Let's Encrypt** automatic SSL, multi-stage Docker builds, non-root container users, and health checks.

### docker-compose.prod.yml (Production)

```yaml
version: "3.9"
services:
  # Traefik (Reverse Proxy + SSL)
  traefik:
    image: traefik:v3.1
    restart: unless-stopped
    command:
      - "--api.dashboard=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.web.http.redirections.entryPoint.to=websecure"
      - "--entrypoints.web.http.redirections.entryPoint.scheme=https"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.email=${ACME_EMAIL}"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--accesslog=true"
      - "--log.level=INFO"
      - "--global.sendAnonymousUsage=false"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - letsencrypt:/letsencrypt
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.traefik.rule=Host(`traefik.${DOMAIN}`)"
      - "traefik.http.routers.traefik.tls.certresolver=letsencrypt"
      - "traefik.http.routers.traefik.entrypoints=websecure"
      - "traefik.http.routers.traefik.service=api@internal"
      - "traefik.http.middlewares.ratelimit.ratelimit.average=100"
      - "traefik.http.middlewares.ratelimit.ratelimit.burst=50"
      - "traefik.http.routers.traefik.middlewares=ratelimit@docker"

  # API (FastAPI)
  api:
    build:
      context: ./api
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/podcast
      - NEO4J_URI=bolt://neo4j:7687
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production
    depends_on:
      postgres: { condition: service_healthy }
      neo4j:    { condition: service_healthy }
      redis:    { condition: service_healthy }
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.${DOMAIN}`)"
      - "traefik.http.routers.api.entrypoints=websecure"
      - "traefik.http.routers.api.tls.certresolver=letsencrypt"
      - "traefik.http.services.api.loadbalancer.server.port=8000"
      - "traefik.http.routers.api.middlewares=ratelimit@docker"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s

  # App (Next.js)
  app:
    build:
      context: ./app
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - NEXT_PUBLIC_API_URL=https://api.${DOMAIN}
      - NODE_ENV=production
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.app.rule=Host(`${DOMAIN}`)"
      - "traefik.http.routers.app.entrypoints=websecure"
      - "traefik.http.routers.app.tls.certresolver=letsencrypt"
      - "traefik.http.services.app.loadbalancer.server.port=3000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s

  # PostgreSQL
  postgres:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=podcast
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d podcast"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Neo4j
  neo4j:
    image: neo4j:5.15-community
    restart: unless-stopped
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:7474 || exit 1"]
      interval: 20s
      timeout: 10s
      retries: 5

  # Redis
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

volumes:
  postgres_data:
  neo4j_data:
  letsencrypt:
```

### Dockerfiles

**API (multi-stage, non-root user, healthcheck):**
```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.11-slim as builder
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
COPY --from=builder /root/.local /home/appuser/.local
RUN chown -R appuser:appgroup /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --chown=appuser:appgroup . .
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**App (multi-stage, non-root user, healthcheck):**
```dockerfile
# syntax=docker/dockerfile:1
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --only=production

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
RUN apk add --no-cache curl
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
WORKDIR /app
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
USER nextjs
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || curl -f http://localhost:3000 || exit 1
CMD ["node", "server.js"]
```

---

## Alembic Migrations

Database schema changes are managed via **Alembic** (`api/alembic/`). The initial migration (`0001_initial`) creates all four tables (`users`, `podcasts`, `episodes`, `versions`).

```bash
# Generate a new migration
cd api && alembic revision --autogenerate -m "add new column"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

For development, `Base.metadata.create_all(bind=engine)` is run on startup as a safety net. Production deployments should use `alembic upgrade head` in the deployment pipeline.

---

## Prometheus Metrics

The API exposes Prometheus metrics at `/api/metrics` for monitoring and alerting.

**Metrics exposed:**

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `podcast_app_info` | Info | `version`, `language` | Application metadata |
| `podcast_api_requests_total` | Counter | `method`, `endpoint`, `status` | Total API requests |
| `podcast_api_request_duration_seconds` | Histogram | `method`, `endpoint` | Request duration |
| `podcast_agent_executions_total` | Counter | `agent_id`, `phase`, `status` | Agent execution count |

**Grafana / Prometheus scraping:**
- Metrics endpoint: `https://api.${DOMAIN}/api/metrics`
- No authentication required on `/api/metrics` (intended for Prometheus scraper)

---

## Production Deployment Scripts

### `scripts/setup-server.sh` — Hetzner VPS Bootstrap

One-time setup for a fresh Ubuntu 22.04/24.04 VPS:
- Updates system packages
- Installs Docker + Docker Compose
- Configures UFW (firewall) — ports 22, 80, 443
- Installs and configures fail2ban for SSH protection
- Creates `podcast` app user and `/opt/multi-lingual-podcast` directory
- Sets up log rotation
- Enables Docker on boot

### `scripts/deploy.sh` — Zero-Downtime Deployment

Idempotent deployment script:
1. Loads `.env` and validates required variables (`DOMAIN`, `POSTGRES_PASSWORD`, `NEO4J_PASSWORD`, `KIMI_API_KEY`, `SECRET_KEY`, `ACME_EMAIL`)
2. Pulls latest Git changes
3. Tags current Docker images for rollback
4. Builds and starts services via `docker-compose.prod.yml`
5. Performs health check against `https://api.${DOMAIN}/health`
6. **Automatic rollback** if health check fails after 30 retries
7. Cleans up old images

```bash
# Usage on server
./scripts/deploy.sh
```

---

## GitHub Actions CI/CD

### `.github/workflows/ci.yml` — Continuous Integration

Runs on every push / PR to `main`:

**Backend Job:**
- Spins up PostgreSQL 15 and Redis 7 service containers
- Installs Python 3.11 + dependencies
- Lints with `flake8`
- Runs `pytest` with coverage reporting
- Uploads coverage artifacts

**Frontend Job:**
- Installs Node 20 + dependencies (`npm ci`)
- Runs `npm run lint`
- Builds Next.js application

### `.github/workflows/deploy.yml` — Continuous Deployment

Runs on push to `main` (or manual dispatch):
- Checks out repository
- Sets up SSH key from GitHub Secrets (`VPS_SSH_KEY`, `VPS_HOST`, `VPS_USER`)
- SSHs into the Hetzner VPS and runs `./deploy.sh`
- Cleans up SSH key

### `.github/workflows/security.yml` — Security Scanning

Runs on push/PR and weekly (Monday 06:00 UTC):

**Trivy Docker Scan:**
- Builds `api` and `app` Docker images
- Scans both images with Trivy for CVEs
- Uploads SARIF results to GitHub Security tab

**Python Dependency Audit:**
- Runs `pip-audit` on `api/requirements.txt`
- Uploads markdown report as artifact

**SAST (Bandit):**
- Runs `bandit` on `api/` directory
- Uploads JSON report as artifact

---

## Next Step

Proceed to `plan.md` for the implementation roadmap.
