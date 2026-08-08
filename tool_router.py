from tools import TOOL_FUNCTIONS

def execute_tool(name: str, arguments: dict) -> str:
    """
    Looks up the tool function by name, unpacks arguments,
    executes it, and returns the string output.
    Catches exceptions to prevent the agent pipeline from crashing.
    """
    # If arguments is a string, parse it as JSON
    if isinstance(arguments, str):
        import json
        try:
            arguments = json.loads(arguments)
        except Exception as json_err:
            error_msg = f"Error: Arguments is a string but failed to parse as JSON: {json_err}"
            print(f"\033[1;31m[{error_msg}]\033[0m")
            return error_msg

    print(f"\033[1;33m[Routing Tool Call: {name} with arguments: {arguments}]\033[0m")
    
    if name not in TOOL_FUNCTIONS:
        return f"Error: Tool '{name}' is not in the allowlist of supported tools."
        
    try:
        # Fetch the local implementation
        func = TOOL_FUNCTIONS[name]
        
        # Execute it
        result = func(**arguments)
        
        # Log outcome to console
        print(f"\033[1;32m[Tool Execution Success: {name}]\033[0m")
        return str(result)
        
    except TypeError as te:
        error_msg = f"Error: Invalid arguments passed to tool '{name}'. Details: {te}"
        print(f"\033[1;31m[{error_msg}]\033[0m")
        return error_msg
    except Exception as e:
        error_msg = f"Error executing tool '{name}': {e}"
        print(f"\033[1;31m[{error_msg}]\033[0m")
        return error_msg
