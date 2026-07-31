# Test layout

- `backend/tests/`: FastAPI contracts, safe error responses, redacted configuration,
  strict Pydantic models, provider parameters, retry policy, error mapping, and the
  single JSON-repair boundary.
- `frontend/src/**/*.test.tsx`: component states, interactions, successful and failed
  API paths, report generation, and the React error boundary.

Live DeepSeek and Paritok integration tests are opt-in and skipped unless their
explicit environment flags and local credentials are present. The default test
suite never calls an external AI service.
