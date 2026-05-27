# Testing Strategy — 3-layer pyramid + test-contract-first

> Canonical testing standard for this repo. Cited by every subagent dispatch (`docs/SUBAGENT_DISPATCH_TEMPLATE.md`) and by `/feature-dev` flow. Updated when the pyramid grows new layers (e.g. visual regression, mutation testing).
>
> **Mental model:** before changing implementation, write a minimal test plan. Subagent A writes tests + verifies they FAIL. Subagent B writes impl that makes them PASS. Tests are NOT modified during impl phase except with explicit reasoning.

**Last updated:** 2026-05-10

---

## The 3 layers

```
                  ┌────────────────────┐
                  │  Layer 3: E2E      │  ← 3-5 tests max
                  │  Playwright        │     (main user flows)
                  └────────────────────┘
              ┌──────────────────────────────┐
              │  Layer 2: Component          │  ← UI behavior
              │  Vitest + RTL + jsdom        │     (FE only)
              └──────────────────────────────┘
        ┌────────────────────────────────────────┐
        │  Layer 1: Unit                         │  ← pure logic
        │  pytest (backend) / Vitest (frontend)  │     (most tests live here)
        └────────────────────────────────────────┘
```

### Layer 1 — Unit tests (pure logic)

**What to test:** validation logic, data transforms, scoring functions, sort/filter/recommendation algorithms, API response cleaning, business rules (resume matching score, label generation, status verdict, etc.).

**Stack:**
- Backend (Python): `pytest` — `packages/harness/tests/unit/<module>/test_*.py`
- Frontend (TypeScript): `vitest` — `ui/src/lib/__tests__/*.test.ts` (planned; infra not yet stood up)

**Coverage target:** every pure function should have ≥1 test. Cost is lowest, AI generates + maintains these well.

**Backend example** (`packages/harness/tests/unit/fit_diagnosis/test_engine_pre_rewrite.py:test_invalid_advance_decision_repaired`):
```python
@pytest.mark.asyncio
async def test_invalid_advance_decision_repaired():
    payload = json.loads(_valid_review_json())
    payload["hrbp"]["advance_decision"] = "promote_to_offer"  # not in enum
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(payload, ensure_ascii=False))
    out = await build_dual_review(...)
    assert out["_method"] == "llm_partial"
    assert out["hrbp"]["advance_decision"] == "screen_out"
```

**Frontend example** (planned for F4 + thereafter):
```ts
// ui/src/lib/__tests__/validateExperience.test.ts
import { validateExperience } from "@/lib/validateExperience";

test("rejects empty company name", () => {
  const result = validateExperience({ company: "", role: "Strategy Intern", description: "..." });
  expect(result.valid).toBe(false);
  expect(result.errors.company).toBe("Company is required");
});
```

### Layer 2 — Component tests (UI behavior)

**What to test:** page renders correctly, click → state change, form input → button enable/disable, loading / error / empty states present.

**Stack:**
- Vitest (test runner)
- React Testing Library (component interaction)
- jsdom (browser simulation)

**Status: NOT YET STOOD UP.** Planned for the dedicated test-infra task before F4 ships.

**Example skeleton:**
```tsx
// ui/src/components/__tests__/ExperienceForm.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ExperienceForm } from "@/components/ExperienceForm";

test("submit disabled when required fields empty", () => {
  render(<ExperienceForm />);
  expect(screen.getByRole("button", { name: /save experience/i })).toBeDisabled();
});

test("user can fill form and submit", async () => {
  const user = userEvent.setup();
  render(<ExperienceForm />);
  await user.type(screen.getByLabelText(/company/i), "Ipsos Strategy3");
  // ...
  expect(screen.getByRole("button", { name: /save experience/i })).toBeEnabled();
});
```

### Layer 3 — E2E tests (user main flows)

**What to test:** 3-5 critical user journeys. Don't test more than this — E2E is slow + flaky. Shouldn't replace unit tests.

**Stack:**
- Playwright

