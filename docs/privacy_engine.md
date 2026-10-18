PRIVACY ENGINE - INTEGRATION GUIDE
==================================

Modules: src/privacy_engine.py         (PrivacyEngine)
         src/privacy_models.py         (plain-Python data structs)

The engine does all redaction itself (and restoration, if the stretch goal is
built). It does not talk to the LLM, the frontend or the database. It is
in-memory only and never writes to disk. Whoever wires it in (API layer) has
to do three things:

  1. Hold the ORIGINAL user text.
  2. Pass it to the engine together with the correct SESSION ID.
  3. Forward the REDACTED text the engine returns to the LLM (never the original).


QUICK START
-----------

    from src.privacy_engine import PrivacyEngine
    from src.privacy_models import Rule, RegexRuleConfig, Ruleset, RulesetEntry

    ruleset = Ruleset(1, "default", [
        RulesetEntry(Rule(1, "email", RegexRuleConfig(r"[\w.+-]+@[\w-]+\.\w+", "EMAIL")), priority=0),
    ])

    engine = PrivacyEngine(ruleset_loader=lambda session_id: ruleset)
    redacted = engine.apply_rules(user_text, session_id, message_id=msg_id)
    if redacted is None:
        ...                                       # fail closed: return an error
    reply = llm.chat(redacted)                    # only the redacted text goes out

See tests/test_privacy_engine.py for fuller examples.


DATA STRUCTS (privacy_models.py)
--------------------------------

They mirror the DB tables but hold only what the engine needs. All are
dataclasses; all except SessionRecords are frozen.

    RegexRuleConfig(pattern, label)          rules.config, type "regex" (Python re syntax)
    NerRuleConfig(entities)                  rules.config, type "ner" (e.g. ["identity.person_name"])
    Rule(id, name, config)                   rules row
    RulesetEntry(rule, priority=0,           ruleset_rules row with the rule inlined.
                 enabled=True)               Lower priority runs first and wins overlaps.
                                             enabled=False entries are skipped.
    Ruleset(id, name, entries)               rulesets row + its entries
    Redaction(id, label, placeholder,        redactions row. `id` is LOCAL to the engine
              original)                      (1, 2, 3 ... per session); real DB ids come later.
    RedactionSpan(message_id,                redaction_spans row. start_pos/end_pos are
                  redaction_id, rule_id,     str indices into the ORIGINAL text passed to
                  start_pos, end_pos)        apply_rules. redaction_id is the local Redaction.id.
    SessionRecords(redactions, spans,        What the engine holds per session:
                   llm_content)                redactions: dict[original text -> Redaction]
                                               spans:      list[RedactionSpan]
                                               llm_content: dict[message_id -> redacted text]

Not mirrored on purpose: users, chat_sessions, messages (including raw
`content`). The engine only needs the session id and, optionally, the message id.


API (PrivacyEngine)
-------------------

PrivacyEngine(ruleset_loader=None, ner_detector=None)
    ruleset_loader: Callable[[session_id], Ruleset | None]. Called on a cache
        miss or refresh. Supplied by the integrator (see TO DO LATER).
    ner_detector:   Callable[[text, entities], list[(start, end, label)]].
        No NER model is bundled. Offsets are into `text`. A ruleset with an
        NER rule and no detector makes apply_rules() return None.

apply_rules(text: str, session: str, *, message_id: int | None = None) -> str | None
    Redacts `text` with the session's ruleset and returns the redacted text.
    Returns None (never raises) if the session has no ruleset or anything
    fails. The error is logged on the `src.privacy_engine` logger as
    "<ExceptionType>: <message>", no traceback. On failure the engine's state
    is unchanged. Callers MUST treat None as an error and not forward the
    original text.
    With message_id, the spans and the redacted text (llm_content) are also
    held in memory; calling again for the same message replaces them. The
    message does not have to exist anywhere; nothing is validated.
    Without message_id only the redaction mapping is updated (so numbering
    stays consistent), no spans are kept.

