from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


from ibmzd.privacy_engine import (
    PrivacyEngine
)

from ibmzd.privacy_models import (
    Rule,
    RegexRuleConfig,
    Ruleset,
    RulesetEntry
)

app = FastAPI(title = "IBM Z Privacy App")

engine = PrivacyEngine()
DEFAULT_SESSION = "Default"

def create_default_ruleset() -> Ruleset:
    """Create the initial set of rules used in redacting sensitive user info"""

    email_rule = Rule(
        id = 1,
        name = "Email detection",
        config = RegexRuleConfig(
            pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            label = "EMAIL",
        )
    )

    phone_rule = Rule(
        id = 2,
        name = "Phone detection",
        config = RegexRuleConfig(

            pattern = r"\+?[0-9][0-9 ()-]{7,}[0-9]",
            label = "PHONE",
        )
    )

    return Ruleset(
        id = 1,
        name = "Default ruleset",
        entries = [
            RulesetEntry(rule = email_rule, priority = 1),
            RulesetEntry(rule = phone_rule, priority = 2)
        ],
    )



class RedactRequest(BaseModel):
    text : str
    session_id : str | None = DEFAULT_SESSION

def call_llm(text : str) -> str:
    #Do LLM Stuff
    pass

@app.post("/redact")
def redact_text(request: RedactRequest):

    if engine.get_ruleset(request.session_id) is None:
        engine.set_ruleset(
            request.session_id,
            create_default_ruleset()
            )

        
    try:
        redacted_text = engine.apply_rules(
            request.text,
            request.session_id,
        )

        if redacted_text is None:
            raise HTTPException(
                status_code = 503,
                detail="Redaction unavailable for this session",
            )

        answer = call_llm(redacted_text)
        
        return {"redacted_text": redacted_text, "answer": answer}

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code = 500,
            detail="Redaction failed",
        )


        

