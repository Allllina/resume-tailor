# Resume Tailor — UI

Frontend for the `jobsearch-ops-agent` Resume Tailor product.

## Stack

- TanStack Start (Vite + React 19) — file-based routing in `src/routes/`
- Tailwind v4 (CSS-in-CSS theme tokens in `src/styles.css`)
- shadcn/ui primitives (Radix-based) in `src/components/ui/`
- Bun runtime for `bun install` / `bun run dev`
- TypeScript strict

## Layout

```
src/
  routes/
    __root.tsx            shell + global head
    index.tsx             /         Inbox (draft list)
    setup.tsx             /setup    onboarding
    run.$id.tsx           /run/:id  draft review (Changes / Tex preview)
    run.demo-anker.tsx    /run/demo-anker  case study
  components/
    floating-composer.tsx fixed bottom-right JD paste box
    draft-card.tsx        Inbox row
    draft-review.tsx      review page body
    change-card.tsx       before/after diff card
    why-expand.tsx        lens routing reasoning
    status-strip.tsx      top bar (sources / drafts / last scan)
    app-menu.tsx          ⋯ dropdown (Connections / Auto-search / Privacy)
    demo-card-loop.tsx    landing demo
    ui/                   shadcn primitives
```

## Dev

```bash
cd ui
bun install
bun run dev          # http://localhost:5173 (or similar)
```

## Backend

The UI talks to the Python harness backend at `packages/harness/` over HTTP.

- Default API base: `http://127.0.0.1:8001`
- Run backend: `cd packages/harness && PYTHONPATH=src uvicorn harness.api.main:app --port 8001`

API client lives in `src/lib/api.ts`. TanStack Query hooks in `src/lib/queries.ts`.

## Configuration

Copy `.env.example` to `.env.local`:

```
VITE_API_BASE=http://127.0.0.1:8001
VITE_USE_MOCK=true
```

`.env.local` is gitignored (via `*.local` pattern in repo root `.gitignore`).

- `VITE_USE_MOCK=true` — use built-in fixtures from `lib/api.ts` (default; lets you dev without backend running)
- `VITE_USE_MOCK=false` — call the real harness backend on `VITE_API_BASE`

## Status (Wave 2.5)

UI ↔ backend wired:
- `useRuns()` → `GET /api/runs`
- `useRun(id)` → `GET /api/runs/{id}`
- `useTailorMutation()` → `POST /api/tier1-tailor` (mode `"auto"`)
- DraftReview Tex tab fetches `GET /api/runs/{id}/tex` + iframe `GET /api/runs/{id}/pdf` (Docker XeLaTeX-compiled)

Submit channels disabled until Wave 3.

## Brand tokens

Defined in `src/styles.css`:

- Background: `oklch(0.984 0.010 215)` — cool near-white (slight cyan tint)
- Foreground: `oklch(0.22 0.015 60)` — warm near-black
- Primary: `oklch(0.66 0.15 232)` — sky blue (~#2DA5F7)
- Verified / attention / error: sage / paper-yellow / brick-red

Fonts: Inter (UI) + Source Han Serif SC / Noto Serif SC (Chinese serif headings).
