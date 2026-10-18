"""PrivacyEngine unit tests (migrated from scripts/test_privacy_engine.py). Synthetic PII only."""

import pytest

from src.privacy_engine import PrivacyEngine
from src.privacy_models import NerRuleConfig, RegexRuleConfig, Rule, Ruleset, RulesetEntry

EMAIL = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
PHONE = r"\+?\d{1,3}[-. ]\d{3}[-. ]\d{3}[-. ]\d{4}"
DIGITS = r"\d{3}[-. ]\d{3}[-. ]\d{4}"  # overlaps PHONE, lower precedence

REGEX = Ruleset(1, "regex", [
    RulesetEntry(Rule(1, "email", RegexRuleConfig(EMAIL, "EMAIL")), priority=0),
    RulesetEntry(Rule(2, "phone", RegexRuleConfig(PHONE, "PHONE")), priority=1),
    RulesetEntry(Rule(3, "digits", RegexRuleConfig(DIGITS, "DIGITS")), priority=2),
    RulesetEntry(Rule(5, "disabled", RegexRuleConfig("secret", "SECRET")), priority=4, enabled=False),
])
SECRET = Ruleset(1, "secret", [RulesetEntry(Rule(5, "secret", RegexRuleConfig("secret", "SECRET")))])
EMPTY = Ruleset(3, "empty", [])

T1 = "Mail alice@example.com or call 555-123-4567 secret"


@pytest.fixture
def sessions():
    return {"s1": REGEX, "s2": REGEX}


@pytest.fixture
def engine(sessions):
    return PrivacyEngine(ruleset_loader=sessions.get)


def test_redacts_and_records_spans(engine):
    redacted = engine.apply_rules(T1, "s1", message_id=1)
    assert redacted == "Mail [EMAIL_1] or call [DIGITS_1] secret"  # the disabled rule is skipped

    records = engine.get_records("s1")
    assert records.llm_content[1] == redacted
    assert len(records.spans) == 2
    by_id = {r.id: r for r in records.redactions.values()}
    for span in records.spans:
        assert T1[span.start_pos : span.end_pos] == by_id[span.redaction_id].original
        assert span.message_id == 1


def test_overlap_lower_priority_number_wins(engine):
    # PHONE (priority 1) beats DIGITS (priority 2) on the same digits
    assert engine.apply_rules("ring +1 555-123-4567", "s1") == "ring [PHONE_1]"
    # priority wins even over a longer match
    short_first = Ruleset(4, "short-first", [
        RulesetEntry(Rule(6, "code", RegexRuleConfig(r"\d{6}", "CODE")), priority=0),
        RulesetEntry(Rule(7, "long", RegexRuleConfig(r"\d{6}-\d{4}", "LONG")), priority=1),
    ])
    engine.set_ruleset("s3", short_first)
    assert engine.apply_rules("id 123456-7890", "s3") == "id [CODE_1]-7890"


def test_same_value_keeps_its_placeholder(engine):
    engine.apply_rules(T1, "s1", message_id=1)
    assert engine.apply_rules("alice@example.com again, plus bob@example.com", "s1") == "[EMAIL_1] again, plus [EMAIL_2]"
    assert all(s.message_id == 1 for s in engine.get_records("s1").spans)  # no message_id -> no spans


def test_sessions_are_numbered_independently(engine):
    engine.apply_rules("alice@example.com", "s1")
    assert engine.apply_rules("bob@example.com", "s2") == "[EMAIL_1]"
    assert len(engine.get_records("s2").redactions) == 1


def test_reapplying_a_message_replaces_its_spans(engine):
    engine.apply_rules(T1, "s1", message_id=1)
    engine.apply_rules(T1, "s1", message_id=1)
    assert sum(s.message_id == 1 for s in engine.get_records("s1").spans) == 2


def test_no_match_returns_text_unchanged(engine):
    assert engine.apply_rules("nothing here", "s1") == "nothing here"


