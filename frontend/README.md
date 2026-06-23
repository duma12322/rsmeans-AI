# RSMeans Cost Assistant — Frontend

Next.js (App Router) + Tailwind CSS UI for the FastAPI backend in this repo.

## Setup

```bash
cd frontend
npm install
```

Point it at the backend (defaults to `http://localhost:8000`) in `.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Run

Start the backend first (from the repo root):

```bash
uvicorn app.main:app --reload
```

Then the frontend:

```bash
npm run dev          # http://localhost:3000
```

The backend already allows `http://localhost:3000` via CORS. To allow other
origins, set `FRONTEND_ORIGINS` (comma-separated) in the backend `.env`.

## How it maps to the API

`POST /ask` returns a flat object keyed by `status`; the UI renders each case:

| `status`               | UI                                                        |
| ---------------------- | --------------------------------------------------------- |
| `ok`                   | Exact-match card (direct code lookup) + full results table |
| `needs_clarification`  | Likely candidates (clickable) + follow-up questions       |
| `needs_subject`        | "Cost of what?" guidance: MasterFormat categories + examples |
| `error`                | Inline error message                                      |

Multi-turn clarification is supported: when a response has
`needs_clarification`, the UI keeps its `session_id` and sends the next message
as `{ session_id, answer }`, so the conversation drills down instead of
restarting.
