# Multi-Lingual Podcast — Iteration Log

**Project:** multi-lingual-podcast  
**Date:** 2026-06-23  
**Author:** Selan (Elanko)  
**Status:** Planning Complete — Ready for Phase 1

---

## Iteration History

### Iteration 0: Planning (2026-06-23)

**Trigger:** User vision for a multi-lingual podcast preparation application

**Actions:**
- Created `idea.md` — Problem definition, core features, success criteria
- Created `architecture.md` — System design, component detail, database schema, knowledge graph
- Created `plan.md` — 8-phase implementation roadmap with deliverables, agents, and cost tracking
- Created `test.md` — Test strategy across unit, integration, and E2E levels
- Created `workforce.yaml` — MAF workforce program with 12 agents, 4 policies, 4 integrations
- Created `step_by_step_guide.md` — Complete guide for building with MAF and sphere

**Decisions:**
- Technology stack: Next.js + FastAPI + PostgreSQL + Neo4j + Ollama
- Self-hosted, FOSS-first, GDPR-aware
- 4 initial languages: English, French, Spanish, Tamil
- MAF agent workforce extended with 5 new domain-specific agents (Researcher, Synthesizer, Scriptwriter, Stylist, Translator)

**Artifacts Created:**
- 7 documents in `raw/`
- 1 workforce program (`workforce.yaml`)
- Project directory structure

**Next Iteration:** Phase 1 — Foundation (scaffold, auth, database)

---

## Cost Tracking

| Iteration | Tokens | USD | Phase |
|-----------|--------|-----|-------|
| 0 (Planning) | ~15,000 | ~$0.03 | Planning |

**Total Budget:** $100 USD, 2,000,000 tokens
**Consumed:** $0.03, 15,000 tokens
**Remaining:** $99.97, 1,985,000 tokens

---

## Adaptive Adjustments

None yet. Adjustments will be recorded here based on Test Agent, Review Agent, and Cost Agent feedback after each phase.

---

## Next Steps

1. Begin Phase 1: `maf run workforce.yaml --input '{"phase": "1", "action": "scaffold"}'`
2. Verify: `docker-compose up` starts all services
3. Verify: `GET /health` returns 200
4. Log results in this file


---

### Iteration 1: Implementation (2026-06-24)

**Trigger:** Autopilot build approved — all 8 phases to be built with Kimi API replacing Ollama

**Actions:**
- **Kimi API Integration:** Replaced Ollama with Kimi API. Created `maf/integration/kimi_client.py` reading `KIMI_API_KEY` from environment. Updated `docker-compose.yml` to remove Ollama and inject `KIMI_API_KEY`.
- **Phase 1 (Foundation):** Built FastAPI backend with SQLAlchemy, PostgreSQL schema (User, Podcast, Episode, Version), JWT+OAuth2 auth with bcrypt, role-based access control (host, researcher, translator, reader, admin), docker-compose with api/app/postgres/neo4j/redis, Next.js 14 scaffold with Tailwind.
- **Phase 2 (Core API):** Created podcast/episode CRUD routers, MAF integration layer (`api/maf_integration.py`), research/script/translation API endpoints, trace logging to `runtime_logs/`.
- **Phase 3 (Research Agent):** Built `ResearchAgent` (`agent-003`) using KimiClient. Produces structured research briefs with key facts, arguments, context, quotes, and angles. Maps to `/api/research/{id}/research`.
- **Phase 4 (Script Agent):** Built `ScriptAgent` (`agent-004`) using KimiClient. Generates structured podcast scripts (Intro, 3 Segments, Outro) with [SEGMENT], [PAUSE], [SFX] markers. Applies style enhancement (transitions, rhetorical questions, engagement prompts). Maps to `/api/scripts/{id}/script`.
- **Phase 5 (Translation Agent):** Built `TranslationAgent` (`agent-005`) using KimiClient. Supports French (fr), Spanish (es), Tamil (ta), German (de). Two-step process: translate with cultural adaptation, then linguistic polishing. Maps to `/api/translations/{id}/translate`.
- **Phase 6 (UI):** Built Next.js App Router pages: login, dashboard, podcast detail, episode detail (with research/script/translation tabs), new podcast, new episode. API client in `app/lib/api.ts` with token auth.
- **Phase 7 (Sphere):** Built `PodcastSphereSync` using `Neo4jStateStore`. Syncs episodes, topics, facts, and arguments to Neo4j knowledge graph. Endpoints: `/api/sphere/{id}/sync`, `/api/sphere/related`, `/api/sphere/{id}/knowledge`.
- **Phase 8 (Testing):** Extended `tests/test_api_basics.py` with tests for research, script, translation, and sphere endpoints. All tests tolerate 500 errors when external services (Kimi/Neo4j) are unavailable.

