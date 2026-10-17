def generate_id(length = 8):
    import random
    import string

    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
class BaseRule:
    def __init__(self, name = "default", description = "does nothing"):
        self.id = generate_id(8)
        self.name = name
        self.description = description
        self.store = {}

    def apply(self, text):
        return text

class PrivacyEngine:
    def __init__(self):
        self._ruleset: list[BaseRule] = []

    def add_rule(self, rule: BaseRule) -> str:
        self._ruleset.append(rule)
        return rule.id

    def remove_rule(self, id: str) -> bool:
        success = False
        try:
            self._ruleset = [rule for rule in self._ruleset if rule.id != id]
            success = True
        except Exception as e:
            print(f"Error removing rule: {e}")
        return success

    def apply_rules(self, text: str) -> str:
        for rule in self._ruleset:
            text = rule.apply(text)
        return text

class EmailRedactionRule(BaseRule):
    def __init__(self):
        super().__init__("email_redaction", "Redacts email addresses from text")
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
        self.email_counter = 0

    def _placeholder(self, email):
        if email not in self.store:
            self.email_counter += 1
            self.store[email] = f"[REDACTED_EMAIL_{self.email_counter}]"
        return self.store[email]


    def apply(self, text):
        import re
        out = re.sub(self.email_pattern, lambda m: self._placeholder(m.group()), text)
        return out

class PhoneRedactionRule(BaseRule):
    def __init__(self):
        super().__init__("phone_redaction", "Redacts phone numbers from text")
        self.phone_pattern = r'(?<!\w)(?:\+\d{1,3}[-.\s]?)?(?:\d[-.\s]?){7,14}\d(?!\w)'
        self.phone_counter = 0

    def _placeholder(self, phone):
        if phone not in self.store:
            self.phone_counter += 1
            self.store[phone] = f"[REDACTED_PHONE_{self.phone_counter}]"
        return self.store[phone]

    def apply(self, text):
        import re
        out = re.sub(self.phone_pattern, lambda m: self._placeholder(m.group()), text)
        return out

class NameRedactionRule(BaseRule):
    def __init__(self):
        super().__init__("name_redaction", "Redacts names from text")
        self.name_counter = 0

    def _placeholder(self, name):
        if name not in self.store:
            self.name_counter += 1
            self.store[name] = f"[REDACTED_NAME_{self.name_counter}]"
        return self.store[name]

    def apply(self, text):
        import re
        out = re.sub(self.name_pattern, lambda m: self._placeholder(m.group()), text)
        return out