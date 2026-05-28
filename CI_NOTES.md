# CI Notes

## Playwright E2E Tests Exclusion

The `ui/playwright/run-detail.spec.ts` test suite is currently excluded from the Playwright CI gate because:
1. **Requires Live Backend:** It performs full page loads on dynamic routes (e.g., `/run/mock-anker-aigc`) which query backend API endpoints (such as `getRun`). In standard environments, this requires a running FastAPI backend listener (`uvicorn`) to respond to API requests.
2. **Translation/Mock Sync:** Running in a frontend-only mock environment (e.g. by setting `VITE_USE_MOCK=true`) still fails because the dynamic route `/run/$id` is not wrapped in the `LangProvider` and defaults to English (`en`), while the test expects Chinese (`zh`) vocabulary headings like `匹配矩阵` and `双视角评估`.

### Prerequisites to land `run-detail.spec.ts` in CI:
* A live backend service step configured inside `.github/workflows/playwright.yml` to spin up uvicorn and seed the sample SQLite database.
* Or, wrapping the `/run/$id` routes in the UI application with a language provider switcher or updating the test assertions to handle the default English locale.