**Decisions:**
- Changed from Ollama to Kimi API due to hardware constraints. API key never hardcoded; always read from `KIMI_API_KEY` env var.
- `PodcastWorkforce.execute_phase()` runs specific agents via `Orchestrator.run()` rather than full workforce, enabling targeted phase execution per episode.
- Script and Translation agents auto-save outputs to `Version` table on success.
- Version model extended with `metadata` column for language tracking.

**Artifacts Created:**
- `api/agents/` — ResearchAgent, ScriptAgent, TranslationAgent
- `api/routers/` — research.py, script.py, translation.py, sphere.py
- `api/sphere_sync.py` — Neo4j knowledge graph sync
- `app/app/` — login, dashboard, podcasts/[id], podcasts/new, episodes/[id], episodes/new, lib/api.ts
- `tests/test_api_basics.py` — Extended test coverage

**Cost Tracking:**

| Iteration | Tokens | USD | Phase |
|-----------|--------|-----|-------|
| 0 (Planning) | ~15,000 | ~$0.03 | Planning |
| 1 (Implementation) | ~45,000 | ~$0.09 | Phases 1-8 |
| **Total** | **~60,000** | **~$0.12** | **—** |

**Total Budget:** $100 USD, 2,000,000 tokens
**Consumed:** $0.12, 60,000 tokens
**Remaining:** $99.88, 1,940,000 tokens

**Next Steps:**
1. Review UI and provide feedback on layout/styling
2. Add web search capability to ResearchAgent when `kimi_search_v2` is available as a Python callable
3. Test full flow: create episode → research → script → translate → sync to sphere
4. Add publishing pipeline (RSS generation, export to Markdown/PDF)


---

### Iteration 2: Production Hardening & Hetzner Deployment (2026-06-24)

**Trigger:** User requested complete deployment pipeline for Hetzner VPS, GitHub push, and production readiness

**Actions:**
- **Frontend Hardening:** Fixed all Next.js TypeScript and build issues. Created `tsconfig.json`, `tailwind.config.js`, `postcss.config.js`, `app/globals.css`. Fixed `package.json` (correct typescript version, moved dev deps). Replaced `<a>` with `<Link>` throughout. Fixed API_BASE to use empty string for Next.js rewrites. Fixed React state mutation. All 27 Python files pass syntax check.
- **Backend Hardening:** Fixed missing imports in `maf_integration.py`. Fixed `get_trace()` and `get_cost_report()` to match actual trace filename pattern. Added API error detection in all agents. Fixed TranslationAgent `en` language short-circuit. Fixed sphere sync `_run_query` to consume records inside session. Added real health checks for PostgreSQL, Redis, Neo4j. Rewrote `config.py` with production env vars, pool settings, and allowed origins.
- **Production Dockerfiles:** Created multi-stage `api/Dockerfile` (non-root user, 4 uvicorn workers, HEALTHCHECK) and `app/Dockerfile` (standalone Next.js, non-root, HEALTHCHECK). Created `.dockerignore` files for both.
- **Production Compose:** Created `docker-compose.prod.yml` with Traefik v3.1 reverse proxy, Let's Encrypt SSL, HTTP→HTTPS redirect, rate limiting middleware, health checks on all services, proper network isolation (`frontend`/`backend`), and named volumes.
- **Nginx Alternative:** Created `nginx/nginx.conf` for users who prefer Nginx over Traefik.
- **Deployment Scripts:**
  - `scripts/setup-server.sh` — Hetzner VPS bootstrap (Docker, UFW, fail2ban, logrotate, app user)
  - `scripts/deploy.sh` — One-command deploy with rollback logic, health check, image cleanup. Detects `docker compose` vs `docker-compose`.
  - `scripts/backup.sh` — PostgreSQL + Neo4j dumps with 7-day retention, optional S3 placeholder
  - `scripts/restore.sh` — Full disaster recovery from backup tarball
