# Production Readiness Checklist

## Functional
- Login flow works end-to-end from UI to API token issuance.
- Podcast detail page can list episodes without 404.
- Episode workflow supports research, script, and translation actions.

## Security
- SECRET_KEY is non-default in production.
- First admin is bootstrapped out-of-band and auditable.
- No secrets committed in repo.

## Operational
- /health and /health/ready return healthy before cutover.
- Deployment script supports rollback on failed health gate.
- Backup and restore scripts are runnable on target host.

## Data
- Alembic migrations are applied before traffic shift.
- Version records are created for script and translation outputs.

## Release Gate
- Required tests pass.
- Iteration log updated with evidence and residual risks.
