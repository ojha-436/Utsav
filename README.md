# Utsav — GenAI event planner

Utsav helps people organise **weddings, birthdays and community events**. A three-step wizard produces a plan with an exact **budget**, a dated **timeline**, a **vendor checklist** and **personalised ideas**. You can refine it in plain language ("make it outdoor, cut decor by 15%"), save it, tick off tasks, log spending, find real local vendors and turn an inspiration photo into decor ideas.

**Live:** https://utsav-823065407403.asia-south1.run.app

![Landing page](docs/screenshots/style-landing-1280.png)

| Wizard | Plan on mobile |
|---|---|
| ![Wizard](docs/screenshots/style-wizard-1280.png) | ![Dashboard](docs/screenshots/style-dashboard-375.png) |

## How it works

Gemini **suggests** and plain Python **calculates**. Gemini returns a plan *skeleton*: weighted budget categories, tasks set "N days before the event", vendor roles with questions to ask, and ideas. Pure, tested functions turn that into whole-rupee budget lines that **always add up exactly** to your total and into real dates. Tasks that are already late move to today and are flagged.

```
Browser ─ index.html · app.html (wizard, dashboard, sign-in dialog) · Firebase JS SDK
   │  fetch /api/*   (Authorization: Bearer <Firebase ID token> when signed in)
   ▼
FastAPI on Cloud Run (asia-south1)
   ├─ routes/       plans (open, rate-limited) · events (signed-in, scoped per uid) · meta
   ├─ ai/           client.py: the only Gemini caller (retry → fallback model → JSON repair)
   │                prompts.py: user text only inside a <user_data> block · service.py
   ├─ planning/     PURE: sanitize · budget · timeline · tracking · ics · defaults · assemble
   ├─ auth.py       Firebase ID-token verification (uid always from the token)
   └─ store.py      Firestore planner_users/{uid}/events/{id}  (in-memory store for tests)
Google Cloud: Vertex AI Gemini (service-account auth) · Firebase Auth · Firestore · Cloud Logging
```

| Feature | How |
|---|---|
| Plan generation | Gemini 3.5 Flash structured output → `sanitize` → `assemble` |
| Exact budget | Largest-remainder rounding, contingency ≥ 5%, per-guest warning |
| Timeline | Due dates from the event date in IST; late tasks move to today and are flagged |
| Refine | Current skeleton + instruction → Gemini; ids are kept, so progress survives |
| Local vendors | Gemini + **Google Search grounding**; source links only from grounding metadata; 24 h cache per saved event |
| Photo → ideas | Gemini **vision**; JPEG/PNG/WebP detected by magic bytes, ≤ 5 MB |
| Calendar | RFC 5545 `.ics`: escaping, 75-octet folding (Devanagari-safe) |
| Accounts | Firebase Auth (email/password and Google); save, tick tasks, log spending |
| Resilience | If Gemini is down: a built-in standard plan with a banner, never a blank page |

## Mapping to the judging criteria

| Criterion | Evidence |
|---|---|
| **Code quality** | Small single-purpose modules; pure `planning/` core with no I/O; typed Pydantic models at every boundary; one Gemini doorway (`ai/client.py`); thin routes; consistent error shape `{"error": {"code", "message"}}`. |
| **Problem alignment** | All three event types × all four outputs (budget, timeline, vendor checklist, personalised ideas), plus refine, saving, tracking, calendar, grounded vendors and photo ideas. Event-specific guidance (for example, police, municipal and sound permissions for community events). INR throughout. |
| **Security** | Server-side Firebase token verification, uid only from the token, cross-user access returns 404; Firestore denies all browser access (Admin SDK only); **no API keys at all**, since Gemini uses Vertex AI with the Cloud Run service account; strict CSP, `nosniff`, no framing; per-IP and per-user rate limits; 6 MB body limit; prompt-injection containment (JSON-escaped `<user_data>` block plus schema-constrained output); the UI renders model text with `textContent` only (test-enforced); non-root container; logs never contain user text. |
| **Testing** | 140 pytest tests, no network or cloud needed (fake Gemini, in-memory store, fake token verifier). Property tests (hypothesis) prove budget lines always sum exactly. **97.8% coverage** on `planning/` + `routes/`, 94% overall. Headless-browser checks of the wizard, keyboard tabs, mobile layout, sign-in, saving and tracking. |
| **Google Cloud** | Cloud Run · Vertex AI Gemini 3.5 Flash (structured output, Google Search grounding, vision) with 2.5 Flash fallback · Firebase Authentication · Firestore · Cloud Build · Cloud Logging (structured JSON request logs). |

## Run locally

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
STORE=memory .venv/bin/uvicorn app.main:app --reload        # no AI: standard plans
# real Gemini through Vertex AI with your gcloud login:
STORE=memory USE_VERTEXAI=true GCP_PROJECT=<project> .venv/bin/uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/app. See `.env.example` for every setting.

## Test

```bash
.venv/bin/pytest
.venv/bin/pytest --cov=app/planning --cov=app/routes --cov-report=term-missing --cov-fail-under=85
```

## Deploy

```bash
gcloud run deploy utsav --source . --region asia-south1 --allow-unauthenticated --max-instances 3 --memory 512Mi \
  --set-env-vars USE_VERTEXAI=true,GEMINI_LOCATION=global,GEMINI_MODEL=gemini-3.5-flash,GEMINI_FALLBACK_MODEL=gemini-2.5-flash,GCP_PROJECT=<project>,STORE=firestore,FIREBASE_AUTH_DOMAIN=<project>.firebaseapp.com,FIREBASE_API_KEY=<public web api key>
```
The runtime service account needs `roles/aiplatform.user` and `roles/datastore.user`. For "Continue with Google", add the Cloud Run hostname under Firebase Authentication → Settings → Authorized domains. `firestore.rules` denies all browser access; deploy it as-is only in a project dedicated to Utsav.

## Project layout

```
app/            FastAPI app (see diagram above)
static/         index.html, app.html, css/app.css, js/*.js (ES modules, no build step)
tests/          pytest suite: factories.py, fakes.py, test_*.py
docs/superpowers/specs/   design spec      docs/superpowers/plans/   implementation plan
```
