"""
Identification Agent
Surfaces longitudinal prescription trends, adherence gaps, and cost burden
from patient-level pharmacy data. Outputs ranked "issues" for the Simulation Agent.
"""

import json
import statistics
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from collections import defaultdict


PATIENT_DATA = [
  {"patient_id": "PT-90182A", "age": 71, "gender": "Female", "age_tier": "Boomers", "insurance_type": "Medicare Part D", "Cardiovascular_fills_Last6M": 1, "Cardiovascular_fills_Last12M": 2, "Cardiovascular_fills_Prev12M": 3, "Cardiovascular_fills_Last36M": 4, "Diabetic_fills_Last6M": 1, "Diabetic_fills_Last12M": 2, "Diabetic_fills_Prev12M": 3, "Diabetic_fills_Last36M": 4, "formulary_tier": "Tier 3", "copay_amount": 45.00, "deductible_amount": 5000.00, "total_prescription_fills_last_12m": 6, "branded_prescription_pct": 0.85, "Cardiovascular_90_day_supply_ind": True, "Diabetic_90_day_supply_ind": True, "persistence_days": 180, "historical_nudge_type": "standard_reminder", "outcome_refill_completed": 0},
  {"patient_id": "PT-33411B", "age": 25, "gender": "Male", "age_tier": "Gen Z", "insurance_type": "Commercial PPO", "Cardiovascular_fills_Last6M": 2, "Cardiovascular_fills_Last12M": 4, "Cardiovascular_fills_Prev12M": 4, "Cardiovascular_fills_Last36M": 12, "Diabetic_fills_Last6M": 0, "Diabetic_fills_Last12M": 0, "Diabetic_fills_Prev12M": 0, "Diabetic_fills_Last36M": 0, "formulary_tier": "Tier 1", "copay_amount": 5.00, "deductible_amount": 1000.00, "total_prescription_fills_last_12m": 12, "branded_prescription_pct": 0.10, "Cardiovascular_90_day_supply_ind": False, "Diabetic_90_day_supply_ind": False, "persistence_days": 350, "historical_nudge_type": "none", "outcome_refill_completed": 1},
  {"patient_id": "PT-77290C", "age": 34, "gender": "Female", "age_tier": "Millennials", "insurance_type": "Medicaid", "Cardiovascular_fills_Last6M": 0, "Cardiovascular_fills_Last12M": 0, "Cardiovascular_fills_Prev12M": 0, "Cardiovascular_fills_Last36M": 0, "Diabetic_fills_Last6M": 1, "Diabetic_fills_Last12M": 3, "Diabetic_fills_Prev12M": 2, "Diabetic_fills_Last36M": 6, "formulary_tier": "Tier 2", "copay_amount": 15.00, "deductible_amount": 0.00, "total_prescription_fills_last_12m": 8, "branded_prescription_pct": 0.50, "Cardiovascular_90_day_supply_ind": False, "Diabetic_90_day_supply_ind": False, "persistence_days": 210, "historical_nudge_type": "loss_aversion_text", "outcome_refill_completed": 1},
  {"patient_id": "PT-10554D", "age": 23, "gender": "Female", "age_tier": "Gen Z", "insurance_type": "Commercial HDHP", "Cardiovascular_fills_Last6M": 1, "Cardiovascular_fills_Last12M": 1, "Cardiovascular_fills_Prev12M": 0, "Cardiovascular_fills_Last36M": 1, "Diabetic_fills_Last6M": 1, "Diabetic_fills_Last12M": 1, "Diabetic_fills_Prev12M": 0, "Diabetic_fills_Last36M": 1, "formulary_tier": "Tier 4", "copay_amount": 125.00, "deductible_amount": 6500.00, "total_prescription_fills_last_12m": 2, "branded_prescription_pct": 1.00, "Cardiovascular_90_day_supply_ind": False, "Diabetic_90_day_supply_ind": False, "persistence_days": 45, "historical_nudge_type": "standard_reminder", "outcome_refill_completed": 0},
  {"patient_id": "PT-88321E", "age": 68, "gender": "Male", "age_tier": "Boomers", "insurance_type": "Medicare Part D", "Cardiovascular_fills_Last6M": 2, "Cardiovascular_fills_Last12M": 4, "Cardiovascular_fills_Prev12M": 4, "Cardiovascular_fills_Last36M": 12, "Diabetic_fills_Last6M": 2, "Diabetic_fills_Last12M": 4, "Diabetic_fills_Prev12M": 4, "Diabetic_fills_Last36M": 11, "formulary_tier": "Tier 2", "copay_amount": 20.00, "deductible_amount": 400.00, "total_prescription_fills_last_12m": 10, "branded_prescription_pct": 0.25, "Cardiovascular_90_day_supply_ind": True, "Diabetic_90_day_supply_ind": True, "persistence_days": 310, "historical_nudge_type": "financial_incentive_offer", "outcome_refill_completed": 1},
  {"patient_id": "PT-49201F", "age": 49, "gender": "Male", "age_tier": "Gen X", "insurance_type": "Commercial HMO", "Cardiovascular_fills_Last6M": 0, "Cardiovascular_fills_Last12M": 0, "Cardiovascular_fills_Prev12M": 0, "Cardiovascular_fills_Last36M": 0, "Diabetic_fills_Last6M": 3, "Diabetic_fills_Last12M": 5, "Diabetic_fills_Prev12M": 6, "Diabetic_fills_Last36M": 15, "formulary_tier": "Tier 3", "copay_amount": 35.00, "deductible_amount": 1500.00, "total_prescription_fills_last_12m": 7, "branded_prescription_pct": 0.70, "Cardiovascular_90_day_supply_ind": False, "Diabetic_90_day_supply_ind": True, "persistence_days": 190, "historical_nudge_type": "peer_social_proof", "outcome_refill_completed": 0},
  {"patient_id": "PT-66192G", "age": 75, "gender": "Female", "age_tier": "Boomers", "insurance_type": "Medicare Part D", "Cardiovascular_fills_Last6M": 1, "Cardiovascular_fills_Last12M": 3, "Cardiovascular_fills_Prev12M": 4, "Cardiovascular_fills_Last36M": 10, "Diabetic_fills_Last6M": 0, "Diabetic_fills_Last12M": 0, "Diabetic_fills_Prev12M": 0, "Diabetic_fills_Last36M": 0, "formulary_tier": "Tier 1", "copay_amount": 2.50, "deductible_amount": 0.00, "total_prescription_fills_last_12m": 11, "branded_prescription_pct": 0.05, "Cardiovascular_90_day_supply_ind": False, "Diabetic_90_day_supply_ind": False, "persistence_days": 320, "historical_nudge_type": "standard_reminder", "outcome_refill_completed": 1},
  {"patient_id": "PT-22948H", "age": 39, "gender": "Male", "age_tier": "Millennials", "insurance_type": "Medicaid", "Cardiovascular_fills_Last6M": 1, "Cardiovascular_fills_Last12M": 2, "Cardiovascular_fills_Prev12M": 1, "Cardiovascular_fills_Last36M": 3, "Diabetic_fills_Last6M": 1, "Diabetic_fills_Last12M": 2, "Diabetic_fills_Prev12M": 1, "Diabetic_fills_Last36M": 2, "formulary_tier": "Tier 3", "copay_amount": 10.00, "deductible_amount": 0.00, "total_prescription_fills_last_12m": 5, "branded_prescription_pct": 0.60, "Cardiovascular_90_day_supply_ind": True, "Diabetic_90_day_supply_ind": False, "persistence_days": 150, "historical_nudge_type": "provider_escalation", "outcome_refill_completed": 1},
  {"patient_id": "PT-55034I", "age": 52, "gender": "Female", "age_tier": "Gen X", "insurance_type": "Commercial PPO", "Cardiovascular_fills_Last6M": 0, "Cardiovascular_fills_Last12M": 0, "Cardiovascular_fills_Prev12M": 0, "Cardiovascular_fills_Last36M": 0, "Diabetic_fills_Last6M": 2, "Diabetic_fills_Last12M": 4, "Diabetic_fills_Prev12M": 4, "Diabetic_fills_Last36M": 10, "formulary_tier": "Tier 5", "copay_amount": 20.00, "deductible_amount": 10000.00, "total_prescription_fills_last_12m": 5, "branded_prescription_pct": 0.60, "Cardiovascular_90_day_supply_ind": True, "Diabetic_90_day_supply_ind": False, "persistence_days": 150, "historical_nudge_type": "provider_escalation", "outcome_refill_completed": 1},
]


