#!/usr/bin/env python3
"""Cron Optimizer — Analyze openclaw cron jobs for efficiency + cost savings.

Usage:
    python3 skills/shared/cron_optimizer.py           # dry-run analysis
    python3 skills/shared/cron_optimizer.py --apply    # generate openclaw cron commands
    python3 skills/shared/cron_optimizer.py --json     # JSON output
"""

import json
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional

# ── Cost model (relative token weights) ──────────────────────────────
# Based on Anthropic pricing ratios: opus ≈ 5x sonnet, haiku ≈ 0.2x sonnet
MODEL_COST = {
    "anthropic/claude-opus-4-6": 5.0,
    "opus": 5.0,
    "anthropic/claude-sonnet-4-6": 1.0,
    "sonnet": 1.0,
    "(default)": 1.0,  # assume sonnet-class
}

# Rough tokens-per-second for estimation (input+output combined)
TOKENS_PER_SECOND = 40  # conservative average across jobs


@dataclass
class CronJob:
    id: str
    name: str
    schedule_expr: str
    tz: str
    model: str
    timeout_s: Optional[int]
    last_duration_s: float
    last_status: str
    session_target: str
    prompt_preview: str
    enabled: bool
    is_recurring: bool

    @property
    def model_cost(self) -> float:
        return MODEL_COST.get(self.model, 1.0)

    @property
    def runs_per_week(self) -> float:
        return _estimate_runs_per_week(self.schedule_expr)

    @property
    def weekly_tokens(self) -> float:
        return self.last_duration_s * TOKENS_PER_SECOND * self.runs_per_week

    @property
    def weekly_cost_units(self) -> float:
        return self.weekly_tokens * self.model_cost


@dataclass
class Recommendation:
    category: str  # model-downgrade, merge, frequency, timing
    severity: str  # high, medium, low
    jobs: list  # affected job names
    action: str
    reason: str
    estimated_weekly_savings: float = 0  # in cost-units
    apply_commands: list = field(default_factory=list)


def load_jobs() -> list[CronJob]:
    """Load jobs from openclaw cron list --json."""
    result = subprocess.run(
        ["openclaw", "cron", "list", "--json"],
        capture_output=True, text=True, timeout=30
    )
    data = json.loads(result.stdout)
    jobs = []
    for j in data["jobs"]:
        sched = j.get("schedule", {})
        payload = j.get("payload", {})
        state = j.get("state", {})
        is_recurring = sched.get("kind") == "cron"
        jobs.append(CronJob(
            id=j["id"],
            name=j["name"],
            schedule_expr=sched.get("expr", "one-shot") if is_recurring else "one-shot",
            tz=sched.get("tz", "UTC"),
            model=payload.get("model", "(default)"),
            timeout_s=payload.get("timeoutSeconds"),
            last_duration_s=state.get("lastDurationMs", 0) / 1000,
            last_status=state.get("lastStatus", "unknown"),
            session_target=j.get("sessionTarget", "main"),
            prompt_preview=payload.get("message", "")[:300],
            enabled=j.get("enabled", True),
            is_recurring=is_recurring,
        ))
    return jobs


def _estimate_runs_per_week(expr: str) -> float:
    """Rough estimate of weekly runs from a cron expression."""
    if expr == "one-shot":
        return 0
    parts = expr.split()
    if len(parts) < 5:
        return 7  # fallback daily

    minute, hour, dom, month, dow = parts[:5]

    # Day-of-week filter
    if dow == "*":
        days_per_week = 7
    elif "-" in dow:
        lo, hi = dow.split("-")
        days_per_week = int(hi) - int(lo) + 1
    elif "," in dow:
        days_per_week = len(dow.split(","))
    else:
        days_per_week = 1

    # Hours per day
    if hour == "*":
        hours_per_day = 24
    elif "," in hour:
        hours_per_day = len(hour.split(","))
    elif "-" in hour:
        lo, hi = hour.split("-")
        hours_per_day = int(hi) - int(lo) + 1
    elif "/" in hour:
        step = int(hour.split("/")[1])
        hours_per_day = 24 // step
    else:
        hours_per_day = 1

    # Minutes per hour
    if minute == "*":
        runs_per_hour = 60
    elif "/" in minute:
        step = int(minute.split("/")[1])
        runs_per_hour = 60 // step
    elif "," in minute:
        runs_per_hour = len(minute.split(","))
    else:
        runs_per_hour = 1

    return days_per_week * hours_per_day * runs_per_hour


