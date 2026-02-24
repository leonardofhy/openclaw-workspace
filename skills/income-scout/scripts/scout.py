#!/usr/bin/env python3
"""
Income Scout - Main orchestrator for finding income opportunities.

Usage:
    python3 scout.py [--output results.md] [--format markdown|json]
"""

import argparse
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Import helpers
from parse_resume import parse_resume
from rank_opportunities import rank_opportunities, ScoredOpportunity
from generate_outreach import generate_template


def load_financial_reality(report_path: Path) -> Dict[str, Any]:
    """Extract key financial metrics from report."""
    if not report_path.exists():
        return {
            "total_assets_twd": "unknown",
            "monthly_income_twd": 20000,
            "burn_rate_twd": "unknown",
            "runway_months": "unknown"
        }
    
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract key numbers
    total_assets = re.search(r'總資產.*?(\d{1,3}(,\d{3})*)\s*TWD', content)
    burn_rate = re.search(r'淨燃燒率.*?(\d{1,3}(,\d{3})*)/月', content)
    runway = re.search(r'預估跑道.*?(\d+\.?\d*)\s*個月', content)
    
    return {
        "total_assets_twd": total_assets.group(1).replace(',', '') if total_assets else "unknown",
        "monthly_income_twd": 20000,
        "burn_rate_twd": burn_rate.group(1).replace(',', '') if burn_rate else "unknown",
        "runway_months": runway.group(1) if runway else "unknown"
    }


def generate_markdown_report(
    skills: Dict[str, List[str]],
    finance: Dict[str, Any],
    constraints: Dict[str, Any],
    ranked_opps: List[ScoredOpportunity],
    top_actions: List[Dict[str, Any]]
) -> str:
    """Generate markdown report."""
    
    report = f"""# Income Scout Report
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 📊 Current Situation

### Financial Reality
- **Total Assets:** {finance['total_assets_twd']} TWD
- **Monthly Income:** {finance['monthly_income_twd']:,} TWD
- **Burn Rate:** {finance['burn_rate_twd']} TWD/month
- **Runway:** {finance['runway_months']} months

### Constraints
- **Time Budget:** {constraints['time_budget_hours_per_week']} hours/week
- **Urgency:** Need cash within {constraints['urgency_days']} days
- **Location:** {constraints['location']}
- **Work Permit:** {constraints['work_permit']}
- **Minimum Target:** {constraints['minimum_monthly_target_twd']:,} TWD/month

---

## 🛠️ Skills Inventory

### Languages
{', '.join(skills.get('languages', [])) if skills.get('languages') else 'None extracted'}

### Frameworks
{', '.join(skills.get('frameworks', [])) if skills.get('frameworks') else 'None extracted'}

### Tools
{', '.join(skills.get('tools', [])) if skills.get('tools') else 'None extracted'}

### Domains
{', '.join(skills.get('domains', [])) if skills.get('domains') else 'None extracted'}

---

## 🎯 Ranked Opportunities (Top 15)

| Rank | Opportunity | Score | $/Month | Days | h/Week | Prob | Synergy | Match Reasons |
|------|------------|-------|---------|------|--------|------|---------|---------------|
"""
    
    for i, opp in enumerate(ranked_opps[:15], 1):
        reasons = '; '.join(opp.match_reasons[:2]) if opp.match_reasons else '-'
        report += f"| {i} | {opp.title[:35]} | {opp.score:.2f} | {opp.monthly_twd:,} | {opp.time_to_cash} | {opp.hours_week} | {opp.probability} | {opp.career_synergy} | {reasons[:40]} |\n"
    
    report += f"""
---

## ⚡ Top 3 Actions (Next 7 Days)

"""
    
    for i, action in enumerate(top_actions, 1):
        report += f"""### {i}. {action['title']}
**Why:** {action['reasoning']}
**Effort:** {action['effort']}
**Expected Result:** {action['expected_result']}
**Action Steps:**
{chr(10).join(['- ' + step for step in action['steps']])}

"""
    
    report += """---

## 📧 Outreach Templates

### Template 1: Short DM (Consulting)
```
"""
    
    # Generate sample templates
    consulting_dm = generate_template("consulting", "short_dm", {
        "name": "[Name]",
        "key_skill": "ML/LLM integration",
        "service_type": "ML prototyping",
        "specific_need": "[their specific problem]"
    })
    
    report += consulting_dm + "\n```\n\n"
    
    report += """### Template 2: Cold Email (Tutoring)
```
"""
    
    tutoring_email = generate_template("tutoring", "cold_email", {
        "subject": "Machine Learning / CS",
        "target_audience": "grad students or interview prep",
        "topic_1": "ML fundamentals & PyTorch",
        "topic_2": "LeetCode interview prep",
        "topic_3": "Research paper reading",
        "rate_range": "1000-1500",
        "availability": "weekday evenings"
    })
    
    report += tutoring_email + "\n```\n\n"
    
    report += """---

## 🚨 Important Notes

1. **Work Permit:** Student visa may restrict on-site work in Taiwan. Verify before accepting local positions.
2. **Time Management:** Protect thesis work (AudioMatters). Only take opportunities that fit 5h/week max.
3. **No Auto-Send:** All outreach templates need manual review and personalization before sending.
4. **Follow-up:** Track applications in a simple spreadsheet (date sent, status, next follow-up).

---

*Generated by income-scout agent*
"""
    
    return report


