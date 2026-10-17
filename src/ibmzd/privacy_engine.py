import sqlite3



def generate_id(length = 8):
    import random
    import string

    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
class BaseRule:
    def __init__(self, id = generate_id(8), name = "default", type = None, config = ""):
        self.id = id
        self.type : str = type
        self.name = "default"
        self.config = ""

    def strip(self, text):
        import re2
        if self.type == "regex":
            out = re2.sub(self.email_pattern, lambda m: self._placeholder(m.group()), text)
            return out
        if self.type == "BERT":
            pass
        return text

    def restore(self, text):
        return text

    @classmethod
    def default(cls, id = generate_id(8), name = "default", type = None, config = ""):
        return cls(id, name, type, config)

class PrivacyEngine:
    def __init__(self):
        import sqlite3
        self._ruleset: list[BaseRule] = []

    def create_session(self) -> str:
        session_id = generate_id(16)
        return session_id

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

    def apply_rules(self, text: str, session: str) -> str:
        for rule in self._ruleset:
            text = rule.strip(text)
        return text

    def get_rules(self) -> list[BaseRule]:
        return self._ruleset

class EmailRedactionRule(BaseRule):
    def __init__(self):
        super().__init__("email_redaction")
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
        self.email_counter = 0

    def _placeholder(self, email):
        if email not in self.store:
            self.email_counter += 1
            self.store[email] = f"[REDACTED_EMAIL_{self.email_counter}]"
        return self.store[email]

    def strip(self, text):
        import re
        out = re.sub(self.email_pattern, lambda m: self._placeholder(m.group()), text)
        return out

class PhoneRedactionRule(BaseRule):
    def __init__(self):
        super().__init__("phone_redaction")
        self.phone_pattern = r'(?<!\w)(?:\+\d{1,3}[-.\s]?)?(?:\d[-.\s]?){7,14}\d(?!\w)'
        self.phone_counter = 0

    def _placeholder(self, phone):
        if phone not in self.store:
            self.phone_counter += 1
            self.store[phone] = f"[REDACTED_PHONE_{self.phone_counter}]"
        return self.store[phone]

    def strip(self, text):
        import re
        out = re.sub(self.phone_pattern, lambda m: self._placeholder(m.group()), text)
        return out

class NameRedactionRule(BaseRule):
    def __init__(self):
        super().__init__("name_redaction")
        self.name_counter = 0

    def _placeholder(self, name):
        if name not in self.store:
            self.name_counter += 1
            self.store[name] = f"[REDACTED_NAME_{self.name_counter}]"
        return self.store[name]

    def strip(self, text):
        import re
        out = re.sub(self.name_pattern, lambda m: self._placeholder(m.group()), text)
        return out