def analyze_model_waste(jobs: list[CronJob]) -> list[Recommendation]:
    """Find jobs using opus for simple tasks."""
    recs = []
    for j in jobs:
        if not j.is_recurring:
            continue
        if j.model_cost < 5.0:
            continue

        # Check if the job is simple enough for sonnet/haiku
        is_simple = (
            j.last_duration_s < 60
            or "Run:" in j.prompt_preview and len(j.prompt_preview) < 200
            or "提醒" in j.prompt_preview  # reminder-type
        )

        if is_simple:
            current_weekly = j.weekly_cost_units
            sonnet_weekly = j.weekly_tokens * 1.0
            savings = current_weekly - sonnet_weekly

            # Determine target model
            if j.last_duration_s < 15:
                target = "haiku"
                target_full = "anthropic/claude-haiku-4-5-20251001"
                target_cost = 0.2
                savings = current_weekly - j.weekly_tokens * target_cost
            else:
                target = "sonnet"
                target_full = "anthropic/claude-sonnet-4-6"
                target_cost = 1.0

            recs.append(Recommendation(
                category="model-downgrade",
                severity="high",
                jobs=[j.name],
                action=f"Downgrade from opus → {target}",
                reason=(
                    f"This job runs {j.last_duration_s:.0f}s and "
                    f"{'just sends a reminder' if '提醒' in j.prompt_preview else 'runs a simple shell script'}. "
                    f"Opus is {j.model_cost:.0f}x the cost of sonnet for no quality benefit here."
                ),
                estimated_weekly_savings=savings,
                apply_commands=[
                    f'openclaw cron update {j.id} --model {target_full}'
                ],
            ))
    return recs


def analyze_timing_collisions(jobs: list[CronJob]) -> list[Recommendation]:
    """Find jobs scheduled at exactly the same time."""
    recs = []
    recurring = [j for j in jobs if j.is_recurring]

    # Group by (hour, dow pattern)
    from collections import defaultdict
    time_groups = defaultdict(list)
    for j in recurring:
        parts = j.schedule_expr.split()
        if len(parts) >= 5:
            # Normalize: group by hour + dow
            key = (parts[1], parts[4])
            time_groups[key].append(j)

    for (hour, dow), group in time_groups.items():
        if len(group) < 2:
            continue
        # Check for exact minute collisions or very close (<15min)
        minutes = []
        for j in group:
            m = j.schedule_expr.split()[0]
            if m.isdigit():
                minutes.append((int(m), j))

        minutes.sort(key=lambda x: x[0])
        for i in range(len(minutes) - 1):
            m1, j1 = minutes[i]
            m2, j2 = minutes[i + 1]
            if m1 == m2:
                recs.append(Recommendation(
                    category="timing",
                    severity="medium",
                    jobs=[j1.name, j2.name],
                    action=f"Stagger by 5-10 minutes to avoid resource contention",
                    reason=(
                        f"Both run at :{m1:02d} on hour {hour}. "
                        f"Concurrent isolated sessions compete for CPU/memory. "
                        f"Combined duration: {j1.last_duration_s + j2.last_duration_s:.0f}s."
                    ),
                ))
    return recs


def analyze_sunday_collision(jobs: list[CronJob]) -> list[Recommendation]:
    """Specifically check the Sunday 21:00 pile-up."""
    sunday_21 = [
        j for j in jobs if j.is_recurring
        and j.schedule_expr.startswith("0 21")
        and ("0" in j.schedule_expr.split()[4] or j.schedule_expr.split()[4] == "*")
    ]
    if len(sunday_21) >= 3:
        total_duration = sum(j.last_duration_s for j in sunday_21)
        return [Recommendation(
            category="timing",
            severity="high",
            jobs=[j.name for j in sunday_21],
            action="Stagger: 20:30 / 21:00 / 21:30 instead of all at 21:00",
            reason=(
                f"{len(sunday_21)} jobs compete at Sunday 21:00. "
                f"Combined runtime: {total_duration:.0f}s ({total_duration/60:.1f}min). "
                f"This causes resource contention and potential timeouts "
                f"(週排程生成 already hits its 120s timeout)."
            ),
            apply_commands=[
                f'openclaw cron update {sunday_21[0].id} --schedule "30 20 * * 0"  # move to 20:30',
                f'# Keep {sunday_21[1].name} at 21:00',
                f'openclaw cron update {sunday_21[2].id} --schedule "30 21 * * 0"  # move to 21:30',
            ] if len(sunday_21) >= 3 else [],
        )]
    return []


def analyze_morning_cluster(jobs: list[CronJob]) -> list[Recommendation]:
    """Check the 08:00-08:30 morning cluster for merge opportunity."""
    morning = []
    for j in jobs:
        if not j.is_recurring:
            continue
        parts = j.schedule_expr.split()
        if len(parts) >= 2 and parts[1] == "8" and parts[4] == "*":
            morning.append(j)

    if len(morning) >= 3:
        names = [j.name for j in morning]
        total_dur = sum(j.last_duration_s for j in morning)
        return [Recommendation(
            category="merge",
            severity="low",
            jobs=names,
            action="Consider chaining into a single 'morning-pipeline' job",
            reason=(
                f"3 sequential jobs at 08:00→08:12→08:30 form a natural pipeline: "
                f"schedule refresh → sync to GCal/Todoist → morning overview. "
                f"Total: {total_dur:.0f}s. Each session has ~10s startup overhead, "
                f"so merging saves ~20s startup + reduces scheduling fragility "
                f"(if 08:00 is late, 08:12 runs on stale data). "
                f"However, isolation is also a valid design — flagging as low severity."
            ),
        )]
    return []