@dataclass
class TrendMetrics:
    patient_id: str
    # Velocity: recent 6M annualized vs prior 12M annualized
    cv_fill_velocity_change: Optional[float] = None
    diabetic_fill_velocity_change: Optional[float] = None
    diabetic_drop_flag: bool = False
    cv_drop_flag: bool = False
    # Persistence & adherence
    persistence_days: int = 0
    low_persistence_flag: bool = False
    # Cost burden
    copay_amount: float = 0.0
    deductible_amount: float = 0.0
    high_copay_flag: bool = False
    high_deductible_flag: bool = False
    branded_prescription_pct: float = 0.0
    high_branded_flag: bool = False
    # 90-day supply adoption
    cv_90day: bool = False
    diabetic_90day: bool = False
    # Historical effectiveness
    historical_nudge_type: str = "none"
    outcome_refill_completed: int = 0
    # Cohort info
    age_tier: str = ""
    insurance_type: str = ""
    formulary_tier: str = ""
    age: int = 0
    gender: str = ""
    total_fills_12m: int = 0


@dataclass
class DetectedIssue:
    issue_type: str
    severity: str  # critical, high, medium, low
    affected_patient_ids: List[str] = field(default_factory=list)
    description: str = ""
    cohort: str = ""
    metric_value: Optional[float] = None
    recommended_intervention_categories: List[str] = field(default_factory=list)


