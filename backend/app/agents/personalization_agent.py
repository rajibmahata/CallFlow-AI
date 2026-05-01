"""
Personalization Agent — runs BEFORE a call is made.
Input:  Lead record
Output: JSON with personalized opener, key hook, language
"""
from __future__ import annotations

import json

from crewai import Agent, Crew, Task

from app.core.llm_factory import get_llm
from app.models.lead import Lead


def run_personalization_agent(lead: Lead, llm_provider: str = "openai") -> dict:
    """
    Generate a personalized call opener for the given lead.

    Returns:
        {
            "opener": "Good morning Mr. Sharma...",
            "key_hook": "retirement planning seminar near Pune",
            "language": "en",
            "tone": "warm"
        }
    """
    llm = get_llm(provider=llm_provider, temperature=0.5)

    agent = Agent(
        role="Call Personalization Specialist",
        goal=(
            "Create a warm, personalized opening for an outbound call to a senior citizen "
            "aged 50+ inviting them to attend a financial seminar. "
            "Speak slowly, clearly, and with genuine warmth. Never be pushy."
        ),
        backstory=(
            "You are an expert at crafting first impressions for phone calls with elderly audiences. "
            "You understand their concerns, respect their time, and make them feel valued immediately."
        ),
        llm=llm,
        verbose=False,
    )

    task_description = f"""
    Create a personalized call opener for this lead:
    - Name: {lead.name}
    - Age: {lead.age or 'unknown'}
    - City: {lead.city or 'unknown'}
    - Preferred Language: {lead.language}

    The call is about a financial planning seminar for people aged 50+.
    Reference: "the letter we recently sent regarding our upcoming seminar."

    Return ONLY valid JSON in this exact format:
    {{
        "opener": "<2-3 sentence warm greeting and context>",
        "key_hook": "<one compelling reason for this specific person to attend>",
        "language": "{lead.language}",
        "tone": "warm"
    }}
    """

    task = Task(
        description=task_description,
        expected_output="JSON object with opener, key_hook, language, tone",
        agent=agent,
    )

    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    raw_result = crew.kickoff()
    result_str = str(raw_result)

    try:
        # Extract JSON from the output (may have surrounding text)
        start = result_str.find("{")
        end = result_str.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result_str[start:end])
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback
    return {
        "opener": f"Good day, may I speak with {lead.name}? I'm calling regarding the letter we sent about our upcoming seminar.",
        "key_hook": "Join us for a complimentary financial planning seminar designed for you.",
        "language": lead.language,
        "tone": "warm",
    }
