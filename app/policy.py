"""Action safety policy for App Builder V1."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    requires_approval: bool
    reason: str = ""
    category: str = "safe"


class ActionPolicy:
    """Classify actions before the agent executes them."""

    APPROVAL_RULES = {
        "human_auth": ("login", "sign in", "password", "external account", "user access flow"),
        "secrets": ("secret", "api key", "token"),
        "financial": ("payment", "pay", "purchase"),
        "external_communication": ("send email", "send message"),
        "release": ("publish", "deploy to production"),
    }
    BLOCKED_KEYWORDS = (
        "rm -rf /", "format disk", "wipe disk", "delete all files",
    )

    def decide(self, action: str) -> PolicyDecision:
        normalized = action.lower().strip()
        if any(keyword in normalized for keyword in self.BLOCKED_KEYWORDS):
            return PolicyDecision(False, False, "Potentially destructive action is blocked", "blocked")
        for category, keywords in self.APPROVAL_RULES.items():
            if any(keyword in normalized for keyword in keywords):
                return PolicyDecision(
                    False,
                    True,
                    f"Human approval is required for {category.replace('_', ' ')} action",
                    category,
                )
        return PolicyDecision(True, False, category="safe")
