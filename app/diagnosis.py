"""Deterministic failure diagnosis used to make repair attempts actionable."""

from __future__ import annotations


class FailureDiagnoser:
    RULES = (
        ("javascript syntax", "Fix the JavaScript syntax error in app.js and keep the existing behavior."),
        ("missing required artifact", "Restore the missing generated artifact and keep the project contract intact."),
        ("missing or empty required artifact", "Recreate the missing or empty required artifact."),
        ("html references missing script", "Fix the HTML script reference so it points to an existing JavaScript file."),
        ("timepro html missing", "Restore the missing TimePro form/dashboard element required by the acceptance contract."),
        ("timepro logic missing", "Restore the missing TimePro behavior required by the functional test."),
        ("acceptance failed", "Repair the generated application to satisfy the failed acceptance criterion."),
        ("quality gate", "Repair the generated application according to the quality gate report."),
        ("project tests failed", "Fix the failing generated-project tests before retesting."),
    )

    def diagnose(self, message: str) -> dict:
        text = (message or "").strip()
        lowered = text.lower()
        for marker, action in self.RULES:
            if marker in lowered:
                return {
                    "category": marker,
                    "action": action,
                    "evidence": text[-2000:],
                    "confidence": "deterministic",
                }
        return {
            "category": "unknown",
            "action": "Inspect the failure evidence, repair the smallest affected component, then retest.",
            "evidence": text[-2000:],
            "confidence": "fallback",
        }
