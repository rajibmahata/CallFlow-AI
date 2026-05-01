"""
Transcript Analyzer Agent — runs AFTER a call ends.
Input:  Call transcript text
Output: Structured JSON with intent, sentiment, summary, confidence
"""
from __future__ import annotations

import json
import re

from crewai import Agent, Crew, Task
from pydantic import BaseModel, Field, field_validator

from app.core.llm_factory import get_llm


class TranscriptAnalysis(BaseModel):
    """Validated output from the transcript analyzer."""

    intent: str = Field(
        ...,
        description="One of: CONFIRMED, PROBABLY_INTERESTED, CALLBACK, NOT_INTERESTED"
    )
    attendees: int = Field(default=1, ge=1, le=20)
    questions_asked: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    summary: str = Field(..., max_length=300)
    confidence: int = Field(..., ge=0, le=100)
    sentiment_score: int = Field(default=50, ge=0, le=100)

    @field_validator("intent")
    @classmethod
    def _valid_intent(cls, v: str) -> str:
        valid = {"CONFIRMED", "PROBABLY_INTERESTED", "CALLBACK", "NOT_INTERESTED"}
        v_upper = v.upper()
        if v_upper not in valid:
            return "NOT_INTERESTED"
        return v_upper


_FALLBACK_ANALYSIS = TranscriptAnalysis(
    intent="NOT_INTERESTED",
    attendees=1,
    questions_asked=[],
    concerns=[],
    summary="Transcript could not be analyzed.",
    confidence=0,
    sentiment_score=30,
)


def run_transcript_analyzer(transcript: str, llm_provider: str = "openai") -> TranscriptAnalysis:
    """
    Analyze a call transcript and return structured intent + sentiment.

    Args:
        transcript: Full call transcript text.
        llm_provider: "openai" or "deepseek"

    Returns:
        TranscriptAnalysis validated Pydantic model.
    """
    if not transcript or len(transcript.strip()) < 20:
        return _FALLBACK_ANALYSIS

    llm = get_llm(provider=llm_provider, temperature=0.1)

    agent = Agent(
        role="Call Transcript Intelligence Analyst",
        goal=(
            "Analyze outbound call transcripts to determine lead intent, sentiment, "
            "and key information relevant to seminar event attendance. "
            "Be precise and conservative — only mark CONFIRMED if the person clearly agreed."
        ),
        backstory=(
            "You specialize in analyzing sales call transcripts with elderly demographics. "
            "You understand hesitation, indirect speech, and how seniors express interest. "
            "You produce structured outputs used to prioritize human follow-up."
        ),
        llm=llm,
        verbose=False,
    )

    task = Task(
        description=f"""
Analyze this call transcript carefully:

---TRANSCRIPT START---
{transcript}
---TRANSCRIPT END---

Classify the lead's intent as exactly one of:
- CONFIRMED: Lead clearly said YES, agreed to attend, or confirmed a specific number of seats
- PROBABLY_INTERESTED: Lead showed interest, asked questions, didn't refuse, or needs follow-up
- CALLBACK: Lead explicitly asked to be called back later
- NOT_INTERESTED: Lead declined, hung up, was rude, or showed no interest

Extract:
- Number of attendees mentioned (default: 1)
- Questions the lead asked (as a list)
- Concerns or objections raised (as a list)

Generate:
- A summary of the call in maximum 2 sentences
- A confidence score (0-100) for your intent classification
- A sentiment score (0=very negative, 50=neutral, 100=very positive)

Return ONLY valid JSON in this exact format:
{{
    "intent": "CONFIRMED|PROBABLY_INTERESTED|CALLBACK|NOT_INTERESTED",
    "attendees": 1,
    "questions_asked": ["question1", "question2"],
    "concerns": ["concern1"],
    "summary": "Lead was warm and asked about the venue. Expressed interest but wanted to confirm with spouse.",
    "confidence": 75,
    "sentiment_score": 65
}}
""",
        expected_output="JSON object with intent, attendees, questions_asked, concerns, summary, confidence, sentiment_score",
        agent=agent,
    )

    crew = Crew(agents=[agent], tasks=[task], verbose=False)

    for attempt in range(2):
        try:
            raw = str(crew.kickoff())
            # Extract JSON block
            match = re.search(r"\{[\s\S]*\}", raw)
            if match:
                data = json.loads(match.group())
                return TranscriptAnalysis(**data)
        except (json.JSONDecodeError, ValueError, Exception):
            if attempt == 1:
                break

    return _FALLBACK_ANALYSIS
