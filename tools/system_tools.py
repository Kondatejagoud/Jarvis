import subprocess
import webbrowser

# Map allowlisted applications to local executables or launch functions
APP_MAP = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "explorer": ["explorer.exe"],
    "paint": ["mspaint.exe"]
}

def open_app(app_name: str) -> str:
    """
    Safely opens a pre-approved system application.
    Does not execute raw shell commands.
    """
    app_key = app_name.strip().lower()
    
    if app_key == "browser":
        try:
            webbrowser.open("about:blank")
            return "Successfully opened default web browser."
        except Exception as e:
            return f"Failed to open web browser: {e}"
            
    if app_key in APP_MAP:
        try:
            # Run the pre-defined command list without shell=True to prevent injection
            subprocess.Popen(APP_MAP[app_key], shell=False)
            return f"Successfully opened {app_name}."
        except Exception as e:
            return f"Failed to launch application {app_name}: {e}"
            
    return f"Access Denied: Application '{app_name}' is not in the allowlist."
