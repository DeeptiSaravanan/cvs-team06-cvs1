"""
A/B Test Simulation Tools for Aura Simulator.

Provides deterministic simulation of A/B experiments including:
- Audience segmentation
- Holdout group sizing
- Content matching and scoring
- Statistical significance calculation
- Best-combination recommendation
"""

import csv
import datetime
import hashlib
import json
import math
import os
import random
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Resolve the project data/ folder relative to this file:
# app/tools/simulation_tools.py → app/tools/ → app/ → project_root/ → data/
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class AudienceSegment:
    name: str
    size: int
    characteristics: dict[str, Any]


@dataclass
class ContentVariant:
    id: str
    title: str
    content_type: str
    tags: list[str]
    target_characteristics: dict[str, Any]
    estimated_relevance: float = 0.0


@dataclass
class ExperimentResult:
    variant_id: str
    holdout_pct: float
    audience_segment: str
    control_conversion: float
    treatment_conversion: float
    lift_pct: float
    confidence_pct: float
    sample_size: int
    matched_content: list[str]
    score: float


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def load_experiment_data() -> dict:
    """Load target audience and content repository from the project data/ folder.

    Reads two JSON files:
      - data/audience.json   — audience description + optional patient records.
                               Supported formats:
                               1. Simple:  {"description": "...", "features": {...}}
                               2. Patient-level: {"description": "...", "features": {...},
                                                  "patients": [{age_tier,
                                                  outcome_refill_completed, ...}]}
      - data/content_repo.json — list of content items to test.

    When a 'patients' array is present, segments are derived directly from the data:
      - Grouped by age_tier
      - conversion_baseline = mean(outcome_refill_completed) per tier
      - engagement_propensity = normalised mean(persistence_days / 365)
      - Each sample patient is scaled to 10,000 real patients for simulation sizing

    Returns:
        A dict with audience metadata, content_items, and optionally patient_segments.
    """
    audience_path = _DATA_DIR / "audience.json"
    content_path = _DATA_DIR / "content_repo.csv"

    errors: list[str] = []

    # Load audience (JSON)
    audience_data: Any = {}
    if not audience_path.exists():
        errors.append(
            f"audience.json not found. Expected at: {audience_path}. "
            "Please upload the file to the data/ folder."
        )
    else:
        try:
            audience_data = json.loads(audience_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"audience.json is invalid JSON: {e}")

    # Load content repo (CSV)
    # Supports two column formats:
    #   1. Single-column:  email_message         (new format — raw message text)
    #   2. Multi-column:   title, type, description, tags  (legacy format)
    content_items: list[dict] = []
    if not content_path.exists():
        errors.append(
            f"content_repo.csv not found. Expected at: {content_path}. "
            "Please upload the file to the data/ folder."
        )
    else:
        try:
            reader = csv.DictReader(content_path.open(encoding="utf-8"))
            fieldnames = reader.fieldnames or []
            is_email_message_format = (
                len(fieldnames) == 1 and fieldnames[0].strip() == "email_message"
            )
            for idx, row in enumerate(reader, start=1):
                if is_email_message_format:
                    # Single-column format: derive metadata from message text
                    message = row.get("email_message", "").strip().strip('"')
                    msg_lower = message.lower()
                    # Auto-derive a short title from the first sentence / ~60 chars
                    title = message[:60].rstrip(" ,.!") + ("…" if len(message) > 60 else "")
                    # Extract keyword-based tags for relevance scoring
                    tags: list[str] = ["email"]
                    for kw in ["refill", "medication", "pharmacy", "prescription",
                               "diabetes", "cardiovascular", "reminder", "90-day",
                               "discount", "offer", "app", "mobile"]:
                        if kw in msg_lower:
                            tags.append(kw)
                    content_items.append({
                        "id": f"msg_{idx:03d}",
                        "title": title,
                        "type": "email",
                        "description": message,
                        "tags": tags,
                        "raw_message": message,
                    })
                else:
                    # Legacy multi-column format
                    tags_raw = row.get("tags", "")
                    content_items.append({
                        "title": row.get("title", "").strip(),
                        "type": row.get("type", "").strip(),
                        "description": row.get("description", "").strip(),
                        "tags": [t.strip() for t in tags_raw.split("|") if t.strip()],
                    })
        except Exception as e:
            errors.append(f"content_repo.csv could not be read: {e}")


    if errors:
        return {"error": " | ".join(errors)}

    if not content_items:
        return {"error": "content_repo.csv is empty or has no data rows."}

    if "description" not in audience_data:
        return {
            "error": (
                "audience.json must contain a top-level 'description' string. "
                "Supported formats: {description, features} "
                "or {description, features, patients: [...]}."
            )
        }

    description: str = audience_data["description"]
    patient_segments: list[dict] = []
    total_audience_size: int = 0

    # ------------------------------------------------------------------
    # Patient-level format: derive segments from the patients array
    # ------------------------------------------------------------------
    if "patients" in audience_data and isinstance(audience_data["patients"], list):
        patients: list[dict] = audience_data["patients"]

        # Group patients by age_tier
        tiers: dict[str, list[dict]] = {}
        for p in patients:
            tier = p.get("age_tier", "Unknown")
            tiers.setdefault(tier, []).append(p)

        # Scale: each sample patient represents 10,000 real patients
        SCALE = 10_000
        for tier_name, tier_patients in tiers.items():
            n = len(tier_patients)
            conversion = (
                sum(p.get("outcome_refill_completed", 0) for p in tier_patients) / n
            )
            avg_age = sum(p.get("age", 0) for p in tier_patients) / n
            avg_copay = sum(p.get("copay_amount", 0) for p in tier_patients) / n
            avg_persistence = sum(p.get("persistence_days", 0) for p in tier_patients) / n
            engagement_propensity = round(min(avg_persistence / 365.0, 1.0), 3)
            insurance_types = list({p.get("insurance_type", "") for p in tier_patients})
            formulary_tiers_list = list({p.get("formulary_tier", "") for p in tier_patients})
            nudge_types = list({p.get("historical_nudge_type", "") for p in tier_patients})
            disease_areas = []
            if any(p.get("Cardiovascular_fills_Last12M", 0) > 0 for p in tier_patients):
                disease_areas.append("Cardiovascular")
            if any(p.get("Diabetic_fills_Last12M", 0) > 0 for p in tier_patients):
                disease_areas.append("Diabetic")

            seg_size = n * SCALE
            total_audience_size += seg_size
            patient_segments.append({
                "segment_name": tier_name,
                "size": seg_size,
                "patients_in_sample": n,
                "avg_age": round(avg_age, 1),
                "conversion_baseline": round(conversion, 4),
                "engagement_propensity": engagement_propensity,
                "avg_copay_usd": round(avg_copay, 2),
                "avg_persistence_days": round(avg_persistence, 1),
                "insurance_types": insurance_types,
                "formulary_tiers": formulary_tiers_list,
                "historical_nudge_types": nudge_types,
                "disease_areas": disease_areas,
            })

        # Sort largest first
        patient_segments.sort(key=lambda s: s["size"], reverse=True)

    result: dict = {
        "audience_description": description,
        "audience_features": audience_data.get("features", {}),
        "content_items": content_items,
        "audience_file": str(audience_path),
        "content_file": str(content_path),
    }

    if patient_segments:
        result["patient_segments"] = patient_segments
        result["total_audience_size"] = total_audience_size
        result["status"] = (
            f"Loaded {len(patients)} patient records across "
            f"{len(patient_segments)} age-tier segments "
            f"(total scaled audience: {total_audience_size:,}) and "
            f"{len(content_items)} content items from data/."
        )
    else:
        result["status"] = (
            f"Loaded audience '{description}' and "
            f"{len(content_items)} content items from data/."
        )

    return result