def analyze_ntuais_duplicate(jobs: list[CronJob]) -> list[Recommendation]:
    """NTUAIS daily + evening check overlap."""
    ntuais = [j for j in jobs if "NTUAIS" in j.name and "每日" in j.name or "補救" in j.name]
    ntuais = [j for j in jobs if j.is_recurring and "NTUAIS" in j.name and ("15 分鐘" in j.name or "補救" in j.name)]
    if len(ntuais) >= 2:
        opus_job = next((j for j in ntuais if j.model_cost >= 5.0), None)
        return [Recommendation(
            category="merge",
            severity="medium",
            jobs=[j.name for j in ntuais],
            action="Merge into single job with conditional logic, downgrade to haiku",
            reason=(
                f"The 晚間補救 check (21:30) is literally 'if you didn't do the 16:30 one, do it now'. "
                f"Both are <10s reminder-type jobs. The evening one uses opus (5x cost) "
                f"for a 3-line Chinese reminder — massive waste. "
                f"Merge into one job at 16:30 that also sets a 21:30 follow-up only if needed, "
                f"or keep both but downgrade both to haiku."
            ),
            estimated_weekly_savings=(
                opus_job.weekly_cost_units - opus_job.weekly_tokens * 0.2
                if opus_job else 0
            ),
            apply_commands=[
                f'openclaw cron update {opus_job.id} --model anthropic/claude-haiku-4-5-20251001'
            ] if opus_job else [],
        )]
    return []


def analyze_long_running(jobs: list[CronJob]) -> list[Recommendation]:
    """Flag jobs with suspiciously long durations."""
    recs = []
    for j in jobs:
        if not j.is_recurring:
            continue
        if j.last_duration_s > 600:  # >10 minutes
            recs.append(Recommendation(
                category="performance",
                severity="medium",
                jobs=[j.name],
                action=f"Investigate why this takes {j.last_duration_s:.0f}s ({j.last_duration_s/60:.1f}min)",
                reason=(
                    f"A '{j.name}' taking {j.last_duration_s/60:.1f} minutes is unusual. "
                    f"This burns ~{j.last_duration_s * TOKENS_PER_SECOND:,.0f} tokens per run. "
                    f"Check if it's doing unnecessary LLM reasoning for tasks that could be scripted, "
                    f"or if it's stuck in retry loops."
                ),
            ))
    return recs


def analyze_weekly_research(jobs: list[CronJob]) -> list[Recommendation]:
    """Check weekly-research-summary opus usage."""
    for j in jobs:
        if "weekly-research-summary" in j.name and j.model_cost >= 5.0:
            current = j.weekly_cost_units
            sonnet_cost = j.weekly_tokens * 1.0
            return [Recommendation(
                category="model-downgrade",
                severity="medium",
                jobs=[j.name],
                action="Downgrade from opus → sonnet",
                reason=(
                    f"This runs weekly (191s) summarizing research notes. "
                    f"Sonnet 4.6 handles summarization well — opus quality gain "
                    f"is marginal for this task type. Saves {current - sonnet_cost:,.0f} "
                    f"cost-units/week (4x reduction)."
                ),
                estimated_weekly_savings=current - sonnet_cost,
                apply_commands=[
                    f'openclaw cron update {j.id} --model anthropic/claude-sonnet-4-6'
                ],
            )]
    return []