**Status: NOT YET STOOD UP.** Deferred from D07.2; planned for the dedicated test-infra task before F4 ships.

**Recommended initial 5 paths:**
1. User opens `/`, sees inbox + tailor CTA
2. User uploads / pastes a JD via FloatingComposer, sees a fresh run with MatchMatrix + DualReview panels populated
3. User clicks `/run/<id>`, sees both panels render + radar chart with 6 axes
4. Backend down: page shows error state, no white screen
5. Refresh `/run/<id>`: panels still render against persisted state.json

**Example skeleton:**
```ts
// ui/playwright/main-flow.spec.ts
import { test, expect } from "@playwright/test";

test("user can paste JD and see fit diagnosis", async ({ page }) => {
  await page.goto("http://localhost:8080");
  await page.getByLabel(/jd/i).fill("...");
  await page.getByRole("button", { name: /tailor/i }).click();
  await expect(page.getByText(/匹配矩阵/i)).toBeVisible({ timeout: 30000 });
  await expect(page.getByText(/双视角评估/i)).toBeVisible();
});
```

---

## Test-contract-first workflow

Two-phase TDD per feature. **Mandatory** for new modules, **strongly recommended** for bug fixes that aren't trivial.

### Phase A — Test contract (subagent dispatch A)

Prompt template (copy from `docs/SUBAGENT_DISPATCH_TEMPLATE.md` Section 4):

