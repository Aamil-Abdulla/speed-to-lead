# Speed-to-Lead Engine

AI-powered lead qualification and routing system for real estate — built for a Dubai brokerage use case (Kirpa Properties AI Officer application).

## Problem

Real estate leads go cold fast. Manually reading every inquiry and deciding who to call first wastes the "golden window" — the first few minutes after a lead comes in. Sales teams need instant, consistent triage: know who's ready to buy *now* vs. who's just browsing, without a human reading every message first.

## What it does

A lead comes in through a webhook (name, phone, email, message) and is automatically:

1. **Validated** — junk/incomplete leads are filtered before they reach the AI.
2. **Scored** — a LangGraph agent (extract → score → decide) pulls structured details (budget, area, bedrooms, timeline) from the raw message and outputs an urgency score (1–10) with a plain-English reason.
3. **Routed** by score:
   - **Hot (≥8):** instant Slack alert to the agent with budget/area/reason, contact created/updated in HubSpot. (WhatsApp alert node is built and wired, currently deactivated pending a verified WhatsApp Business number — see Notes.)
   - **Warm (5–7):** logged to a dedicated follow-up sheet, contact created/updated in HubSpot.
   - **Cold (<5):** automatic personalized nurture email, no CRM contact created.
4. **Logged** — every lead, regardless of branch, is appended to a single **Lead History Log** (Google Sheets) with a derived Hot/Warm/Cold label, giving a full audit trail on top of HubSpot's "current state" view.
5. **Responded** — the triggering webhook call receives a response only after logging completes, so every request resolves cleanly instead of hanging.

## Architecture

```
Webhook → Validation (n8n) → LangGraph agent (FastAPI, Groq) → Switch (n8n)
                                                                   ├─ Hot  → Slack + WhatsApp* + HubSpot ─┐
                                                                   ├─ Warm → Follow-up Sheet + HubSpot ────┼─→ Lead History Log → Respond to Webhook
                                                                   └─ Cold → Gmail nurture ─────────────────┘

*WhatsApp node built, deactivated (no verified Business number yet)
```

- **n8n** — orchestration: webhook trigger, validation, routing, and all downstream actions (Slack, WhatsApp, Gmail, Sheets, HubSpot), with Continue-On-Fail so a messaging hiccup never blocks lead logging.
- **FastAPI + LangGraph** — the qualification "brain," running as its own service. Built as a 3-node graph (extract → score → decide) rather than a single prompt, so each step is independently testable and debuggable.
- **Groq (Llama / GPT-OSS)** — fast, low-cost inference for extraction and scoring, with retry logic to handle occasional empty/malformed LLM responses.
- **HubSpot** — CRM system of record for Hot and Warm leads. Custom contact properties (Budget, Preferred Area, Urgency Score) are written on every Create-or-Update call, matched on email.
- **Google Sheets** — two roles: a Warm-only follow-up sheet, and a separate append-only Lead History Log capturing every submission (Hot, Warm, Cold) with timestamp and derived temperature label, independent of whatever HubSpot currently holds.

## Stack

n8n · FastAPI · LangGraph · Groq · HubSpot · Slack · WhatsApp (Business API, wired/inactive) · Gmail · Google Sheets

## Metric

Lead → first-contact time: sub-second scoring and routing vs. the industry's typical hours-long manual response.

## Notes

- Test leads use `@example.com` addresses (a reserved, non-deliverable domain) to avoid emailing real inboxes during development. The Cold-branch nurture email is fully wired and fires correctly in n8n, but won't visibly land in an inbox unless pointed at a real address — this is a test-data artifact, not a workflow bug.
- HubSpot is fully wired and live for Hot/Warm leads (Create-or-Update on email, with 3 custom properties). Cold leads intentionally skip HubSpot to avoid cluttering the CRM with low-intent browsers — they're still captured in the Lead History Log.
- WhatsApp alerting is built (template message, correct payload) but deactivated, since sending requires a verified WhatsApp Business API number rather than a personal number. Slack currently serves as the live real-time alert channel for Hot leads.
- Multi-channel lead sources (Meta Ads, Property Finder, Bayut) are architected for but not yet wired in this version — the webhook accepts any source that posts the same JSON shape, so adding a new source is a matter of pointing its outbound webhook at this endpoint.
