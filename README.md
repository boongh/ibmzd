# Gatekeeper

Gatekeeper is a privacy gateway for AI chat. PII in user messages is replaced
with placeholders before the text reaches an external LLM, and the original
values are restored in the reply for the user.

## Repository status

- `src/`: FastAPI backend with SQLite storage and the privacy engine.
- `frontend/`: Vue frontend. It still calls the routes it was designed against
  (see [Frontend/API integration](#frontendapi-integration)) and is not wired
  to the backend yet.

## Repository layout

```text
.
├── main.py                    # backend entry point
├── example.toml               # backend config template, copy to config.toml
├── src/
│   ├── app.py                 # FastAPI app
│   ├── auth.py                # routers: /auth
│   ├── llm_models.py          #          /llm-models
│   ├── rules.py               #          /rules
│   ├── rulesets.py            #          /rulesets
│   ├── sessions.py            #          /sessions (incl. streaming chat)
│   ├── deps.py                # shared FastAPI dependencies
│   ├── models.py              # database tables
│   ├── schemas.py             # API request / response bodies
│   ├── db.py                  # database setup
│   ├── security.py            # password hashing, tokens
│   ├── privacy_engine.py      # redaction / restoration (see docs/privacy_engine.md)
│   ├── privacy_models.py      # engine data structures
│   ├── privacy_service.py     # engine <-> database glue
│   ├── llm.py                 # OpenAI compatible streaming client
│   └── ner.py                 # optional NER detector
├── tests/                     # uv run pytest
├── docs/
│   └── privacy_engine.md
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

## Run the backend

```sh
cp example.toml config.toml   # adjust host, port and database path
uv sync
uv run python main.py
```

Interactive API docs are served at `/docs`.

### NER

NER rules use [LFM2.5-Encoder-350M-PII-Detector](https://huggingface.co/LiquidAI/LFM2.5-Encoder-350M-PII-Detector)
at a pinned revision (`src/ner.py`). `torch` and `transformers` are not project
dependencies; install them in the environment that runs the backend, put the
model into a Hugging Face cache, and set `[ner] enabled=true` and `cache_dir` in
`config.toml`. With `mode="hybrid"` (LinuxONE, needs `torch-nnpa`) the model
runs on NNPA with its ShortConv blocks on CPU; at startup the hybrid result is
checked against CPU on a synthetic sample and the server refuses to start if
they differ. Without NER, sessions whose ruleset contains an NER rule refuse to
chat.

- Messages longer than 2048 tokens are rejected (422), not truncated.
- Known model gaps: some names are missed, phone numbers can be cut short, and
  e-mail addresses directly next to Chinese text can lose their first characters.
  Combine NER rules with regex rules for fixed formats (e-mail, phone) and give
  those a lower `priority` number, so they win where both match.

### LinuxONE (Docker)

The `Dockerfile` builds on the LinuxONE Community Cloud JupyterLab image, whose
`/opt/venv` already has the verified torch 2.11.0+cpu, torch-nnpa 1.5.0,
transformers 5.19.0 and zDNN setup; uv only adds the backend's dependencies
(the build fails if it would change the torch / transformers versions).

```sh
docker build -t gatekeeper:dev .
mkdir -p ~/gatekeeper/data            # database and Hugging Face cache (with the pinned model)
cp example.toml ~/gatekeeper/config.toml
# in config.toml: host="127.0.0.1", database path="/data/storage.db",
#                 [ner] enabled=true, cache_dir="/data/hf-cache", mode="hybrid"
docker run -d --name gatekeeper --network host \
  -v ~/gatekeeper/config.toml:/app/config.toml:ro -v ~/gatekeeper/data:/data gatekeeper:dev
docker logs -f gatekeeper             # wait for "self-check passed" and "Uvicorn running"
```

The backend only listens on `127.0.0.1`; reach it through an SSH tunnel
(`ssh -L 8000:127.0.0.1:8000 <user>@<host>`). With the model loaded it uses
about 3 GiB of memory, so stop notebook kernels that hold another copy of the
model first.

## Run the tests

```sh
uv run pytest
```

Tests live in `tests/` and only use synthetic PII: unit tests (`test_units.py`,
`test_privacy_engine.py`) and API integration tests (`test_api.py`), where the
LLM and the NER model are replaced by fakes. Run them through pytest (e.g. PyCharm's pytest runner), not as
plain Python scripts.

## Run the frontend

```sh
cd frontend
npm install
npm run dev
```

Vite proxies `/api/*` to `http://localhost:8000/*` by default and removes the
`/api` prefix. `example.toml` uses port 8080, so either set `port=8000` in
`config.toml`, or copy `.env.example` to `.env` at the repository root and set
`VITE_API_TARGET`. Build with `npm run build` from `frontend/`.

## Backend API

All routes except register and login need `Authorization: Bearer <token>`,
using the token returned by `POST /auth/login`.

| Area | Routes |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| LLM models | `GET/POST /llm-models`, `GET/PATCH/DELETE /llm-models/{id}`: OpenAI compatible endpoints; the API key is write only |
| Rules | `GET/POST /rules`, `GET/PATCH/DELETE /rules/{id}`: `config` is `{"type": "regex", "pattern", "label"}` or `{"type": "ner", "entities": [...]}` |
| Rulesets | `GET/POST /rulesets`, `GET/PATCH/DELETE /rulesets/{id}`: `entries` is a list of `{rule_id, priority, enabled}` |
| Sessions | `GET/POST /sessions`, `GET/PATCH/DELETE /sessions/{id}`: each session is bound to a `ruleset_id` and an `llm_model_id` |
| Chat | `POST /sessions/{id}/messages` (SSE), `GET /sessions/{id}/messages`, `GET /sessions/{id}/redactions` (replacement table) |

`POST /sessions/{id}/messages` streams `data:` JSON events: `user_message`
(`id`, the redacted `llm_content` that was sent), then `delta` chunks of the
raw reply (with placeholders), then `done` (`message_id`, the restored
`content`), or `error` (`detail`). If the message can't be redacted, the
request fails with 422 and nothing is sent or stored.

## Frontend/API integration

The frontend was designed against these routes, which the backend does not
implement yet:

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
