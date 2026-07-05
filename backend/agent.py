
import os
import json
import time
from typing import Optional, TypedDict
from langgraph.graph import StateGraph, END
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


MODEL_NAME = "openai/gpt-oss-20b"


class LeadState(TypedDict):
    raw_message: str
    name: Optional[str]
    phone: Optional[str]
    source: Optional[str]
    email: Optional[str]

    budget: Optional[str]
    preferred_area: Optional[str]
    deal_type: Optional[str]
    bedrooms: Optional[str]
    timeline: Optional[str]

    urgency_score: Optional[int]
    one_line_reason: Optional[str]


def _call_groq(prompt: str) -> str:
    """Raw call to Groq — returns whatever text comes back, unprocessed."""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,  
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()


def _call_groq_with_retry(prompt: str, max_attempts: int = 3) -> dict:
    last_error = None

    for attempt in range(1, max_attempts + 1):
        raw_text = _call_groq(prompt)
        cleaned = raw_text.replace("```json", "").replace("```", "").strip()

        if not cleaned:
            print(f"[attempt {attempt}] Empty response from Groq, retrying...")
            last_error = "empty response"
            time.sleep(0.5)
            continue

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"[attempt {attempt}] Invalid JSON, retrying... ({e})")
            last_error = str(e)
            time.sleep(0.5)

    raise ValueError(f"Groq failed to return valid JSON after {max_attempts} attempts: {last_error}")


def extract_node(state: LeadState) -> LeadState:
    prompt = f"""Extract real-estate lead details from this message.
Return ONLY valid JSON, no markdown, no extra text, matching exactly this shape:

{{
  "budget": "<string or null, e.g. 'AED 1.5M'>",
  "preferred_area": "<string or null, e.g. 'Dubai Marina'>",
  "deal_type": "<'buy' or 'rent' or null>",
  "bedrooms": "<string or null, e.g. '2BR'>",
  "timeline": "<string or null, e.g. 'next month'>"
}}

Lead message:
\"\"\"{state['raw_message']}\"\"\"
"""
    data = _call_groq_with_retry(prompt)

    return {
        **state,
        "budget": data.get("budget"),
        "preferred_area": data.get("preferred_area"),
        "deal_type": data.get("deal_type"),
        "bedrooms": data.get("bedrooms"),
        "timeline": data.get("timeline"),
    }



def score_node(state: LeadState) -> LeadState:
    prompt = f"""You are scoring a real-estate lead's urgency to buy/rent, 1-10.

10 = ready now, clear budget, clear area, short timeline (this week/month).
1 = vague, no timeline, browsing only.

Lead details:
- budget: {state.get('budget')}
- preferred_area: {state.get('preferred_area')}
- deal_type: {state.get('deal_type')}
- bedrooms: {state.get('bedrooms')}
- timeline: {state.get('timeline')}

Return ONLY valid JSON, no markdown:
{{
  "urgency_score": <integer 1-10>,
  "one_line_reason": "<a natural, human-readable sentence explaining the score, under 20 words. Write it as you would say it to a colleague, not a list of keywords.>"
}}
"""
    data = _call_groq_with_retry(prompt)

    return {
        **state,
        "urgency_score": int(data["urgency_score"]),
        "one_line_reason": data["one_line_reason"],
    }

def decide_node(state: LeadState) -> LeadState:
    return state


def build_graph():
    graph = StateGraph(LeadState)

    graph.add_node("extract", extract_node)
    graph.add_node("score", score_node)
    graph.add_node("decide", decide_node)

    graph.set_entry_point("extract")
    graph.add_edge("extract", "score")
    graph.add_edge("score", "decide")
    graph.add_edge("decide", END)

    return graph.compile()


compiled_graph = build_graph()


def run_lead_qualifier(raw_message: str, name: str = None, phone: str = None, email: str = None, source: str = None) -> dict:
    """Entry point called by FastAPI."""
    initial_state: LeadState = {
        "raw_message": raw_message,
        "name": name,
        "phone": phone,
        "email": email,
        "source": source,
        "budget": None,
        "preferred_area": None,
        "deal_type": None,
        "bedrooms": None,
        "timeline": None,
        "urgency_score": None,
        "one_line_reason": None,
    }
    final_state = compiled_graph.invoke(initial_state)
    return final_state