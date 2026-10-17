# Gatekeeper

Gatekeeper is a privacy gateway for AI workflows. The frontend reviews prompts
and supported document uploads, displays detected sensitive values, and sends
only the approved cleaned text to the API.

## Repository status

The Vue frontend is implemented in `frontend/`. The `api/`, `detector/`, and
`eval/` directories are scaffolding for planned services and evaluation
assets; their implementations and container configuration have not been
added yet.

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
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.vue
        ├── main.js
        ├── components/
        ├── composables/
        ├── services/
        └── styles/
```

## Run the frontend

```sh
cd frontend
npm install
npm run dev
```

Vite proxies `/api/*` to `http://localhost:8000/*` by default and removes the
`/api` prefix. To use another API origin, copy `.env.example` to `.env` at the
repository root and set `VITE_API_TARGET`, or set it in the process
environment. Build with `npm run build` from `frontend/`.

## Frontend/API integration

The frontend expects these API routes:

- `POST /chat/prepare` (multipart fields `conversation_id`, `message`, and repeated `files`)
- `POST /chat/preview/update`
- `POST /chat/send` (Server-Sent Events response)
- `GET/POST/PUT/DELETE /rules`, `POST /rules/test`
- `GET /conversations`, `DELETE /conversations/{id}`

Preview data is expected to include `cleaned_text` and `detections`; optional
fields include `original_with_highlights`/`original_text` and `warnings`.
`preview_id` is needed to persist detection toggles or manual detections through
`/chat/preview/update` and is forwarded with the approved `/chat/send` request.
Stream events are read from SSE `data:` fields. Backend errors are surfaced in
the UI; the frontend does not mock successful responses or fall back to
sending the original prompt.