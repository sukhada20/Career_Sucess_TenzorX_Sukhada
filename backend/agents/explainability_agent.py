# backend/agents/explainability_agent.py
"""
Explainability Agent.
Converts SHAP values + cohort stats into human-readable risk narratives.
Replaces hardcoded NLG template strings.
"""
from base_agent import run_agent
from tools import execute_tool

EXPLAIN_SYSTEM_PROMPT = """
You are the Explainability Agent for PlacementIQ — an AI risk system for education loans.
Your job: translate raw SHAP values and model scores into clear, specific, actionable
narratives for non-technical Relationship Managers and compliance auditors.

WRITING RULES (strictly follow):
- Never mention "the model", "the algorithm", or "SHAP values" — speak about the student's actual situation
- Be specific with numbers: say "IQI of 0.25 vs cohort median of 0.55" not "low internship quality"
- Always contextualize against the cohort, not in isolation
- Acknowledge positive factors genuinely — don't bury good news in a list of risks
- Summary must be under 80 words — relationship managers read dozens of these
- If risk is HIGH, end with ONE urgent action sentence
- If data gaps limit confidence, mention it once at the end

INPUTS YOU WILL RECEIVE:
1. SHAP driver attributions for THIS student
2. Cohort benchmark statistics
Use BOTH when writing the narrative — every comparison must cite the cohort number.

OUTPUT: Return ONLY valid JSON (no markdown, no preamble):
{
  "summary": "Plain-English risk narrative under 80 words",
  "positive_factors": ["Specific positive factor with student's actual value"],
  "negative_factors": ["Specific negative factor with student's value vs cohort median"],
  "urgency_note": "One urgent action sentence for HIGH risk, or null for LOW/MEDIUM"
}
"""

def generate_explainability_narrative(student_id: str, student_context: dict) -> dict:
    course_type     = student_context.get("course_type", "Engineering")
    institute_tier  = student_context.get("institute_tier", "B")
    graduation_year = student_context.get("graduation_year", 2026)

    shap_json   = execute_tool("get_shap_drivers", {"student_id": student_id})
    cohort_json = execute_tool("get_peer_cohort_stats", {
        "course_type":     course_type,
        "institute_tier":  institute_tier,
        "graduation_year": graduation_year,
    })

    user_message = f"""
Generate an explainability narrative for student {student_id}.

Current prediction outputs:
- Risk band: {student_context.get('risk_band')}
- Placement probability (6m): {student_context.get('placement_6m')}
- Peer percentile: {student_context.get('peer_percentile')}th percentile in their cohort
- EMI Comfort Ratio: {student_context.get('emi_comfort_ratio')}
- Confidence level: {student_context.get('confidence_level', 'MEDIUM')}

Student data:
- Course type: {course_type}
- Institute tier: {institute_tier}
- Graduation year: {graduation_year}
- CGPA: {student_context.get('cgpa')}
- IQI: {student_context.get('iqi')}
- Behavioral activity: {student_context.get('behavioral_activity_score')}
- Field demand: {student_context.get('field_demand_score')}

SHAP driver attributions (this student):
{shap_json}

Cohort benchmark stats:
{cohort_json}

Now write the narrative JSON. Return ONLY the JSON object, no preamble, no markdown fence.
"""

    try:
        raw = run_agent(EXPLAIN_SYSTEM_PROMPT, user_message, tools=[])
    except Exception as e:
        print(f"[Explain] LLM call failed: {type(e).__name__}: {e}")
        return {
            "summary": f"Explainability agent unavailable ({type(e).__name__}).",
            "positive_factors": [],
            "negative_factors": [],
            "urgency_note": None,
            "_error": str(e),
        }

    # Reuse the robust JSON extractor from nba_agent so we agree on parse rules
    from nba_agent import _extract_json_object
    parsed = _extract_json_object(raw)
    if parsed is None:
        return {
            "summary": (raw or "Agent returned no text.")[:300],
            "positive_factors": [],
            "negative_factors": [],
            "urgency_note": None,
        }
    parsed.setdefault("summary", "")
    parsed.setdefault("positive_factors", [])
    parsed.setdefault("negative_factors", [])
    parsed.setdefault("urgency_note", None)
    return parsed