def _compute_segments(patients: list[dict]) -> tuple[list[dict], int]:
    """Compute patient segments grouped by age_tier from a list of patient dicts.

    Each sample patient is scaled to 10,000 real patients.

    Returns:
        (patient_segments, total_audience_size)
    """
    SCALE = 10_000
    tiers: dict[str, list[dict]] = {}
    for p in patients:
        tier = p.get("age_tier", "Unknown")
        tiers.setdefault(tier, []).append(p)

    segments: list[dict] = []
    total = 0
    for tier_name, tier_patients in tiers.items():
        n = len(tier_patients)
        conversion = sum(p.get("outcome_refill_completed", 0) for p in tier_patients) / n
        avg_age = sum(p.get("age", 0) for p in tier_patients) / n
        avg_copay = sum(p.get("copay_amount", 0) for p in tier_patients) / n
        avg_persistence = sum(p.get("persistence_days", 0) for p in tier_patients) / n
        engagement_propensity = round(min(avg_persistence / 365.0, 1.0), 3)
        insurance_types = list({p.get("insurance_type", "") for p in tier_patients})
        formulary_tiers_list = list({p.get("formulary_tier", "") for p in tier_patients})
        nudge_types = list({p.get("historical_nudge_type", "") for p in tier_patients})
        disease_areas = []
        if any(p.get("Cardiovascular_fills_Last12M", 0) > 0 for p in tier_patients):
            disease_areas.append("Cardiovascular")
        if any(p.get("Diabetic_fills_Last12M", 0) > 0 for p in tier_patients):
            disease_areas.append("Diabetic")

        seg_size = n * SCALE
        total += seg_size
        segments.append({
            "segment_name": tier_name,
            "size": seg_size,
            "patients_in_sample": n,
            "avg_age": round(avg_age, 1),
            "conversion_baseline": round(conversion, 4),
            "engagement_propensity": engagement_propensity,
            "avg_copay_usd": round(avg_copay, 2),
            "avg_persistence_days": round(avg_persistence, 1),
            "insurance_types": insurance_types,
            "formulary_tiers": formulary_tiers_list,
            "historical_nudge_types": nudge_types,
            "disease_areas": disease_areas,
        })

    segments.sort(key=lambda s: s["size"], reverse=True)
    return segments, total