def compute_trend_metrics(patient: dict) -> TrendMetrics:
    """Derive trend metrics from raw longitudinal fields."""
    m = TrendMetrics(patient_id=patient["patient_id"])

    # --- Fill velocity analysis ---
    # Annualize: Last6M * 2 vs Prev12M (already annual)
    cv_recent = patient.get("Cardiovascular_fills_Last6M", 0) * 2
    cv_prior = patient.get("Cardiovascular_fills_Prev12M", 0)
    if cv_prior > 0:
        m.cv_fill_velocity_change = (cv_recent - cv_prior) / cv_prior
    elif cv_recent > 0 and cv_prior == 0:
        m.cv_fill_velocity_change = float("inf")
    else:
        m.cv_fill_velocity_change = 0.0

    diabetic_recent = patient.get("Diabetic_fills_Last6M", 0) * 2
    diabetic_prior = patient.get("Diabetic_fills_Prev12M", 0)
    if diabetic_prior > 0:
        m.diabetic_fill_velocity_change = (diabetic_recent - diabetic_prior) / diabetic_prior
    elif diabetic_recent > 0 and diabetic_prior == 0:
        m.diabetic_fill_velocity_change = float("inf")
    else:
        m.diabetic_fill_velocity_change = 0.0

    # Drop flag: >20% decline or complete cessation from positive prior
    m.cv_drop_flag = (m.cv_fill_velocity_change is not None and m.cv_fill_velocity_change < -0.20) or \
                     (cv_prior > 0 and cv_recent == 0)
    m.diabetic_drop_flag = (m.diabetic_fill_velocity_change is not None and m.diabetic_fill_velocity_change < -0.20) or \
                           (diabetic_prior > 0 and diabetic_recent == 0)

    # --- Persistence ---
    m.persistence_days = patient.get("persistence_days", 0)
    m.low_persistence_flag = m.persistence_days < 90  # threshold

    # --- Cost burden ---
    m.copay_amount = patient.get("copay_amount", 0.0)
    m.deductible_amount = patient.get("deductible_amount", 0.0)
    m.high_copay_flag = m.copay_amount >= 35.0
    m.high_deductible_flag = m.deductible_amount >= 5000.0

    # --- Branded drug burden ---
    m.branded_prescription_pct = patient.get("branded_prescription_pct", 0.0)
    m.high_branded_flag = m.branded_prescription_pct >= 0.60

    # --- 90-day supply ---
    m.cv_90day = patient.get("Cardiovascular_90_day_supply_ind", False)
    m.diabetic_90day = patient.get("Diabetic_90_day_supply_ind", False)

    # --- Historical nudge outcome ---
    m.historical_nudge_type = patient.get("historical_nudge_type", "none")
    m.outcome_refill_completed = patient.get("outcome_refill_completed", 0)

    # --- Cohort info ---
    m.age_tier = patient.get("age_tier", "")
    m.insurance_type = patient.get("insurance_type", "")
    m.formulary_tier = patient.get("formulary_tier", "")
    m.age = patient.get("age", 0)
    m.gender = patient.get("gender", "")
    m.total_fills_12m = patient.get("total_prescription_fills_last_12m", 0)

    return m


