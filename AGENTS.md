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

- **Frontend**: JavaScript chat UI. Framework not finalized.
- **API**: Python backend. Framework not finalized.
- **Privacy engine**: Python component between the API and the LLM. Detects and redacts PII.
- **LLM**: provider not finalized.

### Scope

- **MVP**: one-way stripping. PII is replaced with placeholders (e.g. `<PERSON>`, `<EMAIL>`) and never restored. The user sees placeholders in the reply.
- **Stretch goal**: re-identification. Keep a per-request placeholder map and swap the original values back into the LLM's reply. Don't build this until the MVP works and the user asks for it.

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
- **No PII persistence.** Don't write raw user input or PII mappings to disk, a database, a cache or analytics. Anything sensitive lives in memory for the length of one request only.
- **Synthetic test data only.** Tests, fixtures, examples and demo scripts use fake PII. Never commit real personal data.
- If the privacy engine fails, **fail closed**: return an error instead of forwarding the text.

## Tooling

- Python 3.12, managed with [uv](https://docs.astral.sh/uv/).
  - `uv sync` to install, `uv add <pkg>` to add a dependency (ask first, per the rules above).
  - `uv run ibmzd` runs the current entry point.
- Python package lives in `src/ibmzd/`.
- JS frontend tooling: not set up yet. Ask before choosing.
- Secrets such as LLM API keys go in environment variables or a git-ignored `.env`. Never commit them.

## Open decisions (ask the user before acting on any of these)

- Frontend framework
- API framework
- PII detection approach (rules/regex, NER model, a library like Presidio, or a mix)
- LLM provider and model
- Repo layout for the frontend vs. backend
- Test framework and how tests are run