def filter_patients_by_usecase(use_case: str) -> dict:
    """Load audience and content data, filtering patients based on disease area keywords.

    Disease area detection rules (applied to the use_case string):
      - Contains 'diabetes' or 'diabetic'      → keep only patients with Diabetic_fills_Last12M > 0
      - Contains 'cardiovascular', 'cardiac',
        or 'heart'                              → keep only patients with Cardiovascular_fills_Last12M > 0
      - Contains both sets of keywords          → keep patients with EITHER condition
      - Contains neither                        → return ALL patients (no filter applied)

    Also loads content_repo.csv (unfiltered — all content stays available).

    Args:
        use_case: The experiment goal as described by the user.

    Returns:
        Same structure as load_experiment_data() plus:
          - detected_disease_areas: list of disease areas found in use_case
          - filter_applied: True if any filtering was done
          - total_patients_before_filter: count before filtering
          - total_patients_after_filter: count after filtering
    """
    audience_path = _DATA_DIR / "audience.json"
    content_path = _DATA_DIR / "content_repo.csv"

    # --- Load audience ---
    if not audience_path.exists():
        return {"error": f"audience.json not found at {audience_path}."}
    try:
        audience_data = json.loads(audience_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"error": f"audience.json is invalid JSON: {e}"}

    if "description" not in audience_data:
        return {"error": "audience.json must have a top-level 'description' field."}

    all_patients: list[dict] = audience_data.get("patients", [])
    if not all_patients:
        return {"error": "No 'patients' array found in audience.json."}

    # --- Detect disease areas from use_case ---
    uc = use_case.lower()
    want_diabetic = any(kw in uc for kw in ["diabetes", "diabetic"])
    want_cardiovascular = any(kw in uc for kw in ["cardiovascular", "cardiac", "heart"])

    detected_disease_areas: list[str] = []
    if want_diabetic:
        detected_disease_areas.append("Diabetic")
    if want_cardiovascular:
        detected_disease_areas.append("Cardiovascular")

    # --- Filter patients ---
    if want_diabetic and want_cardiovascular:
        filtered = [
            p for p in all_patients
            if p.get("Diabetic_fills_Last12M", 0) > 0
            or p.get("Cardiovascular_fills_Last12M", 0) > 0
        ]
        filter_reason = "Diabetic OR Cardiovascular patients"
    elif want_diabetic:
        filtered = [p for p in all_patients if p.get("Diabetic_fills_Last12M", 0) > 0]
        filter_reason = "Diabetic patients only"
    elif want_cardiovascular:
        filtered = [p for p in all_patients if p.get("Cardiovascular_fills_Last12M", 0) > 0]
        filter_reason = "Cardiovascular patients only"
    else:
        filtered = all_patients
        filter_reason = "All patients (no disease-area filter)"

    if not filtered:
        return {
            "error": (
                f"No patients matched the filter '{filter_reason}'. "
                "Try a broader use case or check your audience data."
            )
        }

    # --- Load content ---
    content_items: list[dict] = []
    if not content_path.exists():
        return {"error": f"content_repo.csv not found at {content_path}."}
    try:
        reader = csv.DictReader(content_path.open(encoding="utf-8"))
        fieldnames = reader.fieldnames or []
        is_email_format = len(fieldnames) == 1 and fieldnames[0].strip() == "email_message"
        for idx, row in enumerate(reader, start=1):
            if is_email_format:
                message = row.get("email_message", "").strip().strip('"')
                msg_lower = message.lower()
                title = message[:60].rstrip(" ,.!") + ("…" if len(message) > 60 else "")
                tags: list[str] = ["email"]
                for kw in ["refill", "medication", "pharmacy", "prescription",
                            "diabetes", "cardiovascular", "reminder", "90-day",
                            "discount", "offer", "app", "mobile"]:
                    if kw in msg_lower:
                        tags.append(kw)
                content_items.append({
                    "id": f"msg_{idx:03d}",
                    "title": title,
                    "type": "email",
                    "description": message,
                    "tags": tags,
                    "raw_message": message,
                })
            else:
                tags_raw = row.get("tags", "")
                content_items.append({
                    "title": row.get("title", "").strip(),
                    "type": row.get("type", "").strip(),
                    "description": row.get("description", "").strip(),
                    "tags": [t.strip() for t in tags_raw.split("|") if t.strip()],
                })
    except Exception as e:
        return {"error": f"content_repo.csv could not be read: {e}"}

    # --- Compute segments from filtered patients ---
    patient_segments, total_audience_size = _compute_segments(filtered)

    filter_applied = len(filtered) < len(all_patients)
    return {
        "audience_description": audience_data["description"],
        "audience_features": audience_data.get("features", {}),
        "patient_segments": patient_segments,
        "total_audience_size": total_audience_size,
        "content_items": content_items,
        "detected_disease_areas": detected_disease_areas,
        "filter_applied": filter_applied,
        "filter_reason": filter_reason,
        "total_patients_before_filter": len(all_patients),
        "total_patients_after_filter": len(filtered),
        "audience_file": str(audience_path),
        "content_file": str(content_path),
        "status": (
            f"Filter: '{filter_reason}'. "
            f"Patients: {len(filtered)}/{len(all_patients)} retained "
            f"→ {len(patient_segments)} age-tier segments "
            f"(scaled audience: {total_audience_size:,}). "
            f"{len(content_items)} content items loaded."
        ),
    }


