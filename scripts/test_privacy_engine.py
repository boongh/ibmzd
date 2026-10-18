"""Synthetic-data check for PrivacyEngine. Run: uv run python scripts/test_privacy_engine.py"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root, so that `src` is importable

from src.privacy_engine import PrivacyEngine
from src.privacy_models import NerRuleConfig, RegexRuleConfig, Rule, Ruleset, RulesetEntry

EMAIL = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
PHONE = r"\+?\d{1,3}[-. ]\d{3}[-. ]\d{3}[-. ]\d{4}"
DIGITS = r"\d{3}[-. ]\d{3}[-. ]\d{4}"  # overlaps PHONE, lower precedence

NAMES = Rule(4, "names", NerRuleConfig(["identity.person_name"]))

FULL = Ruleset(1, "full", [
    RulesetEntry(Rule(1, "email", RegexRuleConfig(EMAIL, "EMAIL")), priority=0),
    RulesetEntry(Rule(2, "phone", RegexRuleConfig(PHONE, "PHONE")), priority=1),
    RulesetEntry(Rule(3, "digits", RegexRuleConfig(DIGITS, "DIGITS")), priority=2),
    RulesetEntry(NAMES, priority=3),
    RulesetEntry(Rule(5, "disabled", RegexRuleConfig("secret", "SECRET")), priority=4, enabled=False),
])
NER_ONLY = Ruleset(2, "ner-only", [RulesetEntry(NAMES)])

SESSIONS = {"s1": FULL, "s2": FULL, "s3": NER_ONLY}


def fake_ner(text, entities):
    out = []
    for name in ("Alice Example", "Bob Sample"):
        i = text.find(name)
        if i >= 0 and "identity.person_name" in entities:
            out.append((i, i + len(name), "PERSON"))
    return out


def main():
    logging.basicConfig(level=logging.CRITICAL)  # expected failures below log errors; keep output clean
    engine = PrivacyEngine(ruleset_loader=SESSIONS.get, ner_detector=fake_ner)

    # basic redaction + spans + llm_content
    t1 = "Mail alice@example.com or call 555-123-4567 secret"
    r1 = engine.apply_rules(t1, "s1", message_id=1)
    assert r1 == "Mail [EMAIL_1] or call [DIGITS_1] secret", r1
    rec = engine.get_records("s1")
    assert rec.llm_content[1] == r1
    assert len(rec.spans) == 2
    by_id = {r.id: r for r in rec.redactions.values()}
    for s in rec.spans:
        assert t1[s.start_pos : s.end_pos] == by_id[s.redaction_id].original
        assert s.message_id == 1

    # overlap: PHONE (priority 1) beats DIGITS (priority 2) on the same digits
    r2 = engine.apply_rules("ring +1 555-123-4567 and Alice Example", "s1", message_id=2)
    assert r2 == "ring [PHONE_1] and [PERSON_1]", r2

    # same value -> same placeholder within a session; new value -> next number
    t3 = "alice@example.com again, plus bob@example.com and Alice Example, Bob Sample"
    assert engine.apply_rules(t3, "s1") == "[EMAIL_1] again, plus [EMAIL_2] and [PERSON_1], [PERSON_2]"
    assert all(s.message_id in (1, 2) for s in engine.get_records("s1").spans)  # no message_id -> no spans

    # separate session restarts numbering
    assert engine.apply_rules("bob@example.com", "s2") == "[EMAIL_1]"
    assert len(engine.get_records("s2").redactions) == 1

    # reapplying to the same message replaces its spans (idempotent)
    engine.apply_rules(t1, "s1", message_id=1)
    assert sum(s.message_id == 1 for s in engine.get_records("s1").spans) == 2

    # no matches -> unchanged text
    assert engine.apply_rules("nothing here", "s1") == "nothing here"

    # NER-only ruleset
    assert engine.apply_rules("hi Bob Sample a@b.co", "s3") == "hi [PERSON_1] a@b.co"

    # ruleset cache: stale until refreshed, then picks up the new ruleset
    updated = Ruleset(1, "full", [RulesetEntry(Rule(5, "secret", RegexRuleConfig("secret", "SECRET")))])
    SESSIONS["s2"] = updated
    assert engine.apply_rules("a@b.co secret", "s2") == "[EMAIL_2] secret"  # still cached
    assert engine.refresh_ruleset("s2")
    assert engine.apply_rules("a@b.co secret", "s2") == "a@b.co [SECRET_1]"
    engine.set_ruleset("s2", NER_ONLY)  # manual override
    assert engine.apply_rules("a@b.co secret", "s2") == "a@b.co secret"
    engine.invalidate_ruleset("s2")  # next call reloads via the loader
    assert engine.apply_rules("a@b.co secret", "s2") == "a@b.co [SECRET_1]"  # same original -> same placeholder
    engine.clear_ruleset_cache()
    assert engine.apply_rules("a@b.co", "s1") == "[EMAIL_3]"

    # failures return None, leave records untouched
    assert engine.apply_rules("x", "nope") is None  # unknown session
    assert not engine.refresh_ruleset("nope")
    before = len(engine.get_records("s1").redactions)
    bad = PrivacyEngine(ruleset_loader=SESSIONS.get)  # NER rule, no detector
    assert bad.apply_rules("Alice Example a@b.co", "s1", message_id=1) is None
    assert bad.get_records("s1") is None
    failing = PrivacyEngine(ruleset_loader=lambda s: 1 / 0)  # loader error
    assert failing.apply_rules("x", "s1") is None
    assert len(engine.get_records("s1").redactions) == before

    # restoration: LLM-style reply with placeholders, any text, case/unknown/overlapping cases
    assert engine.restore_text("Hi [PERSON_1], I mailed [EMAIL_1] and [email_2].", "s1") == \
        "Hi Alice Example, I mailed alice@example.com and bob@example.com."
    assert engine.restore_text("[EMAIL_1][EMAIL_1] [NOPE_9] plain", "s1") == \
        "alice@example.com" * 2 + " [NOPE_9] plain"
    assert engine.restore_text("[EMAIL_1] vs [PERSON_2]", "s2") == "bob@example.com vs [PERSON_2]"  # per session
    roundtrip = engine.apply_rules("Bob Sample <bob@example.com>", "s1")
    assert engine.restore_text(roundtrip, "s1") == "Bob Sample <bob@example.com>"
    assert engine.restore_text("x", "nope") is None  # unknown session

    # eviction
    engine.forget_session("s1")
    assert engine.get_records("s1") is None

    print("all privacy engine checks passed")


if __name__ == "__main__":
    main()
