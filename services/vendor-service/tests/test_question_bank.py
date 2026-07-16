from __future__ import annotations

import pytest

from app.services.question_bank import ALL_QUESTIONS, DOMAINS, questions_for_tier, score_for_answer


def test_total_question_bank_is_36():
    assert len(ALL_QUESTIONS) == 36
    assert len(DOMAINS) == 12


@pytest.mark.parametrize(
    "tier,expected_count",
    [("Critical", 36), ("High", 24), ("Medium", 18), ("Low", 12)],
)
def test_tier_scaled_question_counts(tier, expected_count):
    assert len(questions_for_tier(tier)) == expected_count


def test_low_tier_questions_are_a_subset_of_high_tier():
    low_codes = {q.code for q in questions_for_tier("Low")}
    high_codes = {q.code for q in questions_for_tier("High")}
    critical_codes = {q.code for q in questions_for_tier("Critical")}
    assert low_codes.issubset(high_codes)
    assert high_codes.issubset(critical_codes)


def test_every_domain_represented_at_every_tier():
    for tier in ("Critical", "High", "Medium", "Low"):
        domains_present = {q.domain for q in questions_for_tier(tier)}
        assert domains_present == set(DOMAINS)


def test_score_for_answer_mapping():
    assert score_for_answer("YES") == 100.0
    assert score_for_answer("PARTIAL") == 50.0
    assert score_for_answer("NO") == 0.0
    assert score_for_answer("NA") is None
    assert score_for_answer(None) is None


def test_score_for_answer_rejects_unknown_value():
    with pytest.raises(ValueError):
        score_for_answer("MAYBE")