> Before changing the implementation, create a minimal test plan for this feature.
>
> Context: [what subsystem]
>
> Feature to implement: [feature name]
>
> Please produce:
> 1. Unit tests for core business logic (Layer 1)
> 2. Component tests for UI behavior (Layer 2 — when feature touches UI)
> 3. One Playwright E2E test for the main user flow (Layer 3 — when feature changes a user journey)
> 4. Edge cases that must NOT break
> 5. A short explanation of what should be mocked vs tested with real behavior
>
> Do NOT implement the feature yet. Only write the test plan and test files.
> Run pytest / vitest to confirm tests FAIL (since impl doesn't exist).
> Commit tests-only.

**Subagent A output:** test files committed; expected `test_*` failures documented in commit message.

### Phase B — Implement to pass (subagent dispatch B)

Prompt template:

> Now implement the feature to pass the tests at <test-file-path>.
>
> Constraints:
> - Do NOT delete or weaken existing tests.
> - If a test needs to change, explain WHY in the commit message before modifying it.
> - Run the test suite — every Phase-A test must PASS, no regression in pre-existing tests.

**Subagent B output:** implementation committed; pytest/vitest output in commit message confirms all Phase-A tests PASS + no regression elsewhere.

### Why two-phase

- **Phase A** locks the contract. Subagent B can't drift away from intended behavior — the test asserts what we want.
- **Phase B** is held accountable to specific assertions, not vague specs.
- Catches the "fix it by deleting the test" anti-pattern.
- Mirrors classic TDD red-green-refactor without requiring per-line discipline.

---

## What goes where

| Type of work | Layer 1 | Layer 2 | Layer 3 |
|---|---|---|---|
| New backend module (Python) | ✅ required | — | — |
| New backend module that affects API output | ✅ required | — | optional (E2E if user-visible) |
| New frontend component (UI panel, form) | optional (extracted helpers) | ✅ required | — |
| New frontend page / route | optional | ✅ required (page tests) | ✅ recommended |
| Schema / contract change | ✅ required (type assertions) | ✅ required (UI consumes) | optional |
| Bug fix (subtle) | ✅ required (regression test) | depends | depends |
| Bug fix (trivial typo) | optional | optional | optional |
| Refactor (no behavior change) | tests should NOT change | tests should NOT change | tests should NOT change |

---

## Mocking strategy

**Mock at boundaries:**
- LLM calls → `unittest.mock.AsyncMock` (backend) / `vi.fn()` (frontend)
- Filesystem → use real `tmp_path` fixtures (pytest) / `tmp/` (Vitest)
- Network / HTTP → mock at the fetch boundary
- Time / dates → inject via dependency

**Use real behavior for:**
- All in-process logic (no internal mocking — that's a test smell)
- Database / state.json reads (use real fixture files in `assets/` or `contracts/fixtures/`)
- Schema validation (real `jsonschema` lib against real `contracts/schemas/`)

**Anti-patterns:**
- Mocking the function under test → measures nothing
- Mocking everything → tests pass even when wrong
- Asserting `result is not None` → use structural / value assertions

---

## The 10 testing + quality rules (codified standard)

These rules apply to every code change — implementer subagent, reviewer subagent, controller, and to me when I'm working directly. Cited in every dispatch prompt.

1. **Do not remove, skip, or weaken existing tests** unless explicitly instructed.
2. For every new feature, **add or update tests before or together with implementation** (Phase A → Phase B).
3. **Business logic should live in pure functions under `lib/`** (frontend) or under domain modules (backend), and be **covered by unit tests** (Layer 1).
4. **UI behavior should be tested with React Testing Library** (Layer 2).
5. **Critical user journeys should be covered by Playwright E2E tests** (Layer 3) — keep these to 3-5 tests max.
6. **Mock external AI / API calls** in unit and component tests (`AsyncMock` for Python, `vi.fn()` for TS).
7. **Do not mock browser behavior in Playwright tests** unless absolutely necessary — Playwright already runs against a real browser.
8. **If a change breaks tests, explain the root cause and fix the implementation first.** Don't reach for "just update the test."
9. **Avoid large rewrites** unless there is a clear reason (and explain it).
10. **Keep changes small, reviewable, and easy to revert.** Multiple small commits beat one large one.

These mirror the spirit of Beck's TDD + Hunt & Thomas's _The Pragmatic Programmer_ — they are NOT optional aesthetic preferences.

---

## Test commands (ui/package.json)

After the test-infra task lands, the following npm scripts are canonical:

```json
{
  "scripts": {
    "test": "vitest",
    "test:watch": "vitest --watch",
    "test:e2e": "playwright test",
    "test:all": "vitest && playwright test"
  }
}
```

**When to run which:**
| Command | When |
|---|---|
| `npm run test` | After EVERY UI code change. ~10s for current scope. |
| `npm run test:e2e` | After important UI changes. ~30-60s. |
| `npm run test:all` | Before committing any UI work; before merging to main. |

Backend equivalent (already shipped):
| Command | When |
|---|---|
| `make test-quick` | After EVERY backend logic change (unit only). ~6s. |
| `make test` | Full pytest including integration. ~5min. |
| `make status` | Anytime — one-screen state without running tests. |

---

## Cross-references

- `docs/SUBAGENT_DISPATCH_TEMPLATE.md` Section 4: dispatch templates that cite this doc
- `docs/HANDSHAKE.md` L5: planned Playwright preview spec — first user of Layer 3
- `docs/INCIDENTS.md`: failures that motivated specific test patterns (e.g. INC-005 schema enum drift → Layer 1 test for enum stability)
- `Makefile`: `make test` (full pytest), `make test-quick` (unit only), eventually `make test-ui` (Vitest) + `make test-e2e` (Playwright) when infra lands

---

## Roadmap

| Item | Status | Owner |
|---|---|---|
| Backend pytest unit + integration | ✅ shipped | maintained |
| `docs/TESTING.md` (this doc) | ✅ shipped 2026-05-10 | — |
| Two-phase TDD pattern in dispatch template | 🟡 in flight (this commit) | next dispatch |
| Frontend Vitest + RTL infra | 🔴 not yet | task before F4 |
| Playwright E2E infra | 🔴 not yet | task before F4 |
| Layer 2 sample tests (1-2 components) | 🔴 not yet | with infra task |
| Layer 3 sample tests (3 main flows) | 🔴 not yet | with infra task |
| `make test-ui` + `make test-e2e` Makefile targets | 🔴 not yet | with infra task |