- **CI/CD:** Created `.github/workflows/ci.yml` (pytest + Next.js build), `.github/workflows/deploy.yml` (SSH to Hetzner via secrets), `.github/workflows/security.yml` (Trivy scan, pip-audit, Bandit SAST).
- **Alembic Migrations:** Added `alembic` to requirements. Created `api/alembic.ini`, `api/alembic/env.py`, `api/alembic/script.py.mako`, and initial migration `0001_initial.py` creating users, podcasts, episodes, versions tables.
- **Prometheus Metrics:** Created `api/routers/metrics.py` with `requests_total`, `request_duration`, `agent_executions_total` counters. Exposed at `/api/metrics`.
- **Project Hygiene:** Created `.gitignore` (Python + Node + Docker + IDE), `.env.example` (19 variables, grouped by service), `Makefile` (dev, prod, test, lint, build, migrate, backup, clean), `README.md` (342 lines with architecture, deployment guide, API reference), `LICENSE` (MIT).

**Decisions:**
- Traefik chosen as default reverse proxy (easier Docker integration than Nginx). Nginx config provided as alternative.
- `docker compose` (plugin) preferred over legacy `docker-compose` binary. Deploy script auto-detects which is available.
- HTTP→HTTPS redirect handled by Traefik global entrypoint configuration, not per-service labels.
- Rate limiting applied globally at 100 req/min average, 50 burst.
- Database migrations via Alembic for production; `Base.metadata.create_all()` kept as safety net in lifespan for dev.
- All shell scripts use `set -euo pipefail` for strict error handling.

**Artifacts Created:**
- 4 new Dockerfiles/.dockerignores
- 1 production docker-compose
- 1 nginx config
- 4 deployment/backup scripts
- 3 GitHub Actions workflows
- 1 Makefile
- 1 .env.example
- 1 .gitignore
- 1 LICENSE
- 1 README.md (rewritten)
- 1 Alembic config + 1 initial migration
- 1 Prometheus metrics router
- 8 frontend config files fixed/created
- 10 backend Python files fixed/rewritten

**Cost Tracking:**

| Iteration | Tokens | USD | Phase |
|-----------|--------|-----|-------|
| 0 (Planning) | ~15,000 | ~$0.03 | Planning |
| 1 (Implementation) | ~45,000 | ~$0.09 | Phases 1-8 |
| 2 (Production) | ~35,000 | ~$0.07 | Deployment Hardening |
| **Total** | **~95,000** | **~$0.19** | **—** |

**Total Budget:** $100 USD, 2,000,000 tokens
**Consumed:** $0.19, 95,000 tokens
**Remaining:** $99.81, 1,905,000 tokens

