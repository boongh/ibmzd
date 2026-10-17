import unittest

from ibmzd.privacy_engine import EmailRedactionRule, PhoneRedactionRule, PrivacyEngine


class TestEmailRedactionRule(unittest.TestCase):
    def setUp(self):
        self.rule = EmailRedactionRule()

    def test_redacts_email(self):
        out = self.rule.apply("Contact alice@example.com today")
        self.assertEqual(out, "Contact [REDACTED_EMAIL_1] today")

    def test_distinct_emails_get_distinct_placeholders(self):
        out = self.rule.apply("alice@example.com and bob@example.org")
        self.assertEqual(out, "[REDACTED_EMAIL_1] and [REDACTED_EMAIL_2]")

    def test_repeated_email_gets_same_placeholder(self):
        out = self.rule.apply("alice@example.com, alice@example.com")
        self.assertEqual(out, "[REDACTED_EMAIL_1], [REDACTED_EMAIL_1]")

    def test_text_without_email_unchanged(self):
        self.assertEqual(self.rule.apply("nothing to see"), "nothing to see")


class TestPhoneRedactionRule(unittest.TestCase):
    def setUp(self):
        self.rule = PhoneRedactionRule()

    def test_redacts_phone_formats(self):
        for phone in ["555-123-4567", "555.123.4567", "555 123 4567", "+1 555-123-4567", "5551234567"]:
            with self.subTest(phone=phone):
                self.assertEqual(self.rule.apply(f"Call {phone} now"), "Call [REDACTED_PHONE_1] now")
                self.setUp()

    def test_distinct_phones_get_distinct_placeholders(self):
        out = self.rule.apply("555-123-4567 and 555-987-6543")
        self.assertEqual(out, "[REDACTED_PHONE_1] and [REDACTED_PHONE_2]")

    def test_repeated_phone_gets_same_placeholder(self):
        out = self.rule.apply("555-123-4567, 555-123-4567")
        self.assertEqual(out, "[REDACTED_PHONE_1], [REDACTED_PHONE_1]")

    def test_text_without_phone_unchanged(self):
        self.assertEqual(self.rule.apply("room 42, floor 3"), "room 42, floor 3")


class TestPrivacyEngine(unittest.TestCase):
    def setUp(self):
        self.engine = PrivacyEngine()

    def test_add_rule_returns_id_and_applies(self):
        rule = EmailRedactionRule()
        self.assertEqual(self.engine.add_rule(rule), rule.id)
        out = self.engine.apply_rules("alice@example.com")
        self.assertEqual(out, "[REDACTED_EMAIL_1]")

    def test_removed_rule_no_longer_applies(self):
        rule_id = self.engine.add_rule(EmailRedactionRule())
        self.engine.remove_rule(rule_id)
        self.assertEqual(self.engine.apply_rules("alice@example.com"), "alice@example.com")


if __name__ == "__main__":
    unittest.main()
