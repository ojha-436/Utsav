# Utsav — GenAI Event Planning Assistant · Design Spec

**Date:** 2026-11-01
**Status:** Approved in brainstorming; awaiting written-spec review
**Context:** Google × Hack2skill PromptWar challenge. Scored on five criteria: code quality, problem-statement alignment, security, testing, Google Cloud alignment. Short build window.

## 1. Problem & goals

Help people organise **weddings, birthdays and community events** with a GenAI assistant that produces **budgets, timelines, vendor checklists and personalized ideas**.

**Success criteria**

1. A live Cloud Run URL where a guest (no login) can generate a full plan for any of the three event types.
2. All four core outputs visible in one dashboard; plan refinable with a free-text instruction.
3. Budget lines always sum *exactly* to the stated total; every date is real and never in the past for open tasks.
4. `pytest -q` passes with no cloud credentials; ≥85% line coverage on `app/planning/` and `app/routes/`.
5. No secrets in the repo; saved data accessible only to its owner.
6. README maps features to the five scoring criteria.

**Non-goals (YAGNI):** chat assistant, multi-user collaboration on one event, RSVP/guest-list management, payments or vendor booking, multi-currency (INR only), email/push notifications, native mobile apps, non-English UI.

## 2. Decisions made

| Topic | Decision |
|---|---|
| Interaction | Wizard → four-tab dashboard (Budget · Timeline · Vendors · Ideas) with one plan-wide refine bar |
| Architecture | "AI proposes, code disposes": one structured Gemini call returns a plan *skeleton*; pure Python computes rupees and dates |
| Extras (all in scope, tiered) | Calendar `.ics` export · progress & spend tracking · grounded local vendors · inspiration photo → ideas |
| Access | Try first: generate/refine/vendors/export open to guests; saving, tracking and photo upload require Firebase login |
| Stack | FastAPI on Cloud Run · Gemini via `google-genai` · Firebase Auth (Google + Email/Password) · Firestore · Secret Manager · Cloud Logging |
| Frontend | Static HTML/CSS/vanilla ES modules served by FastAPI; hand-rolled SVG charts; no build step |
| Name | Utsav |

## 3. Architecture

```
Browser ─ index.html (landing) · app.html (wizard + dashboard + login modal) · Firebase JS SDK
   │  fetch /api/*   (Authorization: Bearer <Firebase ID token> when signed in)
   ▼
FastAPI on Cloud Run (asia-south1, project promptwar-501405)
   ├─ routes/          thin HTTP layer: validate (Pydantic) → call services → shape response
   ├─ auth.py          verify Firebase ID token → optional_user / require_user dependencies
   ├─ ai/client.py     the only Gemini caller: structured() · grounded() · vision()
   ├─ ai/prompts.py    templates + per-event-type guidance
   ├─ planning/        PURE functions, no I/O
   │    sanitize.py    repair model output (unknown keys, dupes, zero weights)
   │    budget.py      allocate(total, categories, guests, event_type) → exact rupee lines + warnings
   │    timeline.py    schedule(event_date, tasks, today, progress) → dated, statused tasks
   │    tracking.py    planned vs actual per category, completion %
   │    ics.py         tasks → RFC 5545 calendar text
   │    defaults.py    deterministic fallback skeleton per event type
   │    assemble.py    (input, skeleton, today, progress, spend) → Plan
   └─ store.py         EventStore protocol; FirestoreEventStore + InMemoryEventStore
External: Gemini (API key from Secret Manager) · Firestore · Firebase Auth
```

**Boundaries**

- `planning/` never touches the network; it owns every number and date shown to the user.
- `ai/client.py` is the single Gemini boundary (timeouts, retry, fallback model, schema validation). Tests replace it with a fake via FastAPI dependency override.
- The **skeleton** is the source of truth. The computed `Plan` is never stored; it is recomputed on every read. Progress and spend are stored separately, keyed by task `id` / category `key`, so refining never erases them.

### Proposed layout

```
app/
  main.py            app factory, middleware (security headers, request id, body limit), error handlers, static mount
  config.py          settings from env
  models.py          Pydantic models (EventInput, PlanSkeleton, Plan, request/response bodies)
  auth.py  ratelimit.py  store.py  logging.py
  ai/client.py  ai/prompts.py
  planning/sanitize.py budget.py timeline.py tracking.py ics.py defaults.py assemble.py
  routes/plans.py  routes/events.py  routes/meta.py
static/  index.html  app.html  css/  js/
tests/
Dockerfile  .dockerignore  requirements.txt  requirements-dev.txt
firestore.rules  .env.example  .gitignore  README.md
```

## 4. Data model

