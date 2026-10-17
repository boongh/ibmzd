# Gatekeeper

Gatekeeper is a planned privacy gateway for AI workflows. This initial
repository snapshot establishes the service and documentation layout before
the frontend and backend implementations are added.

## Repository status

The directories are scaffolding only. The frontend is intentionally excluded
from this structure-only snapshot; its local files are kept under `web/` and
can be added in a later change. API, detector, and evaluation implementations
and container configuration are not included.

## Repository layout

```text
.
├── .env.example
├── api/
│   ├── app/
│   │   ├── auth/
│   │   ├── routers/
│   │   ├── ingest/
│   │   ├── pipeline/
│   │   ├── detectors/
│   │   ├── vault/
│   │   └── llm/
│   └── tests/
├── detector/
│   ├── app/
│   └── models/                 # Local model artifacts; not committed
├── docs/
│   └── screenshots/
├── eval/
│   └── dataset/
└── web/                        # Frontend implementation added separately
```

`.env.example` documents the development API origin setting for the frontend
that will be added later.


- **`web/`** is reserved for the Vue user interface and browser-facing API
  client. Frontend implementation files are intentionally excluded from this
  initial structure snapshot.
- **`api/`** is planned as the FastAPI orchestration service. It will own
  authentication, chat and conversation routes, file ingestion, the
  detection/redaction pipeline, policy, pseudonymisation, the encrypted vault,
  persistence, and the final outbound guard.
- **`detector/`** is planned as a separate service for NER, LLM checks, and risk
  scoring. The API calls its internal endpoints; model artifacts belong under
  `detector/models/` and are excluded from source control.
- **`eval/`** will hold platform/package checks and evaluation scripts with
  synthetic inputs and ground-truth spans.
- **`docs/screenshots/`** is reserved for product and evaluation evidence.