import json
import tempfile
import unittest
from pathlib import Path

from app.build_engine import BuildEngine
from app.quality import QualityGate
from app.specification import SpecificationBuilder


class TimeProQualityGateTests(unittest.TestCase):
    def test_timepro_acceptance_gate_passes_generated_mvp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mission = "Construa o TimePro"
            spec = SpecificationBuilder().build(mission)
            spec.save(root / ".app-builder" / "spec.json")
            BuildEngine(root).implement(mission)

            report = QualityGate().evaluate(root, spec.acceptance_criteria)

            self.assertTrue(report.passed, report.errors)
            self.assertEqual(len(report.acceptance_checks), 7)
            self.assertEqual(report.errors, [])

    def test_quality_gate_uses_saved_spec_without_mission_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mission = "Construa o TimePro"
            spec = SpecificationBuilder().build(mission)
            spec.save(root / ".app-builder" / "spec.json")
            BuildEngine(root).implement(mission)
            (root / ".app-builder" / "mission.txt").unlink()

            report = QualityGate().evaluate(root, spec.acceptance_criteria)

            self.assertTrue(report.passed, report.errors)

            saved = json.loads((root / ".app-builder" / "spec.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["app_name"], "TimePro")


if __name__ == "__main__":
    unittest.main()