def analyze_target_audience(
    audience_description: str,
    use_case: str,
) -> dict:
    """Analyze and segment a target audience based on description and use case.

    Args:
        audience_description: Free-text description of the target audience
                              (e.g. "millennial urban professionals aged 25-35").
        use_case: The business use case for the A/B test
                 (e.g. "increase newsletter sign-up rate").

    Returns:
        A dict with audience segments, size estimates, and key characteristics.
    """
    seed = int(hashlib.md5(f"{audience_description}{use_case}".encode()).hexdigest(), 16) % (10**8)
    rng = random.Random(seed)

    # Derive segments from the description keywords
    keywords = audience_description.lower().split()
    segments: list[dict] = []

    age_ranges = {
        "young": ("18-24", 0.18),
        "millennial": ("25-34", 0.22),
        "gen-z": ("18-26", 0.20),
        "professional": ("28-45", 0.25),
        "senior": ("45-65", 0.15),
        "boomer": ("55-70", 0.12),
    }
    income_ranges = {
        "high-income": "high",
        "affluent": "high",
        "budget": "low",
        "student": "low",
        "executive": "high",
        "urban": "medium-high",
        "suburban": "medium",
        "rural": "low-medium",
    }

    detected_age = ("25-44", 0.25)  # default
    for kw, val in age_ranges.items():
        if kw in keywords:
            detected_age = val
            break

    detected_income = "medium"
    for kw, val in income_ranges.items():
        if kw in keywords:
            detected_income = val
            break

    base_size = rng.randint(50_000, 500_000)
    segment_splits = [0.45, 0.30, 0.25]
    segment_names = ["Core", "Adjacent", "Fringe"]

    for i, (split, name) in enumerate(zip(segment_splits, segment_names)):
        seg_size = int(base_size * split)
        segments.append({
            "segment_name": f"{name} Audience",
            "description": f"{name.lower()} users matching '{audience_description}'",
            "size": seg_size,
            "age_range": detected_age[0],
            "income_level": detected_income,
            "engagement_propensity": round(rng.uniform(0.4 - i * 0.1, 0.9 - i * 0.15), 3),
            "conversion_baseline": round(rng.uniform(0.02 - i * 0.005, 0.12 - i * 0.02), 4),
        })

    return {
        "total_audience_size": base_size,
        "use_case": use_case,
        "segments": segments,
        "audience_summary": f"Audience '{audience_description}' segmented into {len(segments)} groups "
                            f"totaling {base_size:,} users. Core segment is largest at {segments[0]['size']:,}.",
    }


