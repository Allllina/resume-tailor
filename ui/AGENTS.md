# AGENTS.md — Resume Tailor frontend (redesign handoff)

This is the **frontend** of a résumé-tailoring product. Your job: **redesign the
UI to be AI-native** while keeping it wired to the existing backend contract.

## Run it standalone — no backend needed

The app ships with a complete inline **mock layer**, so you can build the whole
UI with realistic data and **no Python backend**:

```bash
npm install
npm run dev          # serves on http://127.0.0.1:8080
```

`VITE_USE_MOCK` defaults to `true` (see `src/lib/api.ts`), so every API call
returns hand-built mock data mirroring the backend. **Do not add a backend.**

Stack: **TanStack Start (React) + Vite + Tailwind CSS**, file-based routing.

## Project map

```
src/
  routes/            file-based pages:
    index.tsx          Inbox — TODAY a queue of run cards + a small bottom-right
                       "Paste a JD" floating composer (this is what you redesign)
    run.$id.tsx        Run review (renders components/draft-review.tsx: match
                       matrix, HM/HRBP dual review, radar, Pass-3 verify panel,
                       Changes, Tex/PDF preview)
    settings.tsx       Profile / target market / per-lens masters
    experiences.tsx    Experience bank
    resume.tsx         Master résumé
    setup.tsx          Onboarding wizard
  components/        draft-card, draft-review, pass3-verify-panel,
                     floating-composer, fit-diagnosis/, layout/Sidebar.tsx, ui/ …
  lib/
    api.ts           API client + ALL TypeScript types + inline mocks + API_BASE
    queries.ts       TanStack Query hooks (useRuns, useRun, useUserStatus,
                     useTailorMutation, usePass3, useVerifyClaim, …)
    user.ts          X-User-Id header (multi-user)
```

## Redesign goal

- Make the Inbox **AI-native**: a **center-stage AI chat/dialog box** as the
  primary surface (replacing the small bottom-right "Paste a JD" composer), so
  the user converses with the assistant to tailor résumés.
- **Full-width** content — everything to the right of the left sidebar should
  use full width (it's currently centered at `max-w-2xl`).
- Keep the left sidebar (Inbox / Resume / Experiences / Settings).

## ⛔ Do NOT change — this is the backend contract (changing it breaks integration)

Redesign components / routes / layout freely, but **keep this data plumbing
intact** — it's how the UI talks to the real backend on handback:

- `src/lib/api.ts` — endpoint URLs, request/response **types**, `API_BASE`.
- `src/lib/queries.ts` — the React Query hooks. Reuse them; don't bypass.
- `src/lib/user.ts` — the `X-User-Id` header on every fetch.
- env var names: `VITE_API_BASE`, `VITE_USE_MOCK` (see `.env.example`).

Endpoint contract (don't rename / restructure):
`GET /api/runs` · `GET /api/runs/{id}` · `/api/runs/{id}/pdf|tex|pass3` ·
`POST /api/runs/{id}/verify-claim` · `GET /api/users/me` ·
`POST /api/tier1-tailor` · `POST /api/users/experiences/rescore`.

## Scope

- Only touch files under `ui/`. There is no backend in this handoff.
- Don't add new product features or new API calls — redesign the existing
  surfaces around the existing data.

## Handback

Return the modified `ui/` tree. The maintainer flips `VITE_USE_MOCK=false`,
re-wires anything that drifted, and tests against the real backend on `:8001`.
