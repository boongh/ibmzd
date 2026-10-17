import sqlite3
import time

def generate_id(length = 8):
    import random
    import string

    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
import re2
class Rule:
    def __init__(self, id, name, type, config, priority):
        self._id = id
        self._type : str = type
        self._name = name
        self._config = config
        self._priority = priority
        self.store = {}

    def _placeholder(self, match):
        if match not in self.store:
            self.store[match] = f"[REDACTED_{self.type.upper()}_{self.counter}]"
        return self.store[match]

    def strip(self, text, session, conn):


        if self.type == "regex":
            out = re2.finditer(self.config, text)

        if self.type == "BERT":
            # Placeholder for BERT-based redaction logic
            out = text  # No actual redaction implemented
        return out

    def restore(self, text):
        return text

    @classmethod
    def default(cls, id = generate_id(8), name = "default", type = None, config = ""):
        return cls(id, name, type, config)

class Ruleset:
    def __init__(self, id = generate_id(8), name = "default"):
        self.id = id
        self.name = name
        self.rules: list[Rule] = []

    def add_rule(self, rule: Rule):
        self.rules.append(rule)

    def remove_rule(self, rule_id: str):
        self.rules = [rule for rule in self.rules if rule.id != rule_id]

    def get_rules(self) -> list[Rule]:
        return self.rules

class Session:
    def __init__(self, id, ruleset_id = None):
        self._id = id
        self._user_id = None
        self._ruleset_id = ruleset_id
        self._title = None
        self._ruleset_cache: Ruleset = None
    def get_ruleset(self, conn) -> Ruleset:
        if self._ruleset_cache is not None:
            return self._ruleset_cache

        if self._ruleset_id is None:
            return None

        ruleset_data = conn.execute("SELECT * FROM rulesets WHERE id = ?", (self._ruleset_id,)).fetchone()
        if not ruleset_data:
            return None

        ruleset = Ruleset(ruleset_data["id"], ruleset_data["name"])
        rules_data = conn.execute("SELECT * FROM ruleset_rules WHERE ruleset_id = ?", (self._ruleset_id,)).fetchall()
        for rule in rules_data:
            rule_data = conn.execute("SELECT * FROM rules WHERE id = ?", (rule["rule_id"],)).fetchone()
            if rule_data:
                ruleset.add_rule(Rule(rule_data["id"], rule_data["name"], rule_data["type"], rule_data["config"], rule["priority"]))

        self._ruleset_cache = ruleset
        return ruleset

class PrivacyEngine:
    def __init__(self):
        import sqlite3
        self._sessions_id: dict[str, Session] = {}  # Maps session IDs to ruleset IDs

        # Connect to your existing SQLite database
        self._conn = sqlite3.connect("database.db")
        self._conn.row_factory = sqlite3.Row

    def refetch_rules(self, session: str) -> list[Rule]:
        if session not in self._ruleset:
            return None  # or raise an exception

        ##Refetch rules from the database and update the ruleset for the session
        return self._ruleset[session]

    # def create_session(self) -> str:
    #     session_id = generate_id(16)
    #     return session_id

    # def add_rule(self, ruleset_id: str, rule_id: Rule) -> str:
    
    #     if ruleset_id not in self._ruleset:
    #         return None  # or raise an exception
    #     self._ruleset[ruleset_id].append(rule_id)
    #     return rule_id.id

    # def remove_rule(self, ruleset_id: str, rule_id: str) -> bool:
    #     success = False
    #     try:
    #         self._ruleset = [rule for rule in self._ruleset if rule.id != rule_id]
    #         success = True
    #     except Exception as e:
    #         print(f"Error removing rule: {e}")

    #     return success

    # Returns None if the session does not exist, otherwise returns the redacted text
    def apply_rules(self, text: str, session: str) -> str:
        
        if session not in self._sessions_rulesets:
            sesh = self._conn.execute("SELECT * FROM rules").fetchone()
            if sesh:
                self._sessions_rulesets[session] = sesh["ruleset_id"] 
            else:
                return None

        if self._sessions_rulesets[session] not in self._ruleset:
            rules = self._conn.execute("SELECT rule_id, priority FROM ruleset_rules WHERE ruleset_id = ?", (self._sessions_rulesets[session],)).fetchall()
            for rule, priority in rules:
                rule_data = self._conn.execute("SELECT * FROM rules WHERE id = ?", (rule["rule_id"],)).fetchone()
                if rule_data:
                    self._ruleset[self._sessions_rulesets[session]].append(Rule(rule_data["id"], rule_data["name"], rule_data["type"], rule_data["config"], priority))
                else: 
                    return None

            self._ruleset[self._sessions_rulesets[session]].sort(key=lambda r: r.priority)

        for rule in self._ruleset[self._sessions_rulesets[session]]:
            text = rule.strip(text, session, self._conn)

        return text


    def get_rules(self) -> list[Rule]:
        return self._ruleset

# class EmailRedactionRule(BaseRule):
#     def __init__(self):
#         super().__init__("email_redaction")
#         self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
#         self.email_counter = 0

#     def _placeholder(self, email):
#         if email not in self.store:
#             self.email_counter += 1
#             self.store[email] = f"[REDACTED_EMAIL_{self.email_counter}]"
#         return self.store[email]

#     def strip(self, text):
#         import re
#         out = re.sub(self.email_pattern, lambda m: self._placeholder(m.group()), text)
#         return out

# class PhoneRedactionRule(BaseRule):
#     def __init__(self):
#         super().__init__("phone_redaction")
#         self.phone_pattern = r'(?<!\w)(?:\+\d{1,3}[-.\s]?)?(?:\d[-.\s]?){7,14}\d(?!\w)'
#         self.phone_counter = 0

#     def _placeholder(self, phone):
#         if phone not in self.store:
#             self.phone_counter += 1
#             self.store[phone] = f"[REDACTED_PHONE_{self.phone_counter}]"
#         return self.store[phone]

#     def strip(self, text):
#         import re
#         out = re.sub(self.phone_pattern, lambda m: self._placeholder(m.group()), text)
#         return out

# class NameRedactionRule(BaseRule):
#     def __init__(self):
#         super().__init__("name_redaction")
#         self.name_counter = 0

#     def _placeholder(self, name):
#         if name not in self.store:
#             self.name_counter += 1
#             self.store[name] = f"[REDACTED_NAME_{self.name_counter}]"
#         return self.store[name]

#     def strip(self, text):
#         import re
#         out = re.sub(self.name_pattern, lambda m: self._placeholder(m.group()), text)
#         return out

