# Multi-Lingual Podcast

A self-hosted, intelligent podcast preparation studio built with **MAF** (Multi-Agent Framework) and **sphere** (knowledge graph). It automates research, synthesis, scriptwriting, translation, and publishing for a weekly multi-language radio show — all through a web UI with authentication, role-based access control, and full audit trails.

**Status:** In Development  
**Version:** 1.0.0  
**Author:** Selan (Elanko)

---

## Features

- **Episode Creation** from a one-sentence vision
- **Automated Research** across web, RSS, and knowledge base
- **Argument Mapping** with pro/con positions and evidence weighting
- **Radio Script Formatting** with timing, segments, and host notes
- **Style Enhancement** with humor, metaphors, and cultural references
- **Multi-Language Translation** with cultural adaptation
- **Publishing Pipeline** to markdown, PDF, HTML, RSS
- **Web UI** for podcast management, editing, and review
- **Authentication & Authorization** with RBAC
- **Knowledge Graph** for cross-episode research and topic discovery
- **Full Audit Trail** of all actions and agent executions
- **Cost Tracking** per episode with budget alerts

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Traefik (HTTPS)                                  │
│                         ┌─────────────────────┐                              │
│                         │  acme@example.com   │                              │
│                         │   :80 / :443        │                              │
│                         └─────────────────────┘                              │
│                                      │                                        │
│            ┌─────────────────────────┼─────────────────────────┐              │
│            ▼                         ▼                         ▼              │
│   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐        │
│   │   Next.js App   │     │  FastAPI API    │     │  Neo4j Browser  │        │
│   │   (Port 3000)   │     │   (Port 8000)   │     │  (Port 7474)    │        │
│   │                 │     │                 │     │                 │        │
│   │  React + SSR    │◄────│  JWT / RBAC     │     │  sphere KG      │        │
│   │  Tailwind CSS   │     │  MAF Runner     │     │  Cypher / APOC  │        │
│   └─────────────────┘     └─────────────────┘     └─────────────────┘        │
│                                    │                                        │
│            ┌───────────────────────┼───────────────────────┐                  │
│            ▼                       ▼                       ▼                  │
│   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐        │
│   │   PostgreSQL    │     │     Redis       │     │   MAF Agents    │        │
│   │   (Port 5432)   │     │   (Port 6379)   │     │  (workforce)    │        │
│   │                 │     │                 │     │                 │        │
│   │  Episodes       │     │  Cache / Queue  │     │  Planner        │        │
│   │  Users / RBAC   │     │  Sessions       │     │  Researcher     │        │
│   │  Scripts / Logs │     │                 │     │  Translator     │        │
│   └─────────────────┘     └─────────────────┘     └─────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start (Development)

```bash
# 1. Clone the repository
git clone <repo-url>
cd multi-lingual-podcast

# 2. Copy environment variables
cp .env.example .env
# Edit .env with your real values (KIMI_API_KEY, SECRET_KEY, etc.)

# 3. Start the full stack
make dev
# or: docker-compose up --build

# 4. Open the app
#   Web UI    → http://localhost:3000
#   API Docs  → http://localhost:8000/docs
#   Neo4j     → http://localhost:7474
```

---

## Production Deployment (Hetzner VPS)

### Prerequisites
- Hetzner Cloud VPS (Ubuntu 22.04, 4 vCPU, 8 GB RAM recommended)
- Domain pointed to VPS IP (A record for `domain.com` and `api.domain.com`)
- SSH key pair for deployment

### Step-by-Step

1. **Provision the VPS**
   ```bash
   # On your local machine, copy SSH key to server
   ssh-copy-id -i ~/.ssh/id_rsa.pub root@<VPS_IP>
   ```

2. **Prepare the server**
   ```bash
   ssh root@<VPS_IP>
   apt update && apt upgrade -y
   apt install -y docker.io docker-compose git
   systemctl enable docker
   usermod -aG docker $USER
   ```

3. **Clone the project**
   ```bash
   mkdir -p /opt
   cd /opt
   git clone <repo-url> multi-lingual-podcast
   cd multi-lingual-podcast
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   nano .env
   # Set:
   #   DOMAIN=yourdomain.com
   #   ACME_EMAIL=admin@yourdomain.com
   #   KIMI_API_KEY=sk-...
   #   SECRET_KEY=<openssl rand -hex 32>
   #   POSTGRES_PASSWORD=<strong-password>
   #   NEO4J_PASSWORD=<strong-password>
   ```

