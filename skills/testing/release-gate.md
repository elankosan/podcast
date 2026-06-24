# Release Gate Skill

## Mandatory Checks
1. API contracts
- Login uses x-www-form-urlencoded for OAuth2 password flow.
- Podcast episodes endpoint exists and returns expected shape.

2. Backend smoke
- GET /health returns 200 and non-error payload.
- GET /api/metrics returns Prometheus text.

3. Frontend smoke
- Login page can obtain token and redirect dashboard.
- Podcast detail page loads episode cards.

4. Migration and data safety
- Alembic upgrade head runs cleanly.
- Bootstrap admin path documented and executable.

## Gate Decision
- PASS if all mandatory checks succeed.
- FAIL if auth, health, or episodes listing is broken.
