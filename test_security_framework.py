import os
import unittest
from security_utils import validate_path

class TestSecurityFramework(unittest.TestCase):
    def setUp(self):
        # Resolve active workspace absolute directory
        self.workspace_dir = os.path.abspath(os.getcwd())

    def test_safe_paths_permitted(self):
        # Absolute path inside workspace
        safe_abs_path = os.path.join(self.workspace_dir, "config.json")
        resolved = validate_path(safe_abs_path)
        self.assertEqual(resolved, safe_abs_path)
        
        # Relative path inside workspace
        safe_rel_path = "tools/memory_tools.py"
        resolved_rel = validate_path(safe_rel_path)
        expected_rel = os.path.abspath(os.path.join(self.workspace_dir, safe_rel_path))
        self.assertEqual(resolved_rel, expected_rel)
        
        # Deep nested path inside workspace
        safe_nested_path = "subdir/another_subdir/file.txt"
        resolved_nested = validate_path(safe_nested_path)
        expected_nested = os.path.abspath(os.path.join(self.workspace_dir, safe_nested_path))
        self.assertEqual(resolved_nested, expected_nested)

    def test_directory_traversal_blocked(self):
        # Traversing upward with dot-dots
        unsafe_traversal = "../main.py"
        with self.assertRaises(PermissionError):
            validate_path(unsafe_traversal)
            
        unsafe_traversal_deep = "subdir/../../../main.py"
        with self.assertRaises(PermissionError):
            validate_path(unsafe_traversal_deep)

    def test_system_paths_blocked(self):
        # Direct Windows path access
        win_system_path = "C:\\Windows\\System32\\drivers\\etc\\hosts"
        with self.assertRaises(PermissionError):
            validate_path(win_system_path)
            
        # Verify custom base path works same
        custom_base = os.path.join(self.workspace_dir, "test_folder")
        safe_custom = os.path.join(custom_base, "file.txt")
        self.assertEqual(validate_path(safe_custom, custom_base), os.path.abspath(safe_custom))
        
        unsafe_custom = os.path.join(self.workspace_dir, "main.py") # outside test_folder!
        with self.assertRaises(PermissionError):
            validate_path(unsafe_custom, custom_base)

if __name__ == "__main__":
    unittest.main()