def index_content_repository(
    content_items: list,
    use_case: str,
) -> dict:
    """Index and score a content repository for relevance to the use case.

    Args:
        content_items: List of content items. Each item can be either:
                       - a plain string (e.g. "Homepage hero banner"), or
                       - a dict with keys 'title', 'type', 'description', 'tags'
                         (as loaded from content_repo.json).
        use_case: The A/B test use case to score content relevance against.

    Returns:
        A dict of scored and ranked content variants ready for experimentation.
    """
    # Extract titles for stable seed (works for both str and dict items)
    titles = [item["title"] if isinstance(item, dict) else item for item in content_items]
    seed = int(hashlib.md5(f"{','.join(titles)}{use_case}".encode()).hexdigest(), 16) % (10**8)
    rng = random.Random(seed)

    use_case_lower = use_case.lower()

    # Simple keyword relevance heuristic
    relevance_keywords = {
        "sign-up": ["welcome", "onboard", "register", "join", "hero", "email"],
        "purchase": ["promo", "offer", "discount", "product", "cart", "checkout"],
        "engagement": ["newsletter", "content", "article", "blog", "social"],
        "retention": ["loyalty", "reward", "re-engage", "reminder", "retention"],
        "awareness": ["brand", "hero", "banner", "ad", "campaign"],
    }

    matched_keywords: list[str] = []
    for kw, words in relevance_keywords.items():
        if kw in use_case_lower:
            matched_keywords.extend(words)

    variants: list[dict] = []
    for idx, item in enumerate(content_items):
        # Support both plain strings and rich dicts from content_repo.json
        if isinstance(item, dict):
            title = item.get("title", f"item_{idx+1}")
            existing_tags = item.get("tags", [])
            description = item.get("description", "")
            content_type = item.get("type", "")
            searchable = f"{title} {description} {' '.join(existing_tags)}".lower()
        else:
            title = item
            existing_tags = []
            description = ""
            content_type = ""
            searchable = title.lower()

        relevance = rng.uniform(0.3, 0.6)
        for kw in matched_keywords:
            if kw in searchable:
                relevance += 0.15
        relevance = min(round(relevance, 3), 1.0)

        # Derive tags from searchable text if not already provided
        tags = list(existing_tags) if existing_tags else []
        if not tags:
            for tag in ["email", "banner", "popup", "hero", "social", "video", "in-app", "push"]:
                if tag in searchable:
                    tags.append(tag)
        if not tags:
            tags = [rng.choice(["banner", "email", "in-app"])]

        resolved_type = content_type or tags[0]

        variants.append({
            "id": f"content_{idx+1:03d}",
            "title": title,
            "description": description,
            "content_type": resolved_type,
            "tags": tags,
            "relevance_score": relevance,
            "estimated_ctr": round(rng.uniform(0.02, 0.15) * relevance, 4),
            "personalization_potential": round(rng.uniform(0.5, 1.0) * relevance, 3),
        })

    # Sort by relevance
    variants.sort(key=lambda x: x["relevance_score"], reverse=True)

    return {
        "total_content_items": len(variants),
        "use_case": use_case,
        "variants": variants,
        "top_3_recommended": [v["title"] for v in variants[:3]],
        "content_summary": f"Indexed {len(variants)} content items. Top pick: '{variants[0]['title']}' "
                           f"with relevance score {variants[0]['relevance_score']}.",
    }


