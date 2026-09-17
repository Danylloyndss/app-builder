import unittest

from app.specification import SpecificationBuilder
from app.timepro_blueprint import TIMEPRO


class TimeProMissionTests(unittest.TestCase):
    def test_timepro_is_first_class_specification(self):
        spec = SpecificationBuilder().build("Construa o TimePro")

        self.assertEqual(spec.app_name, "TimePro")
        self.assertEqual(spec.users, list(TIMEPRO.roles))
        self.assertEqual(spec.screens, list(TIMEPRO.screens))
        self.assertEqual(spec.data_entities, list(TIMEPRO.entities))
        for feature in TIMEPRO.features:
            self.assertIn(feature, spec.features)
        for criterion in TIMEPRO.acceptance_criteria:
            self.assertIn(criterion, spec.acceptance_criteria)

    def test_timepro_business_rules_are_explicit(self):
        spec = SpecificationBuilder().build("Build TimePro timesheet")

        self.assertIn("Total = end - start - break", spec.business_rules)
        self.assertIn("End time must be greater than or equal to start time", spec.business_rules)
        self.assertIn("Break must be zero or positive", spec.business_rules)


if __name__ == "__main__":
    unittest.main()
