import unittest
from tools.planner_tool import register_plan, active_plan

class TestPlannerSubsystem(unittest.TestCase):
    def setUp(self):
        active_plan.reset()

    def tearDown(self):
        active_plan.reset()

    def test_plan_registration_success(self):
        steps = ["Create a test file", "Open it in notepad", "Verify git status"]
        res = register_plan(steps)
        
        self.assertEqual(active_plan.status, "active")
        self.assertEqual(len(active_plan.steps), 3)
        self.assertEqual(active_plan.current_index, 0)
        self.assertEqual(active_plan.get_current_step(), "Create a test file")
        self.assertIn("Plan successfully registered with 3 steps", res)

    def test_plan_registration_empty(self):
        res = register_plan([])
        self.assertEqual(active_plan.status, "idle")
        self.assertIn("Error", res)

    def test_plan_sequential_advance(self):
        steps = ["Step A", "Step B"]
        register_plan(steps)
        
        self.assertEqual(active_plan.get_current_step(), "Step A")
        active_plan.advance()
        self.assertEqual(active_plan.current_index, 1)
        self.assertEqual(active_plan.get_current_step(), "Step B")
        
        active_plan.advance()
        self.assertEqual(active_plan.status, "completed")
        self.assertIsNone(active_plan.get_current_step())

    def test_plan_failure_aborts(self):
        steps = ["Step X", "Step Y"]
        register_plan(steps)
        
        self.assertEqual(active_plan.status, "active")
        active_plan.fail()
        self.assertEqual(active_plan.status, "failed")
        self.assertIsNone(active_plan.get_current_step())

if __name__ == "__main__":
    unittest.main()