**Deployment Checklist (ready to execute):**
1. [ ] Purchase Hetzner VPS (Ubuntu 24.04, 2 vCPU, 4GB RAM, 40GB SSD)
2. [ ] Point DNS A records to VPS IP: `yourdomain.com` and `api.yourdomain.com`
3. [ ] SSH into VPS: `ssh root@yourdomain.com`
4. [ ] Run bootstrap: `curl -fsSL https://raw.githubusercontent.com/YOURUSER/multi-lingual-podcast/main/scripts/setup-server.sh | bash`
5. [ ] Clone repo as `podcast` user: `git clone https://github.com/YOURUSER/multi-lingual-podcast.git /opt/multi-lingual-podcast`
6. [ ] Create `.env` from `.env.example` and fill in real secrets
7. [ ] Run deploy: `cd /opt/multi-lingual-podcast && sudo -u podcast bash scripts/deploy.sh`
8. [ ] Verify: `https://yourdomain.com` (App), `https://api.yourdomain.com/health` (API), `https://traefik.yourdomain.com` (Traefik)
9. [ ] Configure GitHub secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY` for auto-deploy on push
10. [ ] Create first admin user via API or direct DB insert

**Next Steps (post-deployment):**
1. Test full episode flow: create → research → script → translate → sync → publish
2. Set up monitoring alerts (Prometheus + Grafana or Uptime Kuma)
3. Configure automated backups via cron
4. Add web search to ResearchAgent when `kimi_search_v2` Python callable is available
5. Add publishing pipeline (RSS, Markdown, PDF export)
6. Add admin dashboard for user management
7. Performance testing with k6 or locust


### Iteration 3: Source-of-Truth Gap Closure + Domain Deployment Prep (2026-06-24)

**Trigger:** User requested raw/ as source of truth, production gap closure, required agents with skills, iterative delivery, and deployment target `podcast.digity.dev`.

**Actions Completed:**
- Fixed frontend/backend auth contract mismatch: frontend now uses OAuth2 form payload (`application/x-www-form-urlencoded`) for `/api/auth/login`.
- Added missing endpoint `GET /api/podcasts/{id}/episodes` to match UI contract used by podcast detail page.
- Added first-admin bootstrap utility: `api/bootstrap_admin.py` (idempotent admin creation/update flow).
- Added production agent pack:
  - `agents/production_architect.agent.md`
  - `agents/deployment_engineer.agent.md`
  - `agents/qa_guard.agent.md`
- Added production skills:
  - `skills/production/readiness-checklist.md`
  - `skills/deployment/hetzner-traefik.md`
  - `skills/testing/release-gate.md`
- Added governance policy file: `policies/production-governance.yaml`.
- Added dedicated production workflow definition: `workforce.production.yaml`.
- Added domain-specific environment template: `.env.podcast.digity.dev.example`.
- Added domain deployment wrapper: `scripts/deploy-podcast-digity.sh`.
- Added convenience Make targets: `deploy-digity`, `bootstrap-admin`.
- Updated source-of-truth guide with concrete first-admin bootstrap command.

**Current Deployment Status (`podcast.digity.dev`):**
- Deployment automation is now domain-ready in repo.
- Live deployment execution still requires runtime secrets and server access (`KIMI_API_KEY`, passwords, SSH/GitHub secrets).

**Risks / Open Items:**
1. Full production deployment cannot be completed without real secrets and target host access.
2. End-to-end runtime validation against live domain pending after secrets are provisioned.

**Next Iteration Proposal (Iteration 4):**
1. Provision `.env` from `.env.podcast.digity.dev.example` with real values on target server.
2. Run `scripts/deploy-podcast-digity.sh` on target host.
3. Bootstrap admin and execute smoke tests on live domain.
4. Record health evidence and rollback validation in this log.


### Iteration 4: Shared Infrastructure Deployment Mode (2026-06-24)

**Trigger:** User requested no new Traefik or PostgreSQL containers and to reuse existing infrastructure on this machine.

**Actions Completed:**
- Inspected host runtime infrastructure and confirmed existing shared Traefik (`shared-traefik`) and existing Postgres containers are running.
- Added `docker-compose.existing-infra.yml` with services limited to `api`, `app`, `neo4j`, and `redis`.
- Removed project-owned proxy/database from this deployment path by design.
- Added external infra deployment script: `scripts/deploy-existing-infra.sh`.
  - Requires `EXTERNAL_DATABASE_URL`.
  - Requires existing proxy network (`TRAEFIK_DOCKER_NETWORK`, default `proxy`).
  - Runs Alembic migrations against external PostgreSQL.
- Updated `scripts/deploy-podcast-digity.sh` to call existing-infra deployment script.
- Updated `.env.podcast.digity.dev.example` with `EXTERNAL_DATABASE_URL`, `TRAEFIK_DOCKER_NETWORK`, and `TRAEFIK_CERT_RESOLVER`.
- Added Make target: `deploy-existing-infra`.

**Result:**
- Project is now deployable in shared-host mode without creating new Traefik or PostgreSQL containers.

**Open Items:**
1. Populate real `.env` values (external DB credentials and domain secrets).
2. Execute deployment and verify live routing through shared Traefik for `podcast.digity.dev` and `api.podcast.digity.dev`.
