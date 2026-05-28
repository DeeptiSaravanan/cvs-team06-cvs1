"""
Insight Agent — Natural Language Interface for Healthcare Identification

End users type plain-language queries; the agent interprets intent,
runs analysis over the patient data, and returns insight outputs.

Usage:
    OPENAI_API_KEY=sk-xxx python insight_agent.py

If no OPENAI_API_KEY is set, the agent falls back to a rule-based
intent parser for common query patterns.
"""

import os
import json
import re
import statistics
from typing import List, Dict, Optional, Callable
from dataclasses import asdict

from identification_agent import (
    PATIENT_DATA,
    compute_trend_metrics,
    detect_issues,
    TrendMetrics,
    DetectedIssue,
)


class InsightAgent:
    """Agent that translates plain-language queries into data insights."""

    def __init__(self):
        self.patients = PATIENT_DATA
        self.metrics = [compute_trend_metrics(p) for p in self.patients]
        self.issues = detect_issues(self.patients)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self._build_rule_registry()

    # ------------------------------------------------------------------
    # 1. LLM-based intent parsing (primary path)
    # ------------------------------------------------------------------

    def _call_llm(self, user_query: str) -> Optional[Dict]:
        """Use OpenAI to map user query -> structured intent."""
        if not self.openai_api_key:
            return None

        try:
            import openai
        except ImportError:
            return None

        client = openai.OpenAI(api_key=self.openai_api_key)

        system_prompt = (
            "You are an insight extraction engine for a pharmacy analytics system.\n"
            "Your job is to map a user's plain-language question into a JSON intent.\n\n"
            "Available intents (with optional params):\n"
            "  - list_issues : { severity_filter?: 'critical'|'high'|'medium'|'low'|'all' }\n"
            "  - trend_summary : { condition?: 'cardiovascular'|'diabetic'|'all' }\n"
            "  - find_patients : { risk_flags?: ['diabetic_drop','cv_drop','low_persistence','high_cost','high_branded'], age_tier?: string, insurance_type?: string }\n"
            "  - cohort_stats : { dimension: 'age_tier'|'insurance_type'|'gender', metric?: 'fills'|'cost'|'persistence' }\n"
            "  - nudge_effectiveness : {}\n"
            "  - patient_detail : { patient_id: string }\n"
            "  - compare_cohorts : { group_a: {age_tier?:string, insurance_type?:string}, group_b: {age_tier?:string, insurance_type?:string}, metric: string }\n"
            "\n"
            "Respond ONLY with valid JSON in this exact shape:\n"
            '{"intent": "<name>", "params": { ... }}'
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ],
            temperature=0.0,
            max_tokens=300,
        )

        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw)

    # ------------------------------------------------------------------
    # 2. Rule-based fallback intent parser
    # ------------------------------------------------------------------

    def _build_rule_registry(self):
        self.rule_patterns: List[tuple] = [
            # Issues
            (r"issues|problems|what.*wrong|red flags|alerts|concerns", "list_issues", {"severity_filter": "all"}),
            (r"critical issues|most urgent|top priority|critical problems", "list_issues", {"severity_filter": "critical"}),
            (r"high priority|high severity|serious issues", "list_issues", {"severity_filter": "high"}),
            # Trends
            (r"trends|pattern|what.*see|overview|summary|insights", "trend_summary", {"condition": "all"}),
            (r"diabetic trend|diabetes trend|diabetic fills|diabetes", "trend_summary", {"condition": "diabetic"}),
            (r"cardiovascular trend|heart trend|cardio trend|cardiovascular", "trend_summary", {"condition": "cardiovascular"}),
            # Patients at risk
            (r"high risk|at risk|risky patients|vulnerable|which patients", "find_patients", {"risk_flags": ["diabetic_drop","cv_drop","low_persistence","high_cost"]}),
            (r"low persistence|not persistent|adherence problem", "find_patients", {"risk_flags": ["low_persistence"]}),
            (r"high cost|expensive|cost burden|copay|deductible", "find_patients", {"risk_flags": ["high_cost"]}),
            (r"branded.*drug|brand name|generic switch", "find_patients", {"risk_flags": ["high_branded"]}),
            # Cohorts
            (r"cohort|segment|group|by age|by insurance|compare", "cohort_stats", {"dimension": "age_tier"}),
            (r"by insurance|insurance type|plan type", "cohort_stats", {"dimension": "insurance_type"}),
            (r"by gender|male vs female|gender", "cohort_stats", {"dimension": "gender"}),
            # Nudges
            (r"nudge|intervention|reminder|effectiveness|what worked|success rate", "nudge_effectiveness", {}),
            # Patient detail
            (r"patient (PT-\w+|\d+)|tell me about (PT-\w+|\d+)|detail for (PT-\w+|\d+)", "patient_detail", {}),
        ]

    def _rule_parse(self, query: str) -> Optional[Dict]:
        q = query.lower()
        for pattern, intent, default_params in self.rule_patterns:
            if re.search(pattern, q):
                params = dict(default_params)
                # Extract patient ID if present
                m = re.search(r"(PT-\w+)", query)
                if m and intent == "patient_detail":
                    params["patient_id"] = m.group(1)
                return {"intent": intent, "params": params}
        return None

    # ------------------------------------------------------------------
    # 3. Intent handlers (the actual analysis)
    # ------------------------------------------------------------------

    def handle_list_issues(self, params: Dict) -> Dict:
        severity_filter = params.get("severity_filter", "all")
        filtered = self.issues if severity_filter == "all" else [i for i in self.issues if i.severity == severity_filter]
        return {
            "answer_type": "issue_list",
            "count": len(filtered),
            "issues": [asdict(i) for i in filtered],
            "narrative": self._narrate_issues(filtered, severity_filter),
        }

    def handle_trend_summary(self, params: Dict) -> Dict:
        condition = params.get("condition", "all")
        if condition == "diabetic":
            changes = [m.diabetic_fill_velocity_change for m in self.metrics if m.diabetic_fill_velocity_change is not None and m.diabetic_fill_velocity_change != float("inf")]
            drops = sum(1 for m in self.metrics if m.diabetic_drop_flag)
            narrative = (
                f"Diabetic fill velocity: mean change {statistics.mean(changes):.0%} across patients with prior history. "
                f"{drops} patient(s) show a significant drop or cessation."
            )
        elif condition == "cardiovascular":
            changes = [m.cv_fill_velocity_change for m in self.metrics if m.cv_fill_velocity_change is not None and m.cv_fill_velocity_change != float("inf")]
            drops = sum(1 for m in self.metrics if m.cv_drop_flag)
            narrative = (
                f"Cardiovascular fill velocity: mean change {statistics.mean(changes):.0%} across patients with prior history. "
                f"{drops} patient(s) show a significant drop or cessation."
            )
        else:
            diabetic_changes = [m.diabetic_fill_velocity_change for m in self.metrics if m.diabetic_fill_velocity_change is not None and m.diabetic_fill_velocity_change != float("inf")]
            cv_changes = [m.cv_fill_velocity_change for m in self.metrics if m.cv_fill_velocity_change is not None and m.cv_fill_velocity_change != float("inf")]
            diabetic_drops = sum(1 for m in self.metrics if m.diabetic_drop_flag)
            cv_drops = sum(1 for m in self.metrics if m.cv_drop_flag)
            low_persist = sum(1 for m in self.metrics if m.low_persistence_flag)
            high_cost = sum(1 for m in self.metrics if m.high_copay_flag or m.high_deductible_flag)
            narrative = (
                f"Overall trends across {len(self.patients)} patients:\n"
                f"  • Cardiovascular: avg velocity change {statistics.mean(cv_changes):.0%}, {cv_drops} drop(s)\n"
                f"  • Diabetic: avg velocity change {statistics.mean(diabetic_changes):.0%}, {diabetic_drops} drop(s)\n"
                f"  • Low persistence (<90d): {low_persist} patient(s)\n"
                f"  • High cost burden: {high_cost} patient(s)"
            )
        return {"answer_type": "trend_summary", "condition": condition, "narrative": narrative}

    def handle_find_patients(self, params: Dict) -> Dict:
        flags = params.get("risk_flags", [])
        age_tier = params.get("age_tier")
        insurance_type = params.get("insurance_type")

        results = []
        for m in self.metrics:
            if age_tier and m.age_tier != age_tier:
                continue
            if insurance_type and m.insurance_type != insurance_type:
                continue
            matched = False
            if "diabetic_drop" in flags and m.diabetic_drop_flag:
                matched = True
            if "cv_drop" in flags and m.cv_drop_flag:
                matched = True
            if "low_persistence" in flags and m.low_persistence_flag:
                matched = True
            if "high_cost" in flags and (m.high_copay_flag or m.high_deductible_flag):
                matched = True
            if "high_branded" in flags and m.high_branded_flag:
                matched = True
            if matched:
                results.append({
                    "patient_id": m.patient_id,
                    "age": m.age,
                    "gender": m.gender,
                    "insurance_type": m.insurance_type,
                    "age_tier": m.age_tier,
                    "persistence_days": m.persistence_days,
                    "copay": m.copay_amount,
                    "deductible": m.deductible_amount,
                    "branded_pct": m.branded_prescription_pct,
                    "diabetic_drop": m.diabetic_drop_flag,
                    "cv_drop": m.cv_drop_flag,
                })

        narrative = f"Found {len(results)} patient(s) matching your criteria."
        if results:
            narrative += f" IDs: {', '.join(r['patient_id'] for r in results)}."
        return {"answer_type": "patient_list", "count": len(results), "patients": results, "narrative": narrative}

    def handle_cohort_stats(self, params: Dict) -> Dict:
        dimension = params.get("dimension", "age_tier")
        groups: Dict[str, List[TrendMetrics]] = {}
        for m in self.metrics:
            key = getattr(m, dimension, "unknown")
            groups.setdefault(key, []).append(m)

        stats = []
        for group_name, members in sorted(groups.items()):
            avg_persist = statistics.mean(m.persistence_days for m in members)
            avg_copay = statistics.mean(m.copay_amount for m in members)
            avg_fills = statistics.mean(m.total_fills_12m for m in members)
            stats.append({
                "group": group_name,
                "count": len(members),
                "avg_persistence_days": round(avg_persist, 1),
                "avg_copay": round(avg_copay, 2),
                "avg_fills_12m": round(avg_fills, 1),
            })

        narrative = f"Cohort breakdown by {dimension}:\n" + "\n".join(
            f"  • {s['group']}: {s['count']} patients, avg persistence {s['avg_persistence_days']}d, avg copay ${s['avg_copay']}, avg fills {s['avg_fills_12m']}"
            for s in stats
        )
        return {"answer_type": "cohort_stats", "dimension": dimension, "groups": stats, "narrative": narrative}

    def handle_nudge_effectiveness(self, params: Dict) -> Dict:
        from collections import defaultdict
        nudge_stats = defaultdict(lambda: {"success": 0, "total": 0})
        for m in self.metrics:
            if m.historical_nudge_type != "none":
                nudge_stats[m.historical_nudge_type]["total"] += 1
                nudge_stats[m.historical_nudge_type]["success"] += m.outcome_refill_completed

        rows = []
        for nudge, stats in sorted(nudge_stats.items()):
            rate = stats["success"] / stats["total"] if stats["total"] else 0
            rows.append({"nudge_type": nudge, "total": stats["total"], "success_rate": round(rate, 2)})

        narrative = "Nudge effectiveness summary:\n" + "\n".join(
            f"  • {r['nudge_type']}: {r['success_rate']:.0%} success across {r['total']} patients"
            for r in rows
        )
        return {"answer_type": "nudge_effectiveness", "nudges": rows, "narrative": narrative}

    def handle_patient_detail(self, params: Dict) -> Dict:
        pid = params.get("patient_id", "")
        patient = next((p for p in self.patients if p["patient_id"] == pid), None)
        if not patient:
            return {"answer_type": "error", "narrative": f"Patient {pid} not found."}
        m = compute_trend_metrics(patient)
        narrative = (
            f"Patient {pid} ({m.age}, {m.gender}, {m.age_tier}, {m.insurance_type}):\n"
            f"  • Total fills (12M): {m.total_fills_12m}\n"
            f"  • Persistence: {m.persistence_days} days {'(LOW)' if m.low_persistence_flag else ''}\n"
            f"  • Copay: ${m.copay_amount}, Deductible: ${m.deductible_amount}\n"
            f"  • Branded %: {m.branded_prescription_pct:.0%}\n"
            f"  • CV velocity change: {m.cv_fill_velocity_change:.0% if m.cv_fill_velocity_change not in (None, float('inf')) else 'N/A'}\n"
            f"  • Diabetic velocity change: {m.diabetic_fill_velocity_change:.0% if m.diabetic_fill_velocity_change not in (None, float('inf')) else 'N/A'}\n"
            f"  • Last nudge: '{m.historical_nudge_type}' -> outcome: {'refill' if m.outcome_refill_completed else 'no refill'}"
        )
        return {"answer_type": "patient_detail", "patient": patient, "narrative": narrative}

    # ------------------------------------------------------------------
    # 4. Routing & formatting
    # ------------------------------------------------------------------

    def _narrate_issues(self, issues: List[DetectedIssue], severity_filter: str) -> str:
        if not issues:
            return f"No {severity_filter} issues detected."
        lines = [f"Found {len(issues)} {severity_filter} issue(s):"]
        for i in issues:
            lines.append(f"  • [{i.severity.upper()}] {i.issue_type}: {i.description}")
        return "\n".join(lines)

    def execute(self, user_query: str) -> Dict:
        # Try LLM first
        intent = self._call_llm(user_query)
        # Fall back to rules
        if intent is None:
            intent = self._rule_parse(user_query)
        # Default if nothing matched
        if intent is None:
            return {
                "answer_type": "help",
                "narrative": (
                    "I can help with:\n"
                    "  • 'Show me issues' or 'What are the critical problems?'\n"
                    "  • 'What trends do we see?' or 'Diabetic trends'\n"
                    "  • 'Find high-risk patients' or 'Who has low persistence?'\n"
                    "  • 'Breakdown by age tier' or 'Cohort stats by insurance'\n"
                    "  • 'Nudge effectiveness'\n"
                    "  • 'Patient PT-90182A'"
                ),
            }

        intent_name = intent.get("intent", "help")
        params = intent.get("params", {})

        handler: Callable = getattr(self, f"handle_{intent_name}", self.handle_help)
        return handler(params)

    def handle_help(self, params: Dict) -> Dict:
        return {
            "answer_type": "help",
            "narrative": (
                "Try asking:\n"
                "  • 'Show me all issues'\n"
                "  • 'What trends do we see?'\n"
                "  • 'Find patients with high cost burden'\n"
                "  • 'Breakdown by insurance type'\n"
                "  • 'Nudge effectiveness summary'\n"
                "  • 'Tell me about patient PT-90182A'"
            ),
        }

    def chat(self):
        print("=" * 70)
        print("  HEALTHCARE INSIGHT AGENT — Type a question, or 'exit' to quit")
        print("=" * 70)
        if self.openai_api_key:
            print("  [LLM mode: OpenAI GPT-4o-mini enabled]")
        else:
            print("  [Rule-based mode: set OPENAI_API_KEY for smarter parsing]")
        print("-" * 70)

        while True:
            try:
                query = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break
            if not query or query.lower() in ("exit", "quit", "q"):
                print("Goodbye.")
                break

            result = self.execute(query)
            print(f"\n{result['narrative']}")
            if "issues" in result:
                for i in result["issues"][:5]:
                    print(f"  [{i['severity'].upper()}] {i['issue_type']}")
                    print(f"    -> {i['description']}")
                    print(f"    -> Affected: {', '.join(i['affected_patient_ids'])}")
                    print(f"    -> Suggested interventions: {', '.join(i['recommended_intervention_categories'])}")


def main():
    agent = InsightAgent()
    agent.chat()


if __name__ == "__main__":
    main()
