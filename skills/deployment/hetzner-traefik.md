# Hetzner + Traefik Deployment Skill

## Target
- Primary domain: podcast.digity.dev
- API domain: api.podcast.digity.dev
- Optional dashboard: traefik.podcast.digity.dev

## Required Inputs
- DOMAIN=podcast.digity.dev
- ACME_EMAIL set to valid mailbox
- POSTGRES_PASSWORD, NEO4J_PASSWORD, KIMI_API_KEY, SECRET_KEY

## Procedure
1. Apply server bootstrap script once.
2. Copy .env.podcast.digity.dev.example to .env and fill secrets.
3. Run scripts/deploy.sh.
4. Verify health at https://api.podcast.digity.dev/health.
5. Verify app at https://podcast.digity.dev.

## Rollback
- If health checks fail, run compose down/up using last known image tags.
- Keep rollback image tags from scripts/deploy.sh.