def test_ruleset_cache(engine, sessions):
    assert engine.apply_rules("a@b.co secret", "s2") == "[EMAIL_1] secret"
    sessions["s2"] = SECRET
    assert engine.apply_rules("a@b.co secret", "s2") == "[EMAIL_1] secret"  # still cached
    assert engine.refresh_ruleset("s2")
    assert engine.apply_rules("a@b.co secret", "s2") == "a@b.co [SECRET_1]"
    engine.set_ruleset("s2", EMPTY)  # manual override
    assert engine.apply_rules("a@b.co secret", "s2") == "a@b.co secret"
    engine.invalidate_ruleset("s2")  # next call reloads via the loader
    assert engine.apply_rules("a@b.co secret", "s2") == "a@b.co [SECRET_1]"
    sessions["s2"] = REGEX
    engine.clear_ruleset_cache()
    assert engine.apply_rules("a@b.co", "s2") == "[EMAIL_1]"  # reloaded, same original -> same placeholder


def test_failures_return_none_and_change_nothing(engine):
    engine.apply_rules(T1, "s1")
    before = dict(engine.get_records("s1").redactions)

    assert engine.apply_rules("x", "unknown") is None  # unknown session
    assert not engine.refresh_ruleset("unknown")
    failing = PrivacyEngine(ruleset_loader=lambda session: 1 / 0)  # loader error
    assert failing.apply_rules("x", "s1") is None
    assert engine.get_records("s1").redactions == before


def test_restore_text(engine):
    engine.apply_rules("alice@example.com, bob@example.com", "s1")
    engine.apply_rules("bob@example.com", "s2")

    # LLM-style reply: case-insensitive, repeated and unknown placeholders, per session
    assert engine.restore_text("I mailed [EMAIL_1] and [email_2].", "s1") == \
        "I mailed alice@example.com and bob@example.com."
    assert engine.restore_text("[EMAIL_1][EMAIL_1] [NOPE_9] plain", "s1") == \
        "alice@example.com" * 2 + " [NOPE_9] plain"
    assert engine.restore_text("[EMAIL_1] vs [EMAIL_2]", "s2") == "bob@example.com vs [EMAIL_2]"

    roundtrip = engine.apply_rules("Contact <carol@example.com>", "s1")
    assert engine.restore_text(roundtrip, "s1") == "Contact <carol@example.com>"
    assert engine.restore_text("x", "unknown") is None


def test_forget_session(engine):
    engine.apply_rules("alice@example.com", "s1")
    engine.forget_session("s1")
    assert engine.get_records("s1") is None


# ---- NER (with a fake detector) ----

NAMES = Rule(4, "names", NerRuleConfig(["identity.person_name"]))
WITH_NAMES = Ruleset(2, "with-names", [*REGEX.entries, RulesetEntry(NAMES, priority=3)])


def fake_ner(text, entities):
    out = []
    for name in ("Alice Example", "Bob Sample"):
        i = text.find(name)
        if i >= 0 and "identity.person_name" in entities:
            out.append((i, i + len(name), "PERSON"))
    return out


@pytest.fixture
def ner_engine():
    return PrivacyEngine(ruleset_loader={"s1": WITH_NAMES}.get, ner_detector=fake_ner)


def test_ner_rule_uses_the_detector(ner_engine):
    assert ner_engine.apply_rules("ring +1 555-123-4567 and Alice Example", "s1") == "ring [PHONE_1] and [PERSON_1]"
    assert ner_engine.apply_rules("Alice Example, Bob Sample", "s1") == "[PERSON_1], [PERSON_2]"
    assert ner_engine.restore_text("Hi [PERSON_1], see [PHONE_1]", "s1") == "Hi Alice Example, see +1 555-123-4567"


def test_ner_rule_without_detector_fails_closed():
    engine = PrivacyEngine(ruleset_loader={"s1": WITH_NAMES}.get)
    assert engine.apply_rules("Alice Example a@b.co", "s1", message_id=1) is None
    assert engine.get_records("s1") is None