def run_ab_test_simulation(
    audience_segment_name: str,
    audience_size: int,
    baseline_conversion: float,
    content_variant_id: str,
    content_relevance_score: float,
    holdout_pct: float,
    use_case: str,
) -> dict:
    """Run a Monte Carlo A/B test simulation for a specific variant and holdout %.

    Args:
        audience_segment_name: Name of the audience segment being tested.
        audience_size: Total size of the audience segment.
        baseline_conversion: Control group baseline conversion rate (e.g. 0.05 = 5%).
        content_variant_id: The content variant ID being tested.
        content_relevance_score: Relevance score of content to use case (0–1).
        holdout_pct: Fraction of audience to hold out as control (e.g. 0.2 = 20%).
        use_case: The A/B test use case.

    Returns:
        Simulation result with lift, confidence interval, and recommendation score.
    """
    seed = int(hashlib.md5(
        f"{audience_segment_name}{content_variant_id}{holdout_pct}{use_case}".encode()
    ).hexdigest(), 16) % (10**8)
    rng = random.Random(seed)

    holdout_size = int(audience_size * holdout_pct)
    treatment_size = audience_size - holdout_size

    if holdout_size < 100 or treatment_size < 100:
        return {
            "error": "Holdout or treatment group too small for valid simulation (<100 users). "
                     "Increase audience size or adjust holdout %.",
            "variant_id": content_variant_id,
            "holdout_pct": holdout_pct,
        }

    # Simulate conversions (binomial sampling approximation)
    treatment_boost = content_relevance_score * rng.uniform(0.05, 0.35)
    treatment_conversion = min(baseline_conversion * (1 + treatment_boost), 1.0)

    control_conversions: list[int] = []
    treatment_conversions: list[int] = []
    n_trials = 30

    for _ in range(n_trials):
        ctrl = sum(rng.random() < baseline_conversion for _ in range(min(holdout_size, 5000)))
        trt = sum(rng.random() < treatment_conversion for _ in range(min(treatment_size, 5000)))
        control_conversions.append(ctrl / min(holdout_size, 5000))
        treatment_conversions.append(trt / min(treatment_size, 5000))

    ctrl_mean = statistics.mean(control_conversions)
    trt_mean = statistics.mean(treatment_conversions)
    ctrl_std = statistics.stdev(control_conversions)
    trt_std = statistics.stdev(treatment_conversions)

    lift = (trt_mean - ctrl_mean) / ctrl_mean if ctrl_mean > 0 else 0.0

    # Welch's t-test approximation → p-value → confidence
    pooled_se = math.sqrt((ctrl_std**2 / n_trials) + (trt_std**2 / n_trials))
    t_stat = abs(trt_mean - ctrl_mean) / pooled_se if pooled_se > 0 else 0
    # Approximate confidence from t-stat (degrees of freedom ~29)
    confidence = min(0.9999, 1 - (1 / (1 + 0.07 * t_stat**2)))

    # Composite score: lift × confidence × size_adequacy
    size_adequacy = min(1.0, min(holdout_size, treatment_size) / 10_000)
    score = round(lift * confidence * size_adequacy * 100, 4) if lift > 0 else 0.0

    return {
        "variant_id": content_variant_id,
        "holdout_pct": holdout_pct,
        "audience_segment": audience_segment_name,
        "holdout_size": holdout_size,
        "treatment_size": treatment_size,
        "control_conversion_rate": round(ctrl_mean, 5),
        "treatment_conversion_rate": round(trt_mean, 5),
        "lift_pct": round(lift * 100, 3),
        "confidence_pct": round(confidence * 100, 2),
        "simulation_score": score,
        "is_significant": confidence >= 0.95,
        "recommendation": (
            "Strong positive result — recommend deploying this variant."
            if lift > 0.10 and confidence >= 0.95
            else "Moderate result — consider further testing."
            if lift > 0 and confidence >= 0.80
            else "Weak or negative result — do not deploy."
        ),
    }