### 4.1 `EventInput` (user-supplied)

| Field | Type / bounds |
|---|---|
| `event_type` | `wedding` \| `birthday` \| `community` |
| `event_date` | date, strictly after today, at most 3 years ahead |
| `guest_count` | int, 1–5,000 |
| `budget_inr` | int, 1,000–100,000,000 (₹10 crore) |
| `city` | str, 2–80 chars |
| `vibe` | list of 0–5 chips from: `traditional`, `modern`, `eco`, `intimate`, `grand`, `budget-friendly`, `outdoor`, `themed` |
| `notes` | str, 0–500 chars (free text: religion/customs, age of birthday person, cause of community event, etc.) |

The `event_date` future check applies when an input is created or changed, not when a saved event is read after its date has passed.

### 4.2 `PlanSkeleton` (Gemini output, enforced by response schema)

```
title: str (≤80)
summary: str (≤400)
budget_categories: 3–12 × {key: slug, label: str, weight: int 1–100, essential: bool, note: str ≤160}
tasks: 5–40 × {id: slug, title: str ≤100, category_key: slug, days_before: int −30…540}
vendors: 0–12 × {category_key: slug, role: str ≤60, questions_to_ask: 1–5 × str ≤120, book_by_days_before: int 0…540}
ideas: 3–10 × {title: str ≤80, description: str ≤300, kind: theme|decor|food|activity|favour}
```

- `days_before` negative = after the event (thank-you notes, returns, cleanup).
- Refine prompts instruct the model to **preserve existing `id`s and `key`s** for unchanged items.
- Vendor checklist items get a derived id `vendor-{category_key}` (one vendor entry per category after sanitisation), so they can be ticked through the same progress map as tasks.

### 4.3 Sanitisation (`planning/sanitize.py`, after schema validation)

- Duplicate `key`s / `id`s (including two vendor entries for the same `category_key`): keep first occurrence.
- Task or vendor whose `category_key` is unknown → reassigned to `other` (category created with weight 1 if absent).
- All weights zero/missing → equal weights.
- Missing `contingency` category → added (see 4.4).

### 4.4 Budget allocation (`planning/budget.py`)

1. Ensure a `contingency` category exists, then raise its weight if needed so its share is **≥5%** of the total.
2. Exact share per category = `total × weight / Σweights`.
3. Floor each share to whole rupees; distribute the leftover rupees one each to the categories with the largest fractional remainders (ties broken by list order). **Σ lines == `budget_inr` exactly.**
4. Each line: `key, label, amount, percent (1 dp), per_guest`.
5. Warning `low_per_guest` when `budget_inr / guest_count` is below the event-type floor: wedding ₹1,500 · birthday ₹400 · community ₹150.

### 4.5 Scheduling (`planning/timeline.py`)

- `original_due = event_date − days_before`.
- Status per task: `done` (in progress map) · `compressed` (not done and `original_due < today`; displayed due date becomes `today`) · `due_today` · `upcoming`.
- Sorted by displayed due date, then by input order.
- Plan flag `short_notice = true` if any task is `compressed`.
- Vendor `book_by` dates and statuses use the same rule with `book_by_days_before`.
- Calendar export (`planning/ics.py`): one all-day `VEVENT` for the event itself plus one per task and vendor item that is not `done`, dated at its displayed due date; `UID` = `{item_id}-{event_date}@utsav`.

### 4.6 Computed `Plan` (response only, never stored)

```
event: EventInput, title, summary, generated_from: "ai" | "default"
budget: {total, per_guest, lines[], warnings[]}
timeline: {tasks[{id,title,category_key,original_due,due,status}], short_notice, completion_pct}
vendors: [{id, category_key, role, questions_to_ask[], original_book_by, book_by, status}]
ideas: skeleton ideas as-is
photo_ideas: [{title, description, palette[hex]}]       # empty for guests
tracking: {lines[{key,label,planned,actual,variance}], other_actual} | null   # null for guests
```

### 4.7 Firestore layout

Own root collection so it never mixes with SousChef's `users/{uid}` data in the shared `(default)` database:

```
planner_users/{uid}/events/{eventId}
  input, skeleton, version (int), created_at, updated_at
  progress:     {task_id: done_at}
  spend:        [{id, category_key, amount, note, at}]       # entries for removed categories roll into "Other"
  vendor_cache: {fetched_at, category_keys[], items[], sources[]}   # reused for 24 h
  photo_ideas:  [{title, description, palette[hex]}]          # max 20 kept, newest first
```

## 5. API

All errors: `{"error": {"code": str, "message": str}}`; no stack traces.

### 5.1 Open endpoints (optional auth, rate-limited 10/min per IP)

