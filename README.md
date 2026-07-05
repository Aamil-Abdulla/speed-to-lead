# Speed-to-Lead Engine

AI-powered lead qualification and routing system for real estate — built for a Dubai brokerage use case (Kirpa Properties AI Officer application).

## Problem

Real estate leads go cold fast. Manually reading every inquiry and deciding who to call first wastes the "golden window" — the first few minutes after a lead comes in. Sales teams need instant, consistent triage: know who's ready to buy *now* vs. who's just browsing, without a human reading every message first.

## What it does

A lead comes in through a webhook (name, phone, email, message) and is automatically:

1. **Validated** — junk/incomplete leads are filtered before they reach the AI.
2. **Scored** — a LangGraph agent (extract → score → decide) pulls structured details (budget, area, bedrooms, timeline) from the raw message and outputs an urgency score (1–10) with a plain-English reason.
3. **Routed** by score:
   - **Hot (8–10):** instant Slack alert to the agent, with budget/area/reason
   - **Warm (5–7):** logged for follow-up
   - **Cold (<5):** automatic personalized nurture email
4. **Logged** — every lead is recorded to Google Sheets regardless of branch.

## Architecture

```
Webhook → Validation (n8n) → LangGraph agent (FastAPI, Groq) → Switch (n8n) → Slack / Sheets / Gmail
```

- **n8n** — orchestration: webhook trigger, validation, routing, and all downstream actions (Slack, Sheets, Gmail), with Continue-On-Fail so a messaging hiccup never blocks lead logging.
- **FastAPI + LangGraph** — the qualification "brain," running as its own service. Built as a 3-node graph (extract → score → decide) rather than a single prompt, so each step is independently testable and debuggable.
- **Groq (Llama / GPT-OSS)** — fast, low-cost inference for extraction and scoring, with retry logic to handle occasional empty/malformed LLM responses.

## Stack

n8n · FastAPI · LangGraph · Groq · Slack · Gmail · Google Sheets

## Metric

Lead → first-contact time: sub-second scoring and routing vs. the industry's typical hours-long manual response.

## Notes

Currently logs to Google Sheets as a lightweight CRM; the same webhook/routing pattern is designed to drop in a real CRM (e.g. HubSpot) without changing the scoring logic. WhatsApp/Twilio calling and multi-channel lead sources (Meta Ads, Property Finder, Bayut) are architected for but not yet wired in this version.