def main():
    parser = argparse.ArgumentParser(description="Income Scout - Find money-making opportunities")
    parser.add_argument('--output', default='results.md', help='Output file path')
    parser.add_argument('--format', choices=['markdown', 'json'], default='markdown', help='Output format')
    args = parser.parse_args()
    
    # Paths
    scout_dir = Path(__file__).parent.parent
    resume_dir = Path.home() / "Workspace" / "my_resume"
    finance_report = Path.home() / "Workspace" / "little-leo-tools" / "reports" / "2026-02" / "report.md"
    constraints_file = scout_dir / "data" / "constraints.json"
    opportunities_file = scout_dir / "data" / "opportunities.json"
    
    print("🔍 Income Scout Starting...\n")
    
    # Step 1: Load constraints
    print("📋 Loading constraints...")
    with open(constraints_file) as f:
        constraints = json.load(f)
    
    # Step 2: Parse resume
    print("📄 Parsing resume...")
    skills_data = parse_resume(resume_dir)
    skills = skills_data.get("skills", {})
    
    # Step 3: Load financial reality
    print("💰 Loading financial data...")
    finance = load_financial_reality(finance_report)
    
    # Step 4: Load opportunities
    print("🎯 Loading opportunity database...")
    with open(opportunities_file) as f:
        opportunities = json.load(f)
    
    # Step 5: Rank opportunities
    print("📊 Ranking opportunities...")
    ranked = rank_opportunities(opportunities, constraints, skills)
    
    # Step 6: Generate top actions
    print("⚡ Generating action plan...\n")
    top_actions = [
        {
            "title": f"{ranked[0].title}",
            "reasoning": f"Highest score ({ranked[0].score:.2f}). {', '.join(ranked[0].match_reasons[:2])}.",
            "effort": f"{ranked[0].hours_week}h/week",
            "expected_result": f"{ranked[0].monthly_twd:,} TWD/month in ~{ranked[0].time_to_cash} days",
            "steps": [
                "Draft personalized pitch using template above",
                "Identify 5-10 target contacts (LinkedIn, lab connections)",
                "Send outreach (3-5 per day)",
                "Track responses in spreadsheet",
                "Follow up after 3-5 days if no response"
            ]
        },
        {
            "title": f"{ranked[1].title}",
            "reasoning": f"Second-best ({ranked[1].score:.2f}). {', '.join(ranked[1].match_reasons[:2])}.",
            "effort": f"{ranked[1].hours_week}h/week",
            "expected_result": f"{ranked[1].monthly_twd:,} TWD/month in ~{ranked[1].time_to_cash} days",
            "steps": [
                "Research application process (check official website)",
                "Gather required materials (transcript, recommendation letter)",
                "Prepare draft application",
                "Ask advisor (李宏毅) for recommendation if needed",
                "Submit before deadline"
            ]
        },
        {
            "title": f"{ranked[2].title}",
            "reasoning": f"Third option ({ranked[2].score:.2f}). {', '.join(ranked[2].match_reasons[:2])}.",
            "effort": f"{ranked[2].hours_week}h/week",
            "expected_result": f"{ranked[2].monthly_twd:,} TWD/month in ~{ranked[2].time_to_cash} days",
            "steps": [
                "Create profile on relevant platform",
                "Write compelling bio (use template)",
                "Set competitive rate based on market research",
                "Apply to 5-10 suitable postings",
                "Optimize profile based on response rate"
            ]
        }
    ]
    
    # Step 7: Generate output
    if args.format == 'markdown':
        report = generate_markdown_report(skills, finance, constraints, ranked, top_actions)
        output_path = Path(args.output)
        output_path.write_text(report, encoding='utf-8')
        print(f"✅ Report saved to: {output_path}")
        print(f"\nTop 3 opportunities:")
        for i, opp in enumerate(ranked[:3], 1):
            print(f"  {i}. {opp.title} (score: {opp.score:.2f})")
    else:
        # JSON output
        output_data = {
            "generated_at": datetime.now().isoformat(),
            "skills": skills,
            "finance": finance,
            "constraints": constraints,
            "ranked_opportunities": [
                {
                    "rank": i,
                    "id": opp.id,
                    "title": opp.title,
                    "score": opp.score,
                    "monthly_twd": opp.monthly_twd,
                    "time_to_cash_days": opp.time_to_cash,
                    "hours_per_week": opp.hours_week,
                    "match_reasons": opp.match_reasons
                }
                for i, opp in enumerate(ranked, 1)
            ],
            "top_actions": top_actions
        }
        output_path = Path(args.output)
        output_path.write_text(json.dumps(output_data, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"✅ JSON saved to: {output_path}")


if __name__ == "__main__":
    main()
