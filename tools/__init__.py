from tools.system_tools import open_app
from tools.web_tools import web_search
from tools.file_tools import read_file, create_file
from tools.dev_tools import git_status

# Map of tool names to Python implementations
TOOL_FUNCTIONS = {
    "open_app": open_app,
    "web_search": web_search,
    "read_file": read_file,
    "create_file": create_file,
    "git_status": git_status
}

# OpenAI-compatible / Ollama tool schema declarations
tool_schemas = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Opens a pre-approved system application on the user's laptop (e.g. calculator, notepad, paint, explorer, browser). Do not call for general shell commands.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "The name of the application to launch (notepad, calculator, explorer, paint, browser)."
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Performs a web search by opening the query in the default browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads the text contents of a local file. Only reads text files, up to a limit of 5000 characters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The absolute or relative path to the file to read."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Writes text content to a new local file or overwrites an existing one.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The absolute or relative path of the file to create/write."
                    },
                    "content": {
                        "type": "string",
                        "description": "The text content to write into the file."
                    }
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Runs 'git status' in the specified folder to check the repository state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "The path to the git repository folder (defaults to '.' if not provided)."
                    }
                }
            }
        }
    }
]
