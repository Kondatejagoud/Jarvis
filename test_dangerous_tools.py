import os
import unittest
from tools.file_tools import delete_file, create_file
from tools.system_tools import run_command

class TestDangerousTools(unittest.TestCase):
    def setUp(self):
        self.workspace_dir = os.path.abspath(os.getcwd())
        self.test_filename = "test_dangerous_tool_file.txt"
        self.test_filepath = os.path.join(self.workspace_dir, self.test_filename)
        
        # Write dummy file
        create_file(self.test_filename, "Dummy content for testing deletion.")

    def tearDown(self):
        # Clean up if still exists
        if os.path.exists(self.test_filepath):
            try:
                os.remove(self.test_filepath)
            except:
                pass

    def test_delete_file_success(self):
        # Verify file exists
        self.assertTrue(os.path.exists(self.test_filepath))
        
        # Run deletion tool
        result = delete_file(self.test_filename)
        self.assertIn("successfully deleted", result)
        
        # Assert file no longer exists
        self.assertFalse(os.path.exists(self.test_filepath))

    def test_delete_file_traversal_blocked(self):
        # Traversing upward should be blocked by validate_path inside delete_file
        result = delete_file("../unauthorized_delete.txt")
        self.assertIn("Access Denied", result)

    def test_run_command_stdout(self):
        # Run a simple echo command
        result = run_command("echo test_run_command_ok")
        self.assertIn("Exit Code: 0", result)
        self.assertIn("test_run_command_ok", result)

    def test_run_command_error(self):
        # Run a command that fails (returns non-zero exit code)
        result = run_command("powershell -Command \"exit 5\"")
        self.assertIn("Exit Code: 5", result)

if __name__ == "__main__":
    unittest.main()
