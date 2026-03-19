#!/usr/bin/env python3
"""Tests for precheck.py phase transition logic."""

import pytest
from precheck import check_phase_transition


def _make_active(phase, criteria_met):
    """Helper: build an active.json-like dict with given phase and criteria flags."""
    criteria_list = ["eval_harness_exists_T3", "experiment_spec_ready_T3", "leo_approved_gpu_or_cpu_experiment"]
    state = {
        "phase": phase,
        "phase_exit_criteria": {
            "converge_to_execute": criteria_list,
        },
    }
    for key, met in zip(criteria_list, criteria_met):
        if met:
            state["phase_exit_criteria"][key] = True
    return state


class TestCheckPhaseTransition:
    def test_all_criteria_met_returns_recommendation(self):
        """When all exit criteria are true, should return PHASE_READY."""
        active = _make_active("converge", [True, True, True])
        result = check_phase_transition(active)
        assert result is not None
        assert "PHASE_READY" in result
        assert "converge→execute" in result

    def test_partial_criteria_returns_none(self):
        """When some criteria are missing, should return None."""
        active = _make_active("converge", [True, False, True])
        result = check_phase_transition(active)
        assert result is None

    def test_no_criteria_met_returns_none(self):
        """When no criteria are met, should return None."""
        active = _make_active("converge", [False, False, False])
        result = check_phase_transition(active)
        assert result is None

    def test_execute_phase_returns_none(self):
        """Already in execute phase — no further transition."""
        active = _make_active("execute", [True, True, True])
        result = check_phase_transition(active)
        assert result is None

    def test_explore_fallback_phase_checks_converge_criteria(self):
        """explore-fallback should still check converge_to_execute criteria."""
        active = _make_active("explore-fallback", [True, True, True])
        result = check_phase_transition(active)
        assert result is not None
        assert "explore-fallback→execute" in result

    def test_empty_criteria_returns_none(self):
        """No criteria defined → no recommendation."""
        active = {"phase": "converge", "phase_exit_criteria": {}}
        result = check_phase_transition(active)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