The browser holds the skeleton between calls.

| Method & path | Body | Returns |
|---|---|---|
| `POST /api/plans/generate` | `{input}` | `{skeleton, plan}` |
| `POST /api/plans/refine` | `{input, skeleton, instruction ≤300}` | `{skeleton, plan}` |
| `POST /api/vendors` | `{input, category_keys (1–4), event_id?}` | `{items[{category_key, name, why, area?, source_index?}], sources[{title, uri}]}` |
| `POST /api/calendar.ics` | `{input, skeleton, progress?}` | `text/calendar` attachment |

`/api/vendors` with a valid token **and** an `event_id` the caller owns reads/writes `vendor_cache` (24 h). Up to 3 vendors per category.

### 5.2 Authenticated endpoints (Firebase ID token; all lookups scoped to the token's uid; foreign ids → 404)

| Method & path | Purpose |
|---|---|
| `GET /api/events` | list my events (id, title, event_type, event_date, updated_at) |
| `POST /api/events` | save `{input, skeleton}` → `{id, plan}` |
| `GET /api/events/{id}` | full recomputed plan incl. tracking |
| `PUT /api/events/{id}` | replace `{input?, skeleton}` after refine; increments `version` |
| `DELETE /api/events/{id}` | delete event |
| `PATCH /api/events/{id}/tasks/{task_id}` | `{done: bool}`; accepts task ids and `vendor-{category_key}` ids; unknown id → 404 |
| `POST /api/events/{id}/spend` | `{category_key, amount 1–100,000,000, note ≤120}` |
| `DELETE /api/events/{id}/spend/{entry_id}` | remove a mistaken entry |
| `POST /api/events/{id}/photo-ideas` | multipart image (JPEG/PNG/WebP by magic bytes, ≤5 MB); 5/min per user |

### 5.3 Meta

- `GET /api/healthz` → `{"status": "ok"}`
- `GET /api/config` → public Firebase web config (apiKey, authDomain, projectId) from env.

## 6. GenAI design (`app/ai/`)