restore_text(text: str, session: str) -> str | None
    Replaces the session's placeholders in `text` with their original values.
    `text` can be anything, e.g. an LLM reply. Matching is case-insensitive;
    unknown placeholders and other text are left as-is. One pass, so an
    original that looks like a placeholder is not substituted again. Returns
    None (logged, never raises) if the session has no records (apply_rules
    never ran for it, or it was forgotten) or anything fails. The result
    contains raw PII: show it to the user only, never log it or send it to the
    LLM.

Ruleset cache (one cached Ruleset per session):
    set_ruleset(session, ruleset)     put/replace the cached ruleset by hand
    refresh_ruleset(session) -> bool  drop the cache entry and reload via ruleset_loader;
                                      False if no loader, it returns None, or it raises
    invalidate_ruleset(session)       drop the entry; reloaded lazily on next apply_rules
    clear_ruleset_cache()             drop all entries
    get_ruleset(session)              cached ruleset (loads on miss) or None
    The cache is never refreshed automatically: after rules change, call one
    of the above.

Held records:
    get_records(session) -> SessionRecords | None   the LIVE object, treat as read-only
    set_records(session, records)                   seed records (e.g. loaded from the DB);
                                                    Redaction ids must be 1..n
    forget_session(session)                         evict records + cached ruleset


HOW REDACTION WORKS
-------------------

  - Every enabled rule runs against the ORIGINAL text (no chaining).
  - Overlaps are resolved by lower priority number, then longer match, then
    earlier start. The text is rewritten once, so span offsets are exact
    positions in the original text.
  - Placeholders are [LABEL_n], numbered per session and label ([PERSON_1],
    [EMAIL_2], ...). The same original value in a session always reuses its
    Redaction, so it always gets the same placeholder (even if another rule
    or label matches it later). A new session restarts at _1.


SESSION IDs
-----------

The session id keys the ruleset cache and the held records. Always pass the
same id for every message in one conversation, a new id for a new
conversation, and never share one between users.


RULES FOR CALLERS (from AGENTS.md)
----------------------------------

  - Every LLM request goes through the engine. No bypass or debug path.
  - Fail closed: if apply_rules() returns None, return an error to the user.
  - Never log raw user text or placeholder-to-value mappings. Log redacted
    text or metadata only. The engine's own error logs contain exception
    messages from re / rule config / the loader, not user text; a loader or
    detector that puts user text into exceptions would break this.
  - Do not persist original text or mappings without a decision (see below).
  - Tests and examples use synthetic PII only.


TESTING
-------

    uv run pytest tests/test_privacy_engine.py

Pure Python, no database. Checks redaction, per-session placeholder
consistency, restore_text, priority/overlap handling, span offsets, llm_content,
disabled rules, ruleset cache refresh/override/invalidate, eviction, the
return-None failure paths, and NER rules with a fake detector (the real model
is src/ner.py).


TO DO LATER (not implemented; marked `TODO(DB)` in the code)
------------------------------------------------------------

  1. Ruleset loading: write the ruleset_loader that builds a Ruleset (with
     Rule / RulesetEntry) from chat_sessions.ruleset_id, rulesets,
     ruleset_rules and rules rows. rules.config JSON maps to RegexRuleConfig /
     NerRuleConfig.
  2. Persistence: after apply_rules, save get_records(session) (redactions,
     spans, llm_content -> messages.llm_content) to the DB, mapping the local
     Redaction.id values to real DB ids, then call forget_session() when the
     session ends. Until then, records live only in engine memory, grow for
     the life of the process, and are lost on restart (so placeholder
     numbering restarts too).
  3. Loading existing records: on restart the engine does not reload earlier
     redactions, so a continuing session would renumber from _1. A way to seed
     SessionRecords is needed.
  4. Decide where raw `original` values may be stored. AGENTS.md says "no PII
     persistence"; restoration needs the mapping.
  5. An NER detector.
  6. Restoration across restarts: restore_text works from the in-memory
     records only (see item 3).