def detect_issues(patients: List[dict]) -> List[DetectedIssue]:
    """Aggregate patient-level trends into population-level issues."""
    metrics = [compute_trend_metrics(p) for p in patients]
    issues: List[DetectedIssue] = []

    # 1. Diabetic fill decline
    diabetic_decliners = [m for m in metrics if m.diabetic_drop_flag]
    if diabetic_decliners:
        severity = "critical" if len(diabetic_decliners) >= 2 else "high"
        issues.append(DetectedIssue(
            issue_type="diabetic_fill_decline",
            severity=severity,
            affected_patient_ids=[m.patient_id for m in diabetic_decliners],
            description=f"{len(diabetic_decliners)} patients show declining or ceased diabetic prescription fills (6M annualized vs prior 12M).",
            cohort=",".join(sorted(set(m.age_tier for m in diabetic_decliners))),
            metric_value=round(statistics.mean([m.diabetic_fill_velocity_change for m in diabetic_decliners if m.diabetic_fill_velocity_change is not None and m.diabetic_fill_velocity_change != float("inf")]), 2) if any(m.diabetic_fill_velocity_change not in (None, float("inf")) for m in diabetic_decliners) else None,
            recommended_intervention_categories=["financial_incentive_offer", "90_day_supply_conversion", "provider_escalation", "loss_aversion_text"]
        ))

    # 2. Cardiovascular fill decline
    cv_decliners = [m for m in metrics if m.cv_drop_flag]
    if cv_decliners:
        severity = "critical" if len(cv_decliners) >= 2 else "high"
        issues.append(DetectedIssue(
            issue_type="cardiovascular_fill_decline",
            severity=severity,
            affected_patient_ids=[m.patient_id for m in cv_decliners],
            description=f"{len(cv_decliners)} patients show declining or ceased cardiovascular prescription fills.",
            cohort=",".join(sorted(set(m.age_tier for m in cv_decliners))),
            metric_value=round(statistics.mean([m.cv_fill_velocity_change for m in cv_decliners if m.cv_fill_velocity_change is not None and m.cv_fill_velocity_change != float("inf")]), 2) if any(m.cv_fill_velocity_change not in (None, float("inf")) for m in cv_decliners) else None,
            recommended_intervention_categories=["standard_reminder", "90_day_supply_conversion", "provider_escalation"]
        ))

    # 3. Low persistence
    low_persist = [m for m in metrics if m.low_persistence_flag]
    if low_persist:
        issues.append(DetectedIssue(
            issue_type="low_persistence",
            severity="high",
            affected_patient_ids=[m.patient_id for m in low_persist],
            description=f"{len(low_persist)} patients have <90 days persistence (median: {statistics.median([m.persistence_days for m in low_persist]):.0f} days).",
            cohort="all_tiers",
            metric_value=round(statistics.mean([m.persistence_days for m in low_persist]), 1),
            recommended_intervention_categories=["standard_reminder", "loss_aversion_text", "provider_escalation", "90_day_supply_conversion"]
        ))

    # 4. High cost burden (copay + deductible)
    high_cost = [m for m in metrics if m.high_copay_flag or m.high_deductible_flag]
    if high_cost:
        issues.append(DetectedIssue(
            issue_type="high_cost_burden",
            severity="high",
            affected_patient_ids=[m.patient_id for m in high_cost],
            description=f"{len(high_cost)} patients face high cost barriers (copay >=$35 or deductible >=$5,000).",
            cohort=",".join(sorted(set(m.insurance_type for m in high_cost))),
            metric_value=round(statistics.mean([m.copay_amount for m in high_cost]), 2),
            recommended_intervention_categories=["financial_incentive_offer", "generic_switch_education", "copay_coupon_program"]
        ))

    # 5. High branded drug utilization
    high_branded = [m for m in metrics if m.high_branded_flag]
    if high_branded:
        issues.append(DetectedIssue(
            issue_type="high_branded_utilization",
            severity="medium",
            affected_patient_ids=[m.patient_id for m in high_branded],
            description=f"{len(high_branded)} patients have >=60% branded prescriptions, suggesting cost optimization potential.",
            cohort="all_tiers",
            metric_value=round(statistics.mean([m.branded_prescription_pct for m in high_branded]), 2),
            recommended_intervention_categories=["generic_switch_education", "financial_incentive_offer", "copay_coupon_program"]
        ))

    # 6. Low 90-day supply adoption (for chronic conditions with fills)
    chronic_no_90day = [m for m in metrics if (m.total_fills_12m > 0) and (not m.cv_90day) and (not m.diabetic_90day)]
    if chronic_no_90day:
        issues.append(DetectedIssue(
            issue_type="low_90day_supply_adoption",
            severity="medium",
            affected_patient_ids=[m.patient_id for m in chronic_no_90day],
            description=f"{len(chronic_no_90day)} patients with active fills are not enrolled in 90-day supply.",
            cohort="all_tiers",
            metric_value=None,
            recommended_intervention_categories=["90_day_supply_conversion", "standard_reminder", "financial_incentive_offer"]
        ))

    # 7. Nudge efficacy cohort analysis
    nudge_effectiveness = defaultdict(lambda: {"success": 0, "total": 0})
    for m in metrics:
        if m.historical_nudge_type != "none":
            nudge_effectiveness[m.historical_nudge_type]["total"] += 1
            nudge_effectiveness[m.historical_nudge_type]["success"] += m.outcome_refill_completed

    for nudge_type, stats in nudge_effectiveness.items():
        if stats["total"] > 0:
            rate = stats["success"] / stats["total"]
            if rate < 0.5:
                affected = [m.patient_id for m in metrics if m.historical_nudge_type == nudge_type]
                issues.append(DetectedIssue(
                    issue_type="underperforming_nudge",
                    severity="medium",
                    affected_patient_ids=affected,
                    description=f"Nudge type '{nudge_type}' has {rate:.0%} success rate across {stats['total']} patients.",
                    cohort="all_tiers",
                    metric_value=round(rate, 2),
                    recommended_intervention_categories=["alternative_nudge_test"]
                ))

    # Sort: critical > high > medium > low
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    issues.sort(key=lambda x: severity_order[x.severity])
    return issues


