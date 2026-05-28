"""Unit tests for Aura Simulator simulation tools."""

import pytest
from aura_simulator.tools.simulation_tools import (
    analyze_target_audience,
    find_best_ab_combination,
    index_content_repository,
    run_ab_test_simulation,
)


class TestAnalyzeTargetAudience:
    def test_returns_required_keys(self):
        result = analyze_target_audience(
            "millennial urban professionals aged 25-35",
            "increase newsletter sign-up rate",
        )
        assert "total_audience_size" in result
        assert "segments" in result
        assert "audience_summary" in result

    def test_returns_three_segments(self):
        result = analyze_target_audience("young students", "boost course enrollment")
        assert len(result["segments"]) == 3

    def test_segment_fields_present(self):
        result = analyze_target_audience("senior affluent retirees", "promote premium service")
        for seg in result["segments"]:
            assert "segment_name" in seg
            assert "size" in seg
            assert "conversion_baseline" in seg
            assert "engagement_propensity" in seg

    def test_deterministic_output(self):
        r1 = analyze_target_audience("budget suburban families", "increase purchase rate")
        r2 = analyze_target_audience("budget suburban families", "increase purchase rate")
        assert r1["total_audience_size"] == r2["total_audience_size"]
        assert r1["segments"][0]["size"] == r2["segments"][0]["size"]

    def test_total_size_is_positive(self):
        result = analyze_target_audience("gen-z urban users", "drive app downloads")
        assert result["total_audience_size"] > 0

    def test_segment_sizes_sum_approximately(self):
        result = analyze_target_audience("professional executives", "email click-through")
        total = result["total_audience_size"]
        seg_total = sum(s["size"] for s in result["segments"])
        # Segments should account for ~100% (0.45+0.30+0.25=1.0) but rounding differs
        assert abs(seg_total - total) < total * 0.02  # within 2%


class TestIndexContentRepository:
    CONTENT = [
        "Homepage hero banner",
        "Email welcome series",
        "Promo popup discount",
        "Product recommendation carousel",
        "Loyalty rewards section",
    ]

    def test_returns_required_keys(self):
        result = index_content_repository(self.CONTENT, "increase newsletter sign-up rate")
        assert "total_content_items" in result
        assert "variants" in result
        assert "top_3_recommended" in result

    def test_variant_count_matches_input(self):
        result = index_content_repository(self.CONTENT, "boost purchases")
        assert result["total_content_items"] == len(self.CONTENT)
        assert len(result["variants"]) == len(self.CONTENT)

    def test_variants_sorted_by_relevance(self):
        result = index_content_repository(self.CONTENT, "increase newsletter sign-up rate")
        scores = [v["relevance_score"] for v in result["variants"]]
        assert scores == sorted(scores, reverse=True)

    def test_relevance_score_in_range(self):
        result = index_content_repository(self.CONTENT, "drive engagement")
        for v in result["variants"]:
            assert 0.0 <= v["relevance_score"] <= 1.0

    def test_top_3_recommended_are_top_items(self):
        result = index_content_repository(self.CONTENT, "increase purchases")
        top_titles = [v["title"] for v in result["variants"][:3]]
        assert result["top_3_recommended"] == top_titles

    def test_deterministic_output(self):
        r1 = index_content_repository(self.CONTENT, "sign-up rate")
        r2 = index_content_repository(self.CONTENT, "sign-up rate")
        assert r1["variants"][0]["relevance_score"] == r2["variants"][0]["relevance_score"]


