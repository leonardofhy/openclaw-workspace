#!/usr/bin/env python3
"""
Rank income opportunities based on skills, constraints, and scoring heuristics.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ScoredOpportunity:
    """Opportunity with calculated scores."""
    id: str
    title: str
    category: str
    monthly_twd: int
    time_to_cash: int
    hours_week: int
    probability: str
    career_synergy: str
    risk_flags: List[str]
    score: float
    match_reasons: List[str]


def probability_to_score(prob: str) -> float:
    """Convert probability string to numeric score."""
    mapping = {"low": 0.3, "medium": 0.6, "high": 0.9}
    return mapping.get(prob.lower(), 0.5)


def synergy_to_score(synergy: str) -> float:
    """Convert career synergy to numeric score."""
    mapping = {"low": 0.2, "medium": 0.5, "high": 1.0}
    return mapping.get(synergy.lower(), 0.5)


def calculate_opportunity_score(
    opp: Dict[str, Any],
    constraints: Dict[str, Any],
    skills: Dict[str, List[str]]
) -> tuple[float, List[str]]:
    """
    Calculate composite score for an opportunity.
    
    Scoring factors:
    - Expected value (monthly TWD / time cost)
    - Time to cash (prefer shorter)
    - Probability of success
    - Career synergy
    - Constraint fit (time budget, urgency)
    - Skill match
    """
    
    match_reasons = []
    
    # Base value score: monthly TWD per hour
    hours_per_month = opp["time_cost_hours_week"] * 4.3
    value_per_hour = opp["estimated_monthly_twd"] / max(hours_per_month, 1)
    value_score = min(value_per_hour / 1000, 2.0)  # Normalize, cap at 2.0
    
    # Time to cash score (prefer < urgency)
    urgency_days = constraints.get("urgency_days", 60)
    time_score = 1.0 if opp["time_to_cash_days"] <= urgency_days else 0.5
    if opp["time_to_cash_days"] <= 14:
        time_score = 1.5  # Bonus for very fast cash
        match_reasons.append(f"Fast cash: {opp['time_to_cash_days']} days")
    
    # Probability score
    prob_score = probability_to_score(opp["probability"])
    
    # Career synergy score
    synergy_score = synergy_to_score(opp["career_synergy"])
    if synergy_score >= 0.8:
        match_reasons.append("High career synergy")
    
    # Time budget fit
    time_budget = constraints.get("time_budget_hours_per_week", 5)
    if opp["time_cost_hours_week"] <= time_budget:
        time_fit_score = 1.0
        match_reasons.append(f"Fits {time_budget}h/week budget")
    else:
        time_fit_score = 0.3
        match_reasons.append(f"⚠️ Exceeds time budget ({opp['time_cost_hours_week']}h > {time_budget}h)")
    
    # Preference bonus
    preferences = constraints.get("preferences", {})
    pref_score = 0.0
    if preferences.get("remote") and opp["category"] in ["freelance", "consulting", "remote"]:
        pref_score += 0.3
        match_reasons.append("Remote-friendly")
    if preferences.get("consulting_over_hourly") and opp["category"] == "consulting":
        pref_score += 0.2
        match_reasons.append("Consulting model")
    
    # Avoid flags
    avoid_list = preferences.get("avoid", [])
    for avoid in avoid_list:
        if avoid.lower() in opp["title"].lower() or avoid.lower() in opp.get("notes", "").lower():
            pref_score -= 0.5
            match_reasons.append(f"⚠️ In avoid list: {avoid}")
    
    # Risk flags penalty
    risk_penalty = len(opp.get("risk_flags", [])) * 0.1
    
    # Composite score
    score = (
        value_score * 1.5 +       # Value is important
        time_score * 1.2 +        # Time to cash matters
        prob_score * 1.0 +        # Probability of success
        synergy_score * 0.8 +     # Career fit
        time_fit_score * 1.0 +    # Time budget fit
        pref_score                # Preferences
        - risk_penalty            # Penalties
    )
    
    return score, match_reasons


def rank_opportunities(
    opportunities: List[Dict[str, Any]],
    constraints: Dict[str, Any],
    skills: Dict[str, List[str]]
) -> List[ScoredOpportunity]:
    """Rank all opportunities and return sorted list."""
    
    scored = []
    for opp in opportunities:
        score, reasons = calculate_opportunity_score(opp, constraints, skills)
        
        scored.append(ScoredOpportunity(
            id=opp["id"],
            title=opp["title"],
            category=opp["category"],
            monthly_twd=opp["estimated_monthly_twd"],
            time_to_cash=opp["time_to_cash_days"],
            hours_week=opp["time_cost_hours_week"],
            probability=opp["probability"],
            career_synergy=opp["career_synergy"],
            risk_flags=opp.get("risk_flags", []),
            score=score,
            match_reasons=reasons
        ))
    
    # Sort by score descending
    scored.sort(key=lambda x: x.score, reverse=True)
    return scored


if __name__ == "__main__":
    import sys
    
    # Load data
    scout_dir = Path(__file__).parent.parent
    opp_file = scout_dir / "data" / "opportunities.json"
    constraints_file = scout_dir / "data" / "constraints.json"
    
    with open(opp_file) as f:
        opportunities = json.load(f)
    
    with open(constraints_file) as f:
        constraints = json.load(f)
    
    # Dummy skills for testing
    skills = {"languages": ["Python", "JavaScript"], "frameworks": ["PyTorch"]}
    
    ranked = rank_opportunities(opportunities, constraints, skills)
    
    print(f"{'Rank':<5} {'Title':<50} {'Score':<6} {'$/Month':<10} {'Days':<6}")
    print("=" * 85)
    for i, opp in enumerate(ranked[:15], 1):
        print(f"{i:<5} {opp.title[:48]:<50} {opp.score:>5.2f} {opp.monthly_twd:>9} {opp.time_to_cash:>5}")