- **SDK:** `google-genai`, Developer API path (`USE_VERTEXAI=false`), key from env var injected from Secret Manager secret `gemini-api-key`.
- **Models:** primary `GEMINI_MODEL` (default `gemini-3.5-flash`), fallback `GEMINI_FALLBACK_MODEL` (default `gemini-2.5-flash`). Verify model availability at implementation start.
- **`structured(prompt, schema)`** — `response_mime_type=application/json` + `response_schema` from the Pydantic model; 30 s timeout. On 429/5xx: one retry with backoff, then fallback model. On schema-invalid output: one repair call including the validation error. Final failure raises `AIUnavailable`.
- **`grounded(prompt)`** — `google_search` tool; 45 s timeout. Request JSON in the response; if the model rejects structured output combined with the search tool, parse a fenced JSON block from text. Source URLs come **only** from grounding metadata, never from model text.
- **`vision(image_bytes, mime, prompt, schema)`** — multimodal structured call returning `{ideas[{title, description, palette[hex]}]}`.
- **Fallback:** `/api/plans/generate` catches `AIUnavailable` and returns `defaults.skeleton_for(event_type)` with `generated_from: "default"`; UI shows a "Standard plan — AI unavailable" banner. Refine failure returns 502 and leaves the current plan untouched. Vendor failure returns the checklist with no names plus a message.
- **Prompting:** a system instruction sets the role (Indian event planner, INR, city-aware, respects stated customs, never assumes religion or culture beyond the user's notes). User-supplied text (city, notes, instruction) goes inside a delimited data block that the instruction says to treat as data only.
- **Per-event guidance:** wedding (multi-function ceremonies only when notes or vibe suggest them; venue, catering, decor, photography, attire); birthday (adjust to age and audience from notes; cake, venue, entertainment, return gifts); community (permissions — police / municipal / sound, volunteers, sponsorship, safety, waste management).

## 7. Security

- Server-side ID-token verification with `firebase-admin`; uid always from the token, never from the body.
- `firestore.rules` denies all client reads and writes; only the server (Admin SDK) accesses data.
- Gemini key only in Secret Manager; `.env.example` holds placeholders; `.gitignore` covers `.env`.
- Pydantic bounds on every field; request body limit 6 MB (5 MB image + multipart overhead); image type by magic bytes → 415, oversize → 413.
- Prompt-injection containment: delimited data block plus schema-constrained output; frontend renders model text with `textContent` only (never `innerHTML`); vendor links restricted to `http(s)` with `rel="noopener noreferrer"`.
- In-memory per-IP token-bucket rate limiter on AI endpoints (acceptable with `max-instances=3`).
- Headers: `Content-Security-Policy` (self + gstatic/googleapis for Firebase SDK), `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `frame-ancestors 'none'`. CORS same-origin only.
- Container runs as a non-root user.
- Structured JSON logs to Cloud Logging with a request id; user notes, instructions and images are never logged.

## 8. Frontend

- **`index.html`** — landing: value proposition, sample plan preview, "Plan an event" CTA.
- **`app.html`**
  - **Wizard:** 3 steps (event type → date / guests / budget / city → vibe chips + notes), with client-side validation mirroring server bounds.
  - **Dashboard:** plan title and summary, short-notice / standard-plan banners, sticky refine bar, ARIA tablist with four tabs:
    - **Budget** — SVG donut + table (amount, %, per guest), warnings; signed in: log spend, variance per line, "Other" bucket.
    - **Timeline** — tasks grouped by month; checkboxes (signed in); compressed badge showing original date; **Export .ics**.
    - **Vendors** — per-category checklist with book-by date and questions to ask (tickable when signed in); **Find local vendors** → grounded results with numbered source links.
    - **Ideas** — idea cards; signed in: upload inspiration photo → ideas with palette swatches.
  - **Save plan** (guest) opens the login modal (Google or Email/Password), then `POST /api/events`. The unsaved plan stays in memory, so nothing is lost.
  - **My events** list for signed-in users.
- **Look:** warm, festive style with an accent colour per event type; final visual design done with the frontend-design skill during implementation.
- **Accessibility:** semantic HTML, labelled inputs, keyboard-operable tabs and chips, visible focus, WCAG AA contrast, `prefers-reduced-motion`; ₹ formatted with `Intl.NumberFormat('en-IN')`.

## 9. Testing

pytest; no cloud credentials or network required.

- **planning/** (with `hypothesis` property tests):
  - budget: Σ == total for random totals, weights and category counts; contingency ≥5%; single category; tiny totals; per-guest warning thresholds.
  - timeline: compressed tasks, post-event tasks, due_today, sorting stability, leap day, done tasks never compressed.
  - tracking: variance, removed category → Other, completion %.
  - ics: valid `VCALENDAR` / `VEVENT`, all-day `DTSTART;VALUE=DATE`, escaping of `,` `;` `\` and newlines, CRLF line endings, 75-octet line folding, done tasks excluded.
  - sanitize and defaults: every default skeleton passes schema and sanitisation for all three event types.
- **ai/** with a fake client: retry → fallback → repair → `AIUnavailable`; grounded parse failure; sources only from metadata.
- **routes/** via `TestClient` with `InMemoryEventStore` and a fake token verifier: 422 invalid input; 401 missing/invalid token; 404 cross-user access; 413/415 uploads; 429 rate limit; security headers on every response; default-plan fallback when the AI is unavailable; refine preserves progress for kept task ids.
- **Coverage:** ≥85% on `app/planning/` and `app/routes/` (`pytest --cov`).
- **Manual:** browser check of the wizard → dashboard flow for each event type, keyboard navigation, mobile width.

## 10. Deployment

- New Cloud Run service **`utsav`**, project `promptwar-501405`, region `asia-south1`; `--max-instances 3`, 512 MiB.
- `Dockerfile` on `python:3.12-slim`, non-root user, `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- Deploy: `gcloud run deploy utsav --source . --region asia-south1 --allow-unauthenticated --max-instances 3 --memory 512Mi --set-secrets GEMINI_API_KEY=gemini-api-key:latest --set-env-vars` with the env vars listed below.
- Reuses: Secret Manager secret `gemini-api-key`, Firestore `(default)` database, linked billing. Runtime service account needs `datastore.user` and `secretmanager.secretAccessor` (already granted per earlier deployment; verify).
- **Manual prerequisite:** Firebase Email/Password and Google sign-in providers enabled in the Firebase console for `promptwar-501405`. Status unknown since July 2026 — check at deploy time.
- Env vars: `GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL`, `USE_VERTEXAI=false`, `GCP_PROJECT`, `FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN`, `STORE=firestore|memory` (memory for local dev and tests).

## 11. Build order (tiers — later tiers can be dropped without breaking earlier ones)

1. **Core:** scaffold + `planning/` with tests → `ai/client` + generate/refine → wizard + four-tab dashboard → **deploy #1**.
2. **Accounts:** Firebase Auth + Firestore store + events CRUD + save-after-login flow.
3. **Extras (cheapest first):** `.ics` export → progress and spend tracking → grounded vendors → photo → ideas.
4. **Polish:** frontend-design pass, README with rubric mapping, final deploy, live verification.