class TestRunAbTestSimulation:
    BASE_PARAMS = dict(
        audience_segment_name="Core Audience",
        audience_size=100_000,
        baseline_conversion=0.05,
        content_variant_id="content_001",
        content_relevance_score=0.75,
        holdout_pct=0.20,
        use_case="increase sign-up rate",
    )

    def test_returns_required_keys(self):
        result = run_ab_test_simulation(**self.BASE_PARAMS)
        for key in ["lift_pct", "confidence_pct", "simulation_score", "is_significant", "recommendation"]:
            assert key in result

    def test_positive_lift_for_relevant_content(self):
        result = run_ab_test_simulation(**self.BASE_PARAMS)
        assert result["lift_pct"] > 0

    def test_small_group_returns_error(self):
        params = dict(self.BASE_PARAMS)
        params["audience_size"] = 100
        params["holdout_pct"] = 0.99
        result = run_ab_test_simulation(**params)
        assert "error" in result

    def test_holdout_sizes_computed_correctly(self):
        result = run_ab_test_simulation(**self.BASE_PARAMS)
        expected_holdout = int(100_000 * 0.20)
        assert result["holdout_size"] == expected_holdout

    def test_deterministic_output(self):
        r1 = run_ab_test_simulation(**self.BASE_PARAMS)
        r2 = run_ab_test_simulation(**self.BASE_PARAMS)
        assert r1["lift_pct"] == r2["lift_pct"]
        assert r1["simulation_score"] == r2["simulation_score"]

    def test_different_holdouts_give_different_results(self):
        p10 = dict(self.BASE_PARAMS, holdout_pct=0.10)
        p50 = dict(self.BASE_PARAMS, holdout_pct=0.50)
        r10 = run_ab_test_simulation(**p10)
        r50 = run_ab_test_simulation(**p50)
        # Scores should differ
        assert r10["simulation_score"] != r50["simulation_score"]

    def test_conversion_rates_are_valid(self):
        result = run_ab_test_simulation(**self.BASE_PARAMS)
        assert 0.0 <= result["control_conversion_rate"] <= 1.0
        assert 0.0 <= result["treatment_conversion_rate"] <= 1.0

    def test_confidence_in_range(self):
        result = run_ab_test_simulation(**self.BASE_PARAMS)
        assert 0.0 <= result["confidence_pct"] <= 100.0


class TestFindBestAbCombination:
    RESULTS = [
        {
            "variant_id": "content_001",
            "holdout_pct": 0.20,
            "audience_segment": "Core Audience",
            "holdout_size": 20000,
            "treatment_size": 80000,
            "control_conversion_rate": 0.05,
            "treatment_conversion_rate": 0.065,
            "lift_pct": 30.0,
            "confidence_pct": 97.5,
            "simulation_score": 12.5,
            "is_significant": True,
            "recommendation": "Strong positive result — recommend deploying this variant.",
        },
        {
            "variant_id": "content_002",
            "holdout_pct": 0.10,
            "audience_segment": "Core Audience",
            "holdout_size": 10000,
            "treatment_size": 90000,
            "control_conversion_rate": 0.05,
            "treatment_conversion_rate": 0.058,
            "lift_pct": 16.0,
            "confidence_pct": 88.0,
            "simulation_score": 5.2,
            "is_significant": False,
            "recommendation": "Moderate result.",
        },
        {"error": "Too small", "variant_id": "content_003", "holdout_pct": 0.95},
    ]

    def test_returns_best_combination(self):
        result = find_best_ab_combination(self.RESULTS)
        assert result["best_variant_id"] == "content_001"
        assert result["best_holdout_pct"] == 0.20

    def test_filters_out_errors(self):
        result = find_best_ab_combination(self.RESULTS)
        # total simulated includes error entries
        assert result["total_simulated"] == 3

    def test_top_n_respected(self):
        result = find_best_ab_combination(self.RESULTS, top_n=2)
        assert len(result["top_combinations_ranked"]) == 2

    def test_empty_results_returns_error(self):
        result = find_best_ab_combination([])
        assert "error" in result

    def test_all_errors_returns_error(self):
        bad = [{"error": "too small", "variant_id": "x", "holdout_pct": 0.99}]
        result = find_best_ab_combination(bad)
        assert "error" in result

    def test_summary_present(self):
        result = find_best_ab_combination(self.RESULTS)
        assert "summary" in result
        assert len(result["summary"]) > 10

    def test_leaderboard_present(self):
        result = find_best_ab_combination(self.RESULTS)
        assert "leaderboard" in result
        assert "#1" in result["leaderboard"]