5. **Create deploy script** (`deploy.sh` on the server)
   ```bash
   #!/bin/bash
   set -e
   cd /opt/multi-lingual-podcast
   git pull origin main
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
   docker system prune -f
   ```
   ```bash
   chmod +x deploy.sh
   ```

6. **Start production stack**
   ```bash
   make prod
   # or: docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

7. **Configure GitHub Secrets** for CD
   Go to **Settings → Secrets → Actions** and add:
   - `VPS_HOST` — your VPS IP or domain
   - `VPS_USER` — the SSH user (e.g., `root` or `deploy`)
   - `VPS_SSH_KEY` — the private SSH key contents

8. **Trigger deploy**
   Pushes to `main` will auto-deploy. You can also trigger manually:
   ```bash
   # Via GitHub UI → Actions → Deploy → Run workflow
   ```

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_USER` | PostgreSQL username | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `change-me` |
| `POSTGRES_DB` | PostgreSQL database name | `podcast` |
| `DATABASE_URL` | Full SQLAlchemy connection string | `postgresql://...` |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | `podcast_password` |
| `NEO4J_URI` | Neo4j Bolt URI | `bolt://neo4j:7687` |
| `SECRET_KEY` | JWT signing secret (hex 32) | `abc123...` |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiry | `30` |
| `KIMI_API_KEY` | Kimi / OpenAI API key | `sk-...` |
| `KIMI_BASE_URL` | Kimi API base URL | `https://api.moonshot.cn/v1` |
| `KIMI_MODEL` | Default LLM model | `moonshot-v1-8k` |
| `REDIS_URL` | Redis connection URI | `redis://redis:6379/0` |
| `ACME_EMAIL` | Let's Encrypt email | `admin@example.com` |
| `DOMAIN` | Primary domain | `example.com` |
| `API_SUBDOMAIN` | API subdomain | `api` |
| `NEXT_PUBLIC_API_URL` | Frontend → API URL | `http://localhost:8000` |
| `ENVIRONMENT` | Runtime environment | `development` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `MAF_WORKFORCE_PATH` | Path to `workforce.yaml` | `/app/workforce.yaml` |

---

## API Endpoints Overview

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/v1/health` | `GET` | Service health check | No |
| `/api/v1/auth/register` | `POST` | Create new user account | No |
| `/api/v1/auth/login` | `POST` | OAuth2 password login → JWT | No |
| `/api/v1/users/me` | `GET` | Current user profile | Yes |
| `/api/v1/podcasts` | `GET` | List all podcasts | Yes |
| `/api/v1/podcasts` | `POST` | Create a new podcast | Yes (Admin) |
| `/api/v1/podcasts/{id}` | `GET` | Get podcast details | Yes |
| `/api/v1/episodes` | `GET` | List episodes | Yes |
| `/api/v1/episodes` | `POST` | Create episode from vision | Yes |
| `/api/v1/episodes/{id}` | `GET` | Get episode details | Yes |
| `/api/v1/episodes/{id}/research` | `POST` | Trigger research phase | Yes |
| `/api/v1/episodes/{id}/script` | `GET` | Get generated script | Yes |
| `/api/v1/episodes/{id}/script` | `POST` | Generate / enhance script | Yes |
| `/api/v1/episodes/{id}/translate` | `POST` | Translate episode | Yes |
| `/api/v1/sphere/sync` | `POST` | Sync episode to Neo4j KG | Yes |
| `/api/v1/sphere/topics` | `GET` | Query topics from graph | Yes |

Full OpenAPI documentation available at `/docs` when the API is running.

---

## MAF Agent Workflow

The **Multi-Agent Framework (MAF)** orchestrates a pipeline of specialized agents defined in `workforce.yaml`:

1. **Podcast Planner** — Decomposes the host's vision into a structured task tree.
2. **Podcast Researcher** — Gathers sources from the web, RSS feeds, and the sphere knowledge graph.
3. **Podcast Synthesizer** — Connects facts into coherent arguments with evidence weighting.
4. **Podcast Scriptwriter** — Formats the narrative into a radio-ready script with timing and segments.
5. **Podcast Stylist** — Adds humor, metaphors, and cultural references to match the show's tone.
6. **Podcast Translator** — Translates the script into multiple languages with cultural adaptation.
7. **Podcast Executor** — Writes files, runs database migrations, and triggers CI/CD.
8. **Podcast Reviewer** — Reviews code, content, and policies before final approval.
9. **Podcast Test Agent** — Generates and runs tests for every new feature.
10. **Podcast Cost Agent** — Tracks token usage per episode and alerts on budget thresholds.
11. **Podcast Governance** — Enforces project policies and compliance rules.

Agents communicate via the MAF runtime, share state through the database, and leave a full audit trail.

---

## Sphere Knowledge Graph Integration

**sphere** is the project's knowledge graph layer powered by **Neo4j**.

- **Episodes** are synced as nodes with `Episode` labels, linking to `Topic`, `Person`, and `Source` nodes.
- **Cross-episode research** is enabled by traversing shared topics and entities.
- **Topic discovery** uses Cypher queries to surface trending or under-explored subjects.
- The `sphere_sync` module (`api/sphere_sync.py`) handles bidirectional sync between PostgreSQL and Neo4j.

Example Cypher query for related episodes:
```cypher
MATCH (e:Episode)-[:COVERS]->(t:Topic)<-[:COVERS]-(e2:Episode)
WHERE e.id = $episode_id
RETURN e2.title, e2.created_at, collect(t.name) as shared_topics
```

---

## Testing

### Backend (Python)
```bash
# Run all tests
make test
# or manually:
pytest tests/ -v --cov=api

