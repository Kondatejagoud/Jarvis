# verify_tools_outcome.py
import os
import json
import subprocess
from security_utils import validate_path

def verify_action_outcome(tool_name: str, tool_args: dict, raw_result: str) -> tuple[bool, str]:
    """
    Verifies that the executed system tool actually had the desired physical effect.
    Returns:
        (is_verified: bool, output_message: str)
    """
    # If the tool itself already returned an execution error, pass it back
    if "Failed" in raw_result or "Error" in raw_result or "Access Denied" in raw_result:
        return False, raw_result

    # Standardize args
    if isinstance(tool_args, str):
        try:
            args = json.loads(tool_args)
        except:
            args = {}
    else:
        args = tool_args or {}

    if tool_name == "create_file":
        file_path = args.get("file_path", "")
        try:
            normalized_path = validate_path(file_path)
            # Verify file exists on disk
            if not os.path.exists(normalized_path):
                return False, f"Verification Error: File could not be verified on disk: '{file_path}'."
            # Verify file is not empty (if content was provided)
            if os.path.getsize(normalized_path) == 0 and args.get("content", ""):
                return False, f"Verification Error: File created but appears to be empty: '{file_path}'."
            return True, raw_result
        except Exception as e:
            return False, f"Verification Error during path checks: {e}"

    elif tool_name == "delete_file":
        file_path = args.get("file_path", "")
        try:
            normalized_path = validate_path(file_path)
            # Verify file is actually deleted
            if os.path.exists(normalized_path):
                return False, f"Verification Error: File was not deleted and is still present: '{file_path}'."
            return True, raw_result
        except Exception as e:
            return False, f"Verification Error during path checks: {e}"

    elif tool_name == "open_app":
        app_name = args.get("app_name", "").strip().lower()
        if app_name == "browser":
            # Browser defaults to launching about:blank, which might spin up many different user processes.
            # We don't perform task list check to avoid false negatives.
            return True, raw_result
            
        exe_map = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "explorer": "explorer.exe",
            "paint": "mspaint.exe"
        }
        
        target_exe = exe_map.get(app_name)
        if not target_exe:
            return True, raw_result  # Bypass if not an allowlisted exe
            
        try:
            # Query tasklist on Windows to see if target process is currently active
            res = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {target_exe}"],
                capture_output=True,
                text=True,
                shell=True
            )
            # Check for name or generic calculator mappings
            stdout_lower = res.stdout.lower()
            if target_exe.lower() in stdout_lower or (app_name == "calculator" and ("calc" in stdout_lower or "calculator" in stdout_lower)):
                return True, raw_result
            else:
                return False, f"Verification Error: Application process '{target_exe}' is not running in Windows Task Manager. It may have crashed or failed to launch."
        except:
            # Fall back to True if tasklist command fails due to privileges, preventing locks
            return True, raw_result

    elif tool_name == "run_command":
        # Check if the shell output indicates non-zero exit code
        if "Exit Code: 0" not in raw_result and "Exit Code:" in raw_result:
            return False, f"Verification Error: Shell execution failed.\nDetails:\n{raw_result}"
        return True, raw_result

    # Safe / query tools (web_search, read_file, git_status, memories) bypass verification
    return True, raw_result
