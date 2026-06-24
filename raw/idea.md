# Multi-Lingual Podcast — Idea

**Project:** multi-lingual-podcast  
**Date:** 2026-06-23  
**Author:** Selan (Elanko)  
**Status:** ✅ Implemented — v1.0.0 Production Ready

---

## The Problem

I host a weekly one-hour radio show covering politics, history, economy, and philosophy. Preparing for each show requires:

1. **Research** across multiple sources — news, academic papers, historical archives
2. **Synthesis** — connecting disparate facts into a coherent narrative
3. **Formatting** — structuring content for radio (timing, segments, transitions)
4. **Style enhancement** — adding humor, metaphors, cultural references
5. **Multi-language publication** — translating and adapting content for different audiences
6. **Version management** — tracking drafts, revisions, and published versions

Currently, this is done manually with scattered notes, documents, and bookmarks. There is no unified system.

## The Vision (Realized)

A self-hosted web application that acts as an **intelligent podcast preparation studio**. The user (the host) describes the topic and desired angle. The application:

1. **Researches** the topic using Kimi AI (web search capability planned)
2. **Synthesizes** findings into a structured narrative with key arguments, evidence, and counter-arguments
3. **Formats** the content into a radio-ready script with timing, segment markers, and host notes
4. **Enhances** the script with humor, metaphors, and cultural references appropriate to the audience
5. **Translates** the final script into configured target languages with cultural adaptation
6. **Publishes** the content as reading material associated with the radio show recording
7. **Manages** the entire lifecycle through a web UI with authentication and authorization
8. **Syncs** all knowledge to a Neo4j knowledge graph for cross-episode research

## Core Features (Implemented)

| Feature | Description | Status |
|---------|-------------|--------|
| **Topic Research** | AI-powered synthesis from Kimi API | ✅ Implemented |
| **Narrative Synthesis** | Structured briefs with key facts, arguments, angles | ✅ Implemented |
| **Script Formatting** | Radio-ready script with segments, timing, [PAUSE], [SFX] markers | ✅ Implemented |
| **Style Enhancement** | Smooth transitions, rhetorical questions, engagement prompts | ✅ Implemented |
| **Multi-Language Translation** | Translate and culturally adapt to FR/ES/TA/DE | ✅ Implemented |
| **Podcast Management UI** | CRUD for podcasts, episodes, drafts, versions | ✅ Implemented |
| **Authentication & Authorization** | JWT + OAuth2, bcrypt, roles (host/researcher/translator/reader/admin) | ✅ Implemented |
| **Publishing Pipeline** | Export to markdown, PDF, web (RSS pending) | ✅ Partial |
| **Version Control** | Track drafts, revisions, and published versions via `versions` table | ✅ Implemented |
| **Sphere Integration** | Store podcast knowledge in Neo4j knowledge graph | ✅ Implemented |
| **Production Deployment** | Hetzner VPS, Traefik SSL, Docker, CI/CD | ✅ Implemented |

## Target Users

- **Primary:** Radio show host (myself) — creates and manages podcasts
- **Secondary:** Research assistants — verify facts and add sources
- **Tertiary:** Translators — review and refine machine translations
- **Public:** Readers — consume published reading material

## Success Criteria (Met)

1. ✅ A new podcast episode can be created from a one-sentence vision in under 30 minutes
2. ✅ The produced script is radio-ready with timing and segment markers
3. ✅ Translations are available in at least 3 languages within 1 hour of script completion
4. ✅ All content is stored in sphere's knowledge graph for cross-episode research
5. ✅ The application is self-hosted, FOSS-first, and compliant with data privacy requirements
6. ✅ Deployable to Hetzner VPS with one command

## Technology Stack (Actual)

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Frontend** | Next.js 14 / React / TypeScript / Tailwind CSS | Modern, fast, type-safe, SEO-friendly |
| **Backend** | FastAPI (Python) | Native MAF integration, async, OpenAPI docs |
| **Database** | PostgreSQL 15 + Neo4j 5.15 (sphere) | Relational + graph for knowledge |
| **AI/LLM** | Kimi API (Moonshot AI) | External API, hardware-independent, fast |
| **Auth** | OAuth2 + JWT + bcrypt | Standard, secure, role-based |
| **Deployment** | Docker + docker-compose + Traefik | Self-hosted, reproducible, SSL auto |
| **Agent Framework** | MAF v2.0 | Multi-agent orchestration |
| **Knowledge Base** | sphere (Neo4j) | Cross-episode knowledge graph |
| **Monitoring** | Prometheus + FastAPI health endpoints | Production observability |
| **CI/CD** | GitHub Actions | Automated testing + deployment |

## Constraints (Enforced)

- **Self-hosted:** No cloud dependency for core functionality
- **Privacy:** Research data and scripts stored locally; only LLM API calls leave the system
- **FOSS-first:** All components are open-source or have open-source alternatives
- **Compliant:** GDPR-aware data handling; deletable within 30 days
- **Multi-lingual:** Support for English, French, Spanish, and Tamil (German added)

## Next Step

Proceed to `architecture.md` for system design.
Proceed to `step_by_step_guide.md` for deployment instructions.
