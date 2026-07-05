from fastapi import FastAPI
from pydantic import BaseModel
from agent import run_lead_qualifier

app = FastAPI()


class LeadRequest(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    source: str | None = None
    message: str

@app.post("/analyze-lead")
def analyze_lead(lead: LeadRequest):
    result = run_lead_qualifier(
        raw_message=lead.message,
        name=lead.name,
        phone=lead.phone,
        email=lead.email,
        source=lead.source,
    )
    return result



@app.get("/")
def health_check():
    return {"status": "ok"}





