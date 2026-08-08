import os
import subprocess

def git_status(directory: str = ".") -> str:
    """
    Runs 'git status' inside the specified local directory.
    Executes the command safely without using shell execution.
    """
    # Clean and resolve the path
    target_dir = os.path.abspath(directory.strip() if directory else ".")
    
    if not os.path.exists(target_dir):
        return f"Error: Directory does not exist: '{directory}'"
        
    if not os.path.isdir(target_dir):
        return f"Error: Path is a file, not a directory: '{directory}'"
        
    try:
        # Run git status directly. shell=False prevents shell command injection
        result = subprocess.run(
            ["git", "status"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            shell=False,
            check=False
        )
        
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        
        output = []
        if stdout:
            output.append(stdout)
        if stderr:
            output.append(f"Errors/Warnings:\n{stderr}")
            
        if not output:
            return "git status returned no output (no repo or empty directory)."
            
        return "\n".join(output)
        
    except FileNotFoundError:
        return "Error: 'git' command not found. Ensure git is installed and added to the PATH."
    except Exception as e:
        return f"Failed to run git status: {e}"
