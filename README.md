# Gatekeeper

Gatekeeper is a planned privacy gateway for AI workflows. This initial
repository snapshot establishes the service and documentation layout before
the frontend and backend implementations are added.

## Repository status

The directories are scaffolding only. The frontend implementation is
intentionally excluded from this structure-only snapshot; its local files are
kept under `frontend/` and can be added in a later change. API, detector, and
evaluation implementations and container configuration are not included.

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
└── frontend/                   # Frontend implementation added separately
```

`.env.example` documents the development API origin setting for the frontend
that will be added later.