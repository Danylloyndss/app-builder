"""Action safety policy for App Builder V1."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    requires_approval: bool
    reason: str = ""


class ActionPolicy:
    """Classify actions before the agent executes them."""

    APPROVAL_KEYWORDS = (
        "login", "sign in", "password", "secret", "api key", "token",
        "payment", "pay", "purchase", "publish", "deploy to production",
        "delete production", "send email", "send message", "external account",
    )
    BLOCKED_KEYWORDS = (
        "rm -rf /", "format disk", "wipe disk", "delete all files",
    )

    def decide(self, action: str) -> PolicyDecision:
        normalized = action.lower()
        if any(keyword in normalized for keyword in self.BLOCKED_KEYWORDS):
            return PolicyDecision(False, False, "Potentially destructive action is blocked")
        if any(keyword in normalized for keyword in self.APPROVAL_KEYWORDS):
            return PolicyDecision(False, True, "Human approval is required for this action")
        return PolicyDecision(True, False)
