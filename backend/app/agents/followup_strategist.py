"""
Follow-up Strategist Agent — runs AFTER transcript analysis.
Input:  TranscriptAnalysis + Lead + Campaign context
Output: next_action, sms_message, callback_delta_hours, notes
"""
from __future__ import annotations

import json
import re

from crewai import Agent, Crew, Task
from crewai.tools import tool
from pydantic import BaseModel, Field

from app.core.chroma import query_knowledge
from app.core.llm_factory import get_llm


class FollowUpStrategy(BaseModel):
    next_action: str = Field(
        ...,
        description="One of: SEND_SMS, SCHEDULE_CALLBACK, MARK_NOT_INTERESTED, NEEDS_HUMAN_APPROVAL"
    )
    sms_message: str | None = Field(default=None, max_length=320)
    callback_delta_hours: int | None = Field(default=None, ge=1, le=168)
    notes: str = Field(default="")


@tool("Event Knowledge Base")
def search_event_faq(query: str) -> str:
    """Search the event knowledge base for FAQ answers and seminar details."""
    docs = query_knowledge(query, n_results=3)
    if not docs:
        return "No relevant information found."
    return "\n".join(docs)


def run_followup_strategist(
    intent: str,
    summary: str,
    confidence: int,
    attendees: int,
    concerns: list[str],
    lead_name: str,
    lead_language: str,
    event_name: str,
    event_date: str,
    event_location: str,
    llm_provider: str = "openai",
) -> FollowUpStrategy:
    """
    Decide the best follow-up action based on transcript analysis results.

    Returns:
        FollowUpStrategy with next_action, optional SMS, callback scheduling, and notes.
    """
    llm = get_llm(provider=llm_provider, temperature=0.3)

    agent = Agent(
        role="Sales Follow-Up Strategist",
        goal=(
            "Determine the best next action after an AI call with a senior citizen lead. "
            "Maximize conversion while maintaining trust and not being pushy. "
            "Use the event knowledge base to address any concerns raised."
        ),
        backstory=(
            "You are a senior sales strategist with deep experience in seminar marketing "
            "for the 50+ demographic. You know exactly when to push forward and when to back off."
        ),
        tools=[search_event_faq],
        llm=llm,
        verbose=False,
    )

    task = Task(
        description=f"""
Lead: {lead_name} | Language: {lead_language}
Intent: {intent} | Confidence: {confidence}% | Attendees mentioned: {attendees}
Summary: {summary}
Concerns raised: {", ".join(concerns) if concerns else "None"}

Event: {event_name}
Date: {event_date}
Location: {event_location}

Based on the above, decide the best follow-up action:
- SEND_SMS: If lead is interested or confirmed → draft a brief, warm SMS (no links, max 2 lines)
- SCHEDULE_CALLBACK: If lead asked for callback or was hesitant → set callback_delta_hours
- MARK_NOT_INTERESTED: If lead clearly declined
- NEEDS_HUMAN_APPROVAL: If lead is CONFIRMED or highly interested → escalate to admin

Use the Event Knowledge Base tool if you need to address specific concerns.

Return ONLY valid JSON:
{{
    "next_action": "NEEDS_HUMAN_APPROVAL",
    "sms_message": null,
    "callback_delta_hours": null,
    "notes": "Lead confirmed 2 seats. High confidence."
}}
""",
        expected_output="JSON with next_action, sms_message (or null), callback_delta_hours (or null), notes",
        agent=agent,
    )

    crew = Crew(agents=[agent], tasks=[task], verbose=False)

    try:
        raw = str(crew.kickoff())
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            data = json.loads(match.group())
            return FollowUpStrategy(**data)
    except Exception:
        pass

    # Fallback based on intent
    fallback_map = {
        "CONFIRMED": FollowUpStrategy(next_action="NEEDS_HUMAN_APPROVAL", notes="Auto-escalated based on CONFIRMED intent"),
        "PROBABLY_INTERESTED": FollowUpStrategy(next_action="NEEDS_HUMAN_APPROVAL", notes="Auto-escalated based on PROBABLY_INTERESTED intent"),
        "CALLBACK": FollowUpStrategy(next_action="SCHEDULE_CALLBACK", callback_delta_hours=24),
        "NOT_INTERESTED": FollowUpStrategy(next_action="MARK_NOT_INTERESTED"),
    }
    return fallback_map.get(intent, FollowUpStrategy(next_action="MARK_NOT_INTERESTED"))