def find_best_ab_combination(
    simulation_results: list[dict],
    top_n: int = 3,
) -> dict:
    """Rank all simulation results and return the best A/B test combination.

    Args:
        simulation_results: List of result dicts from run_ab_test_simulation.
        top_n: Number of top combinations to return.

    Returns:
        Best combination with holdout %, matched content, lift, and confidence.
    """
    valid = [r for r in simulation_results if "error" not in r and r.get("simulation_score", 0) > 0]

    if not valid:
        return {
            "error": "No valid simulation results to rank. Try with a larger audience or more content variants.",
            "total_simulated": len(simulation_results),
        }

    ranked = sorted(valid, key=lambda x: x["simulation_score"], reverse=True)
    top = ranked[:top_n]

    best = top[0]
    summary_lines = []
    for i, r in enumerate(top):
        summary_lines.append(
            f"  #{i+1} | Variant {r['variant_id']} | Holdout {int(r['holdout_pct']*100)}% | "
            f"Lift {r['lift_pct']:+.1f}% | Confidence {r['confidence_pct']:.1f}% | "
            f"Score {r['simulation_score']:.3f}"
        )

    return {
        "best_variant_id": best["variant_id"],
        "best_holdout_pct": best["holdout_pct"],
        "best_holdout_pct_display": f"{int(best['holdout_pct'] * 100)}%",
        "best_audience_segment": best["audience_segment"],
        "best_lift_pct": best["lift_pct"],
        "best_confidence_pct": best["confidence_pct"],
        "best_control_rate": best["control_conversion_rate"],
        "best_treatment_rate": best["treatment_conversion_rate"],
        "is_statistically_significant": best["is_significant"],
        "recommendation": best["recommendation"],
        "top_combinations_ranked": top,
        "leaderboard": "\n".join(summary_lines),
        "total_simulated": len(simulation_results),
        "summary": (
            f"Best combination: Content variant '{best['variant_id']}' with {int(best['holdout_pct']*100)}% holdout "
            f"on '{best['audience_segment']}'. Expected lift: {best['lift_pct']:+.1f}% "
            f"at {best['confidence_pct']:.1f}% confidence."
        ),
    }


