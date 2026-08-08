import os
import unittest
from verify_tools_outcome import verify_action_outcome

class TestToolVerification(unittest.TestCase):
    def setUp(self):
        self.workspace_dir = os.path.abspath(os.getcwd())
        self.test_filename = "test_verification_dummy.txt"
        self.test_filepath = os.path.join(self.workspace_dir, self.test_filename)

    def tearDown(self):
        if os.path.exists(self.test_filepath):
            try:
                os.remove(self.test_filepath)
            except:
                pass

    def test_verify_create_file_success(self):
        # Create a file physically
        with open(self.test_filepath, "w", encoding="utf-8") as f:
            f.write("Some dummy test content.")
            
        args = {"file_path": self.test_filename, "content": "Some dummy test content."}
        is_ok, msg = verify_action_outcome("create_file", args, "Success")
        self.assertTrue(is_ok)
        self.assertEqual(msg, "Success")

    def test_verify_create_file_missing_on_disk(self):
        # Do not create the file physically
        args = {"file_path": self.test_filename, "content": "Some dummy test content."}
        is_ok, msg = verify_action_outcome("create_file", args, "Success")
        self.assertFalse(is_ok)
        self.assertIn("could not be verified on disk", msg)

    def test_verify_delete_file_success(self):
        # Do not create file physically (meaning it is deleted/gone)
        args = {"file_path": self.test_filename}
        is_ok, msg = verify_action_outcome("delete_file", args, "Success")
        self.assertTrue(is_ok)

    def test_verify_delete_file_still_present(self):
        # Create file physically (meaning delete failed)
        with open(self.test_filepath, "w", encoding="utf-8") as f:
            f.write("Some dummy test content.")
            
        args = {"file_path": self.test_filename}
        is_ok, msg = verify_action_outcome("delete_file", args, "Success")
        self.assertFalse(is_ok)
        self.assertIn("was not deleted and is still present", msg)

    def test_verify_open_app_active_process(self):
        # explorer.exe is always active on Windows
        args = {"app_name": "explorer"}
        is_ok, msg = verify_action_outcome("open_app", args, "Success")
        self.assertTrue(is_ok)

    def test_verify_open_app_inactive_process(self):
        # Test fictitious inactive process (or app not allowlisted)
        args = {"app_name": "notepad"}
        # Ensure notepad is closed before checking
        # If notepad is closed in tasklist, verify_action_outcome returns False
        import subprocess
        res = subprocess.run(["tasklist", "/FI", "IMAGENAME eq notepad.exe"], capture_output=True, text=True, shell=True)
        if "notepad.exe" not in res.stdout.lower():
            is_ok, msg = verify_action_outcome("open_app", args, "Success")
            self.assertFalse(is_ok)
            self.assertIn("not running in Windows Task Manager", msg)

    def test_verify_run_command_exit_code(self):
        # Valid exit code
        is_ok, msg = verify_action_outcome("run_command", {}, "Exit Code: 0\nStdout:\nhello")
        self.assertTrue(is_ok)
        
        # Invalid exit code
        is_ok_err, msg_err = verify_action_outcome("run_command", {}, "Exit Code: 1\nStderr:\nerror")
        self.assertFalse(is_ok_err)
        self.assertIn("Shell execution failed", msg_err)

if __name__ == "__main__":
    unittest.main()
