PRIVACY ENGINE - INTEGRATION GUIDE
==================================

Module: src/ibmzd/privacy_engine.py
Class:  PrivacyEngine

The engine does all redaction itself (and restoration, if the stretch goal is
built). It does not talk to the LLM or the frontend. Whoever wires it in
(API layer) only has to do three things:

  1. Hold the ORIGINAL user text.
  2. Pass it to the engine together with the correct SESSION ID.
  3. Forward the REDACTED text the engine returns to the LLM (never the original).


QUICK START
-----------

    from ibmzd.privacy_engine import (
        PrivacyEngine, EmailRedactionRule, PhoneRedactionRule, NameRedactionRule,
    )

    engine = PrivacyEngine()                      # create once at app startup
    engine.add_rule(EmailRedactionRule())
    engine.add_rule(PhoneRedactionRule())
    engine.add_rule(NameRedactionRule())

    session_id = engine.create_session()          # once per conversation
    redacted = engine.apply_rules(user_text, session_id)
    reply = llm.chat(redacted)                    # only the redacted text goes out


API
---

PrivacyEngine()
    Creates an engine with an empty ruleset. Nothing is redacted until rules
    are added.

create_session() -> str
    Returns a new random session ID (16 chars). Call it once per conversation
    and keep the ID with that conversation.

add_rule(rule: BaseRule) -> str
    Appends a rule and returns its ID. Rules run in the order they were added.

remove_rule(id: str) -> bool
    Removes the rule with that ID. Returns True on success.

get_rules() -> list[BaseRule]
    Returns the current ruleset, in execution order.

apply_rules(text: str, session: str) -> str
    Runs every rule over `text` and returns the redacted text.
    Pass the session ID of the conversation the text belongs to.


SESSION IDs
-----------

The session ID is how the engine keeps placeholders consistent and (for
restoration) remembers which original value each placeholder stands for.

  - Always pass the same ID for every message in one conversation.
  - Use a new ID (create_session()) for a new conversation.
  - Never share an ID between users or conversations.
  - Passing the wrong ID gives wrong placeholder numbering and, once
    restoration exists, restores the wrong values. The caller owns this.


BUILT-IN RULES
--------------

    EmailRedactionRule   alice@example.com     -> [REDACTED_EMAIL_1]
    PhoneRedactionRule   +1 555-123-4567       -> [REDACTED_PHONE_1]
    NameRedactionRule    person names          -> [REDACTED_NAME_1]

Within one session the same value always maps to the same placeholder, and a
different value gets the next number (EMAIL_1, EMAIL_2, ...).


WHAT THE INTEGRATOR HANDLES
---------------------------

Per request, the API layer deals with two texts and one ID:

    original_text   what the user typed. Keep it only in memory for the
                    length of the request. Never log it, store it, or send it
                    to the LLM.
    redacted_text   what apply_rules() returned. This is the only version
                    that may go to the LLM or into logs.
    session_id      identifies the conversation. Created once, supplied on
                    every call.

Flow:

    user_text -> apply_rules(user_text, session_id) -> redacted_text -> LLM
    LLM reply -> frontend

MVP: the LLM reply is shown to the user as-is, placeholders included.
Stretch goal (restoration): the engine swaps placeholders in the LLM reply
back to the original values for that session. The integrator then passes the
LLM reply plus the same session ID to the engine and shows what it returns.
The restore call is not part of the public API yet; this section will be
updated when it is.


RULES FOR CALLERS (from AGENTS.md)
----------------------------------

  - Every LLM request goes through the engine. No bypass or debug path.
  - Fail closed: if apply_rules() raises, return an error to the user. Do not
    forward the original text.
  - Never log raw user text or placeholder-to-value mappings. Log redacted
    text or metadata only (counts, entity types).
  - Do not persist original text or mappings anywhere.
  - Tests and examples use synthetic PII only.


CURRENT STATUS (known gaps in the code)
---------------------------------------

The module is mid-iteration and does not run yet. The guide above describes
the intended interface.

  - privacy_engine.py has a syntax error in BaseRule.strip
    (`if self.type == "BERT"` is missing its colon and body).
  - Rules use `self.store`, which is never initialised, so the built-in
    rules fail on first match.
  - apply_rules() accepts `session` but does not use it yet, so
    placeholders are not scoped per session.
  - NameRedactionRule references `self.name_pattern`, which is not defined.
  - Restoration is not implemented (BaseRule.restore is a stub).
  - test_privacy_engine.py calls apply_rules(text) without a session
    argument and needs updating to the two-argument form.
