# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project

Hackathon project for the IBM Z Datathon 2026: a privacy-preserving chatbot.
User messages are scrubbed of PII before they ever reach an LLM.

```
Chat frontend (JS) -> API (Python) -> Privacy engine (strip PII) -> LLM
                                                                    |
Chat frontend      <- API          <- response ---------------------+
```

- **Frontend**: Vue 3 + Vite chat UI in `frontend/`.
- **API**: FastAPI backend in `src/`, storage in SQLite via SQLModel.
- **Privacy engine**: `src/privacy_engine.py`, between the API and the LLM. Detects PII with each user's
  rules (regex, or the optional NER model LiquidAI/LFM2.5-Encoder-350M-PII-Detector) and replaces it with placeholders.
- **LLM**: any OpenAI compatible API. Each user adds their own endpoints (base URL, model, API key).
- **Target platform**: IBM LinuxONE (s390x). Prefer dependencies that are pure Python or ship s390x wheels.

### Scope

- **MVP**: PII is replaced with placeholders (e.g. `[EMAIL_1]`, `[PERSON_NAME_1]`) before the text is sent to the
  LLM, and the original values are swapped back into the reply for the user. The same value keeps the same
  placeholder within a session.
- Not yet: file uploads.

## Working rules for agents

**Never assume. State decisions and ask first.**

1. Before you start any task, write down the decisions and assumptions you're making: libraries, file layout, interfaces, data formats, scope. Then wait for the user to confirm.
2. If something is ambiguous or not covered here, ask. Don't pick a default on your own.
3. This applies to small choices too: adding a dependency, renaming things, changing an interface, picking a PII detection approach, choosing an LLM provider or model.
4. If something you find during the work contradicts a confirmed decision, stop and raise it instead of working around it.
5. Keep changes scoped to the task. No drive-by refactors.

## Privacy rules (non-negotiable)

- **No raw PII to the LLM.** Every request to the LLM goes through the privacy engine. Don't add bypass paths, debug shortcuts or fallbacks that send unredacted text.
- **No PII in logs.** Logs, error messages, exceptions and traces must never contain raw user text or PII mappings. Log only redacted text or metadata such as counts and entity types.
- **PII stays in the local database.** The original messages, the replacement table (placeholder <-> original) and the redaction spans are stored in the local SQLite database, so that history and restoration survive restarts. They are only returned to their owner through the API, never written anywhere else (files, caches, analytics), and the database file (`*.db`) is never committed.
- **Synthetic test data only.** Tests, fixtures, examples and demo scripts use fake PII. Never commit real personal data.
- If the privacy engine fails, **fail closed**: return an error instead of forwarding the text.

## Tooling

- Python 3.12, managed with [uv](https://docs.astral.sh/uv/).
  - `uv sync` to install, `uv add <pkg>` to add a dependency (ask first, per the rules above).
  - Copy `example.toml` to `config.toml` (git-ignored), then `uv run python main.py` starts the API.
- Backend code lives flat in `src/` (no package). Import modules as `from src.xxx import ...` and run from the repository root.
- Tests: pytest, in `tests/`. Run `uv run pytest` from the repository root (`uv sync` installs the dev dependencies).
  Tests never call a real LLM (use the `fake_llm` fixture). The NER tests are commented out until the NER model is integrated.
- Frontend: `cd frontend && npm install && npm run dev` (see README).
- Never commit secrets. Users' LLM API keys are stored in the local database and are never returned by the API.

## Open decisions (ask the user before acting on any of these)

- Whether chatting keeps the frontend's preview / review step before sending (the backend currently redacts and sends in one call)