def format_report(jobs: list[CronJob], recs: list[Recommendation]) -> str:
    """Format human-readable report."""
    lines = []
    lines.append("=" * 70)
    lines.append("  CRON OPTIMIZER REPORT")
    lines.append("=" * 70)

    # ── Current State ──
    recurring = [j for j in jobs if j.is_recurring]
    oneshot = [j for j in jobs if not j.is_recurring]
    lines.append(f"\n📊 Current State: {len(recurring)} recurring jobs, {len(oneshot)} one-shot reminders\n")

    # Cost breakdown by model
    lines.append("── Weekly Cost by Model ──")
    model_costs = {}
    for j in recurring:
        model_costs.setdefault(j.model, {"jobs": 0, "cost": 0, "tokens": 0})
        model_costs[j.model]["jobs"] += 1
        model_costs[j.model]["cost"] += j.weekly_cost_units
        model_costs[j.model]["tokens"] += j.weekly_tokens

    for model, info in sorted(model_costs.items(), key=lambda x: -x[1]["cost"]):
        multiplier = MODEL_COST.get(model, 1.0)
        lines.append(
            f"  {model:40s}  {info['jobs']} jobs  "
            f"{info['tokens']:>10,.0f} tokens  "
            f"×{multiplier:.1f}  = {info['cost']:>12,.0f} cost-units"
        )

    total_cost = sum(j.weekly_cost_units for j in recurring)
    total_tokens = sum(j.weekly_tokens for j in recurring)
    lines.append(f"  {'TOTAL':40s}         {total_tokens:>10,.0f} tokens           {total_cost:>12,.0f} cost-units/week")

    # ── Top consumers ──
    lines.append("\n── Top 5 Most Expensive Jobs (weekly) ──")
    by_cost = sorted(recurring, key=lambda j: j.weekly_cost_units, reverse=True)
    for i, j in enumerate(by_cost[:5], 1):
        pct = j.weekly_cost_units / total_cost * 100 if total_cost else 0
        lines.append(
            f"  {i}. {j.name:40s}  {j.weekly_cost_units:>10,.0f} cost-units "
            f"({pct:4.1f}%)  [{j.model}, {j.last_duration_s:.0f}s×{j.runs_per_week:.0f}/wk]"
        )

    # ── Recommendations ──
    lines.append(f"\n{'=' * 70}")
    lines.append(f"  RECOMMENDATIONS ({len(recs)} found)")
    lines.append(f"{'=' * 70}")

    total_savings = sum(r.estimated_weekly_savings for r in recs)

    for i, r in enumerate(recs, 1):
        severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}[r.severity]
        lines.append(f"\n{severity_icon} [{r.severity.upper()}] #{i}: {r.category.upper()}")
        lines.append(f"  Jobs: {', '.join(r.jobs)}")
        lines.append(f"  Action: {r.action}")
        lines.append(f"  Why: {r.reason}")
        if r.estimated_weekly_savings > 0:
            lines.append(f"  💰 Estimated savings: {r.estimated_weekly_savings:,.0f} cost-units/week")
        if r.apply_commands:
            lines.append(f"  Commands:")
            for cmd in r.apply_commands:
                lines.append(f"    $ {cmd}")

    # ── Summary ──
    lines.append(f"\n{'=' * 70}")
    lines.append(f"  SUMMARY")
    lines.append(f"{'=' * 70}")
    lines.append(f"  Total weekly cost (current):  {total_cost:>12,.0f} cost-units")
    if total_savings > 0:
        lines.append(f"  Potential weekly savings:      {total_savings:>12,.0f} cost-units")
        lines.append(f"  Savings percentage:           {total_savings/total_cost*100:>11.1f}%")
        lines.append(f"  After optimization:           {total_cost - total_savings:>12,.0f} cost-units")
    lines.append("")

    return "\n".join(lines)


def main():
    apply_mode = "--apply" in sys.argv
    json_mode = "--json" in sys.argv

    jobs = load_jobs()

    # Run all analyzers
    recs = []
    recs.extend(analyze_model_waste(jobs))
    recs.extend(analyze_ntuais_duplicate(jobs))
    recs.extend(analyze_weekly_research(jobs))
    recs.extend(analyze_sunday_collision(jobs))
    recs.extend(analyze_timing_collisions(jobs))
    recs.extend(analyze_morning_cluster(jobs))
    recs.extend(analyze_long_running(jobs))

    # Sort: high → medium → low
    severity_order = {"high": 0, "medium": 1, "low": 2}
    recs.sort(key=lambda r: severity_order.get(r.severity, 9))

    if json_mode:
        output = {
            "jobs_analyzed": len([j for j in jobs if j.is_recurring]),
            "recommendations": [
                {
                    "category": r.category,
                    "severity": r.severity,
                    "jobs": r.jobs,
                    "action": r.action,
                    "reason": r.reason,
                    "weekly_savings": r.estimated_weekly_savings,
                    "commands": r.apply_commands,
                }
                for r in recs
            ],
            "total_weekly_savings": sum(r.estimated_weekly_savings for r in recs),
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    print(format_report(jobs, recs))

    if apply_mode:
        print("\n🔧 APPLY MODE — Generating commands:\n")
        commands = []
        for r in recs:
            commands.extend(r.apply_commands)
        if not commands:
            print("  No auto-applicable commands. Recommendations require manual review.")
        else:
            for cmd in commands:
                if cmd.startswith("#"):
                    print(f"  {cmd}")
                else:
                    print(f"  $ {cmd}")
            print(f"\n  Run these commands to apply. Total: {len(commands)} changes.")
    else:
        has_commands = any(r.apply_commands for r in recs)
        if has_commands:
            print("💡 Run with --apply to generate executable commands.")


if __name__ == "__main__":
    main()
