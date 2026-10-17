from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ibmzd.privacy_engine import (
    PrivacyEngine,
    EmailRedactionRule,
    PhoneRedactionRule,
    NameRedactionRule,
)

engine = PrivacyEngine()

engine.add_rule(EmailRedactionRule())
engine.add_rule(PhoneRedactionRule())
engine.add_rule(NameRedactionRule())

app = FastAPI()

class ChatRequest(BaseModel):
    text : str
    session_id : str | None = None

# Temporary Endpoint
@app.get("/")
def home():
    return {"message": "Privacy API is running"}

@app.post("/redact")
def redact_text(request: ChatRequest):
    if not request.session_id:
        raise HTTPException(
            status_code = 400,
            detail = "Session ID is missing!"
        )

    try:
        redacted_text = engine.apply_rules(
            request.text,
            request.session_id
        )
    except Exception as e:
        print(f"Redaction Error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code = 500,
            detail = "Redaction failed"
        )

    return {
         "redacted_text": redacted_text
    }

        

