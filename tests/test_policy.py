from app.policy import ActionPolicy


def test_safe_action_is_allowed():
    decision = ActionPolicy().decide("Create app files")
    assert decision.allowed
    assert not decision.requires_approval
    assert decision.category == "safe"


def test_sensitive_action_requires_approval():
    decision = ActionPolicy().decide("User login with external account")
    assert not decision.allowed
    assert decision.requires_approval
    assert decision.category == "human_auth"


def test_destructive_action_is_blocked():
    decision = ActionPolicy().decide("rm -rf /")
    assert not decision.allowed
    assert not decision.requires_approval
    assert decision.category == "blocked"
