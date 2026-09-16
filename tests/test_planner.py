import unittest

from app.planner import Planner


class PlannerTests(unittest.TestCase):
    def test_basic_mission(self):
        plan = Planner().create_plan("Create a simple Hello App")
        self.assertIn("Create the project structure", plan)
        self.assertIn("Implement the requested functionality", plan)
        self.assertIn("Run tests", plan)

    def test_time_tracking_mission_gets_focused_stages(self):
        mission = "Create a mobile timesheet app with login, forms, data storage and manager dashboard"
        plan = Planner().create_plan(mission)
        self.assertIn("Implement user access flow", plan)
        self.assertIn("Implement data storage layer", plan)
        self.assertIn("Implement input forms", plan)
        self.assertIn("Implement dashboard", plan)
        self.assertIn("Optimize mobile experience", plan)


if __name__ == "__main__":
    unittest.main()
