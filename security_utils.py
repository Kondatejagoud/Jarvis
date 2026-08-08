# security_utils.py
import os

def validate_path(target_path: str, base_path: str = None) -> str:
    """
    Sanitizes and checks if target_path resides within the allowlisted workspace folder.
    Prevents path traversal attacks (e.g., read/write outside the project directory).
    Returns the absolute path if valid, otherwise raises a PermissionError.
    """
    if not target_path:
        raise ValueError("Error: Path parameter is empty.")
        
    if not base_path:
        # Default base path is the active workspace directory
        base_path = os.path.abspath(os.getcwd())
        
    abs_base = os.path.abspath(base_path)
    
    # Check for direct system path attempts on Windows (e.g., C:\Windows)
    # We resolve it relative to base_path first unless it's absolute
    if os.path.isabs(target_path):
        abs_target = os.path.abspath(target_path)
    else:
        abs_target = os.path.abspath(os.path.join(abs_base, target_path))
        
    # Standardize case for Windows comparisons
    abs_base_norm = os.path.normcase(abs_base)
    abs_target_norm = os.path.normcase(abs_target)
    
    try:
        common_path = os.path.commonpath([abs_base_norm, abs_target_norm])
        # The resolved common path must exactly match the base path prefix
        if os.path.normcase(common_path) != abs_base_norm:
            raise PermissionError(f"Access Denied: Path '{target_path}' attempts to access files outside the workspace.")
    except Exception as e:
        if isinstance(e, PermissionError):
            raise e
        raise PermissionError(f"Access Denied: Path '{target_path}' is invalid or outside the workspace.")
        
    return abs_target
