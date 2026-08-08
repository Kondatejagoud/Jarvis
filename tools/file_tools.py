import os

def read_file(file_path: str) -> str:
    """
    Reads the content of a local text file.
    Limits read buffer size to 5000 characters to prevent context length exhaustion.
    """
    normalized_path = os.path.abspath(file_path)
    
    if not os.path.exists(normalized_path):
        return f"Error: File does not exist at path: '{file_path}'"
        
    if not os.path.isfile(normalized_path):
        return f"Error: Path is a directory, not a file: '{file_path}'"
        
    try:
        # Read file contents
        with open(normalized_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(5000)
            
        snippet_marker = "\n[Content truncated to 5000 characters]" if len(content) >= 5000 else ""
        return f"File contents from '{file_path}':\n---\n{content}{snippet_marker}\n---"
    except Exception as e:
        return f"Failed to read file: {e}"

def create_file(file_path: str, content: str) -> str:
    """
    Writes content to a new text file or overwrites an existing one.
    """
    normalized_path = os.path.abspath(file_path)
    parent_dir = os.path.dirname(normalized_path)
    
    try:
        # Ensure parent directory exists
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            
        with open(normalized_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return f"File successfully created/written at: '{file_path}'"
    except Exception as e:
        return f"Failed to create/write file: {e}"
