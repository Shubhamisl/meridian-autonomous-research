from src.meridian.application.pipeline.reliability_policy import ReliabilityPolicy


def test_reliability_policy_defaults_are_domain_specific():
    policy = ReliabilityPolicy()

    assert policy.coverage_for("biomedical").min_documents == 3
    assert policy.coverage_for("computer_science").min_documents == 3
    assert policy.coverage_for("general").min_documents == 2
    assert policy.relevance.auto_reject_below == 0.45
    assert policy.relevance.borderline_below == 0.70
    assert policy.relevance.final_accept_below == 0.60
