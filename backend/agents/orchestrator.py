# backend/agents/orchestrator.py
"""
Master Orchestrator for PlacementIQ.
Coordinates all sub-agents. FastAPI endpoints call functions from here.
ML scoring engine runs first (fast + reliable), then agents add reasoning layers.
"""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from nba_agent import get_nba_recommendations
from explainability_agent import generate_explainability_narrative
from market_agent import assess_market_shock, scan_portfolio_for_shocks
from career_path_agent import get_career_path_recommendations
from offer_survival_agent import get_offer_survival_score


def score_student_full(student_data: dict) -> dict:
    """
    Full agentic pipeline for a single student scoring request.
    
    Flow:
    1. ML models run first (XGBoost + LightGBM) — fast, deterministic
    2. NBA + Explainability agents run in parallel — agent-driven, contextual
    3. Results merged into final response
    
    This keeps API latency predictable: ML is fast (~50ms),
    agents add ~1–2s for contextual reasoning.
    """
    student_id = student_data.get("student_id", "UNKNOWN")

    # ── Step 1: Run ML scoring engine (fast path) ─────────────────────────────
    try:
        from scoring_engine import ScoringEngine
        engine = ScoringEngine()
        ml_scores = _flatten_score(engine.score_student(student_data))
    except Exception as e:
        # Graceful fallback if scoring engine unavailable
        ml_scores = _fallback_ml_scores(student_data)
        print(f"[Orchestrator] Scoring engine error: {e} -- using fallback")

    # ── Step 2: Enrich context with ML outputs ────────────────────────────────
    student_context = {
        **student_data,
        "risk_band": ml_scores.get("risk_band", "MEDIUM"),
        "placement_6m": ml_scores.get("placement_probability", {}).get("within_6_months", 0.65),
        "peer_percentile": ml_scores.get("peer_benchmark", {}).get("student_percentile", 50),
        "emi_comfort_ratio": ml_scores.get("emi_comfort", {}).get("ratio", 2.5),
        "confidence_level": ml_scores.get("confidence", {}).get("level", "MEDIUM"),
    }

    # ── Step 3: Run NBA + Explainability in parallel ──────────────────────────
    nba_result = {}
    explain_result = {}

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(get_nba_recommendations, student_id, student_context): "nba",
            executor.submit(generate_explainability_narrative, student_id, student_context): "explain",
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                result = future.result(timeout=30)
                if key == "nba":
                    nba_result = result
                else:
                    explain_result = result
            except Exception as e:
                print(f"[Orchestrator] Agent '{key}' error: {e}")

    # ── Step 4: Assemble final response ───────────────────────────────────────
    return {
        **ml_scores,
        "agentic_nba": {
            "reasoning": nba_result.get("reasoning"),
            "actions": nba_result.get("actions", []),
        },
        "agentic_explainability": {
            "summary": explain_result.get("summary"),
            "positive_factors": explain_result.get("positive_factors", []),
            "negative_factors": explain_result.get("negative_factors", []),
            "urgency_note": explain_result.get("urgency_note"),
        }
    }


def score_student_fast(student_data: dict) -> dict:
    """
    ML-only scoring (no agents). Use for bulk scoring or latency-sensitive requests.
    NBA and explainability will use hardcoded fallbacks.
    """
    try:
        from scoring_engine import ScoringEngine
        engine = ScoringEngine()
        return _flatten_score(engine.score_student(student_data))
    except Exception as e:
        return _fallback_ml_scores(student_data)


def _flatten_score(nested: dict) -> dict:
    """Map the nested shape returned by ScoringEngine.score_student into the flat
    shape the rest of the agentic pipeline (and the frontend) expects. Keeps the
    raw nested view under "_raw_ml" for anything that needs the original."""
    pred    = nested.get("prediction", {}) or {}
    explain = nested.get("explainability", {}) or {}
    insights = nested.get("insights", {}) or {}
    probs   = pred.get("placement_probability", {}) or {}
    salary  = pred.get("salary_estimate", {}) or {}
    confidence = explain.get("confidence", {}) or {}
    peer    = insights.get("peer_benchmark", {}) or {}

    p6 = probs.get("6m")
    risk_score = int(round((1 - p6) * 100)) if isinstance(p6, (int, float)) else None

    return {
        "student_id": nested.get("student_id"),
        "risk_band":  pred.get("risk_band"),
        "risk_score": risk_score,
        "placement_probability": {
            "within_3_months":  probs.get("3m"),
            "within_6_months":  probs.get("6m"),
            "within_12_months": probs.get("12m"),
        },
        "salary_estimate": salary,
        "emi_comfort": {
            "ratio": insights.get("emi_comfort_index"),
            "tier":  _emi_tier(insights.get("emi_comfort_index")),
        },
        "confidence": {
            "level":      (confidence.get("rating") or "").upper() or None,
            "percentage": confidence.get("score"),
            "data_gaps":  confidence.get("data_gaps", []),
        },
        "peer_benchmark": {
            "student_percentile":            peer.get("student_percentile"),
            "cohort_median_probability_6m":  peer.get("cohort_median"),
            "cohort":                        peer.get("cohort"),
            "percentile_label":              peer.get("percentile_label"),
        },
        "risk_drivers": explain.get("top_drivers", []),
        "_raw_ml": nested,
    }


def _emi_tier(ratio):
    if not isinstance(ratio, (int, float)):
        return None
    if ratio >= 3.0: return "COMFORTABLE"
    if ratio >= 2.0: return "ADEQUATE"
    if ratio >= 1.0: return "TIGHT"
    return "DISTRESS"


def get_career_paths(student_id: str, student_context: dict) -> dict:
    """Get alternate career path recommendations for a student."""
    return get_career_path_recommendations(student_id, student_context)


def get_shock_report(field_region_pairs: list) -> list:
    """Run the Market Intelligence Agent across a list of field+region pairs."""
    return scan_portfolio_for_shocks(field_region_pairs)


def get_offer_survival(student_id: str, company_name: str) -> dict:
    """Get Offer Survival Score for a student with an active offer."""
    return get_offer_survival_score(student_id, company_name)


def _fallback_ml_scores(student_data: dict) -> dict:
    """Emergency fallback scores when the scoring engine is unavailable."""
    return {
        "student_id": student_data.get("student_id"),
        "risk_band": "MEDIUM",
        "risk_score": 50,
        "placement_probability": {
            "within_3_months": 0.45,
            "within_6_months": 0.68,
            "within_12_months": 0.87
        },
        "salary_estimate": {"low": 35000, "median": 55000, "high": 80000, "currency": "INR"},
        "emi_comfort": {"ratio": 2.5, "tier": "ADEQUATE"},
        "confidence": {"level": "LOW", "percentage": 40, "data_gaps": ["Scoring engine unavailable"]},
        "peer_benchmark": {"student_percentile": 50, "cohort_median_probability_6m": 0.65},
        "risk_drivers": []
    }