# Run linting
make lint
# or manually:
flake8 api/ --count --show-source --statistics
```

### Frontend (Next.js)
```bash
cd app
npm test
npm run lint
```

### CI
GitHub Actions runs the full test matrix on every push and pull request to `main`. See `.github/workflows/ci.yml`.

---

## Backup and Restore

### Backup (run on server)
```bash
make backup
# or manually:
./scripts/backup.sh
```
This creates:
- `backups/podcast_db_YYYY-MM-DD.sql` — PostgreSQL dump
- `backups/neo4j_dump_YYYY-MM-DD/` — Neo4j graph dump
- `backups/app_data_YYYY-MM-DD.tar.gz` — Uploaded assets and runtime logs

### Restore
```bash
# Restore PostgreSQL
psql -U postgres -d podcast < backups/podcast_db_YYYY-MM-DD.sql

# Restore Neo4j
neo4j-admin load --from=backups/neo4j_dump_YYYY-MM-DD/ --database=neo4j --force

# Restore assets
tar -xzf backups/app_data_YYYY-MM-DD.tar.gz -C /opt/multi-lingual-podcast/
```

---

## Security Considerations

- **Secrets** are never committed. Use `.env` and GitHub Secrets.
- **JWT tokens** expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30 min).
- **Passwords** are hashed with bcrypt via `passlib`.
- **RBAC** enforces role-based access (Admin, Editor, Host, Viewer).
- **Dependency audits** run weekly via Trivy, pip-audit, and Bandit. See `.github/workflows/security.yml`.
- **HTTPS** is enforced in production via Traefik + Let's Encrypt.
- **Docker** images run as non-root users wherever possible.
- **CORS** is restricted to the production domain in production builds.

---

## License

MIT — See the `LICENSE` file at the project root.

---

## Project Documents

| Document | Purpose | File |
|----------|---------|------|
| **Idea** | Problem, vision, features, constraints | [`raw/idea.md`](raw/idea.md) |
| **Architecture** | System design, API, database, security | [`raw/architecture.md`](raw/architecture.md) |
| **Plan** | 8-phase roadmap with deliverables and costs | [`raw/plan.md`](raw/plan.md) |
| **Step-by-Step Guide** | How to build using MAF and sphere | [`raw/step_by_step_guide.md`](raw/step_by_step_guide.md) |

---

## Next Steps

Read the [`step-by-step guide`](raw/step_by_step_guide.md) to begin building or the [`architecture doc`](raw/architecture.md) for deep technical details.