@dataclass
class IdentificationReport:
    """Structured output from the Identification Agent for the Simulation Agent."""
    patient_count: int
    issues: List[DetectedIssue]
    patient_metrics: List[TrendMetrics]  # full patient-level metrics for matching

    def to_dict(self) -> Dict:
        return {
            "agent": "identification",
            "patient_count": self.patient_count,
            "issues": [asdict(i) for i in self.issues],
        }

    def get_issue_by_type(self, issue_type: str) -> Optional[DetectedIssue]:
        for issue in self.issues:
            if issue.issue_type == issue_type:
                return issue
        return None

    def get_critical_issues(self) -> List[DetectedIssue]:
        return [i for i in self.issues if i.severity == "critical"]


def run_identification(patients: Optional[List[dict]] = None) -> IdentificationReport:
    """Run identification and return a structured report for downstream simulation."""
    data = patients if patients is not None else PATIENT_DATA
    metrics = [compute_trend_metrics(p) for p in data]
    issues = detect_issues(data)
    return IdentificationReport(
        patient_count=len(data),
        issues=issues,
        patient_metrics=metrics,
    )


def main():
    print("=" * 70)
    print("IDENTIFICATION AGENT — Consumer Health Personalization Loop")
    print("=" * 70)

    report = run_identification()
    issues = report.issues

    print(f"\nTotal patients analyzed: {report.patient_count}")
    print(f"Issues detected: {len(issues)}")
    print("-" * 70)

    for i, issue in enumerate(issues, 1):
        print(f"\n{i}. [{issue.severity.upper()}] {issue.issue_type}")
        print(f"   Description: {issue.description}")
        if issue.metric_value is not None:
            print(f"   Key Metric: {issue.metric_value}")
        print(f"   Affected patients ({len(issue.affected_patient_ids)}): {', '.join(issue.affected_patient_ids)}")
        print(f"   Cohorts: {issue.cohort}")
        print(f"   Suggested simulation levers: {', '.join(issue.recommended_intervention_categories)}")

    print("\n" + "=" * 70)
    print("OUTPUT: Pass this issue list to the Simulation Agent.")
    print("=" * 70)

    # Emit JSON for programmatic handoff
    print(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    main()