def save_results_csv(
    best_variant_id: str,
    winning_message: str,
    holdout_pct: float = 0.20,
) -> dict:
    """Save A/B test results to a CSV with one row per patient.

    Reads patient records from data/audience.json and writes:
      output/ab_test_results.csv

    Columns:
      - patient_id    : unique patient identifier
      - group         : 'control' (holdout — receives no message)
                        or 'test'  (treatment — receives the winning message)
      - best_content  : winning email message text (empty for control patients)
      - email         : patient email address

    Group assignment is deterministic: each patient's ID is hashed so the
    same patient always lands in the same group across runs.

    Args:
        best_variant_id: The variant ID that won (e.g. 'content_001').
        winning_message: Full text of the winning email message.
        holdout_pct:    Fraction of patients to assign to 'control' (e.g. 0.30 = 30%).

    Returns:
        A dict with the output file path, row/group counts, or an error message.
    """
    audience_path = _DATA_DIR / "audience.json"
    output_dir = _DATA_DIR.parent / "output"
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"ab_test_results_{timestamp}.csv"

    # Load patients
    if not audience_path.exists():
        return {"error": f"audience.json not found at {audience_path}."}
    try:
        audience_data = json.loads(audience_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"error": f"audience.json is invalid JSON: {e}"}

    patients: list[dict] = audience_data.get("patients", [])
    if not patients:
        return {"error": "No 'patients' array found in audience.json."}

    def _is_control(patient_id: str, pct: float) -> bool:
        """Deterministic group assignment: hash patient_id → 0–99 bucket."""
        bucket = int(hashlib.md5(patient_id.encode()).hexdigest(), 16) % 100
        return bucket < int(pct * 100)

    # Write output CSV
    output_dir.mkdir(parents=True, exist_ok=True)
    control_count = test_count = 0
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["patient_id", "group", "best_content", "email"]
        )
        writer.writeheader()
        for p in patients:
            pid = p.get("patient_id", "")
            group = "control" if _is_control(pid, holdout_pct) else "test"
            if group == "control":
                control_count += 1
                content_value = ""          # control patients receive no message
            else:
                test_count += 1
                content_value = winning_message

            writer.writerow({
                "patient_id": pid,
                "group": group,
                "best_content": content_value,
                "email": p.get("email", ""),
            })

    total = control_count + test_count
    return {
        "output_file": str(output_path),
        "rows_written": total,
        "test_count": test_count,
        "control_count": control_count,
        "best_variant_id": best_variant_id,
        "status": (
            f"Saved {total} rows to {output_path}. "
            f"test={test_count}, control={control_count} "
            f"({int(holdout_pct * 100)}% holdout). "
            f"Winning variant: '{best_variant_id}'."
        ),
    }


def prepare_campaign_recipients(csv_path: str = "") -> dict:
    """Read the latest simulation output CSV and return the list of 'test' recipients.

    This tool is used by the execution_agent to prepare the recipient list before
    calling the Gmail MCP tool to send each email individually.

    Reads the most recent ab_test_results_*.csv from output/ (or a specific
    file if csv_path is provided). Returns only rows where group == 'test'.

    Args:
        csv_path: Optional explicit path to a results CSV.
                  If empty, uses the most recent ab_test_results_*.csv in output/.

    Returns:
        Dict with:
          - recipients: list of {patient_id, email, message} for test patients
          - control_count: number of patients withheld (no email)
          - csv_used: path of the CSV that was read
          - email_subject: suggested subject line for the campaign
    """
    output_dir = _DATA_DIR.parent / "output"

    # Resolve CSV path
    if csv_path:
        target = Path(csv_path)
    else:
        csvs = sorted(output_dir.glob("ab_test_results_*.csv"), reverse=True)
        if not csvs:
            return {
                "error": (
                    f"No ab_test_results_*.csv found in {output_dir}. "
                    "Run a simulation first, then type 'execute' to send."
                )
            }
        target = csvs[0]  # most recent

    if not target.exists():
        return {"error": f"CSV not found: {target}"}

    recipients: list[dict] = []
    control_count = 0
    with target.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("group", "").strip() == "test":
                recipients.append({
                    "patient_id": row["patient_id"],
                    "email": row["email"],
                    "message": row["best_content"],
                })
            else:
                control_count += 1

    if not recipients:
        return {
            "error": "No 'test' rows found in the CSV — nothing to send.",
            "csv_used": str(target),
        }

    return {
        "recipients": recipients,
        "recipient_count": len(recipients),
        "control_count": control_count,
        "csv_used": str(target),
        "email_subject": "Important: Your Medication Refill Reminder",
        "status": (
            f"Ready to send to {len(recipients)} test patients "
            f"({control_count} in control group will not receive email). "
            f"CSV: {target.name}"
        ),
    }
