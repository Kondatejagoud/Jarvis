import os
import json
from datetime import datetime
import config
import security

def write_audit_entry(
    command: str = None,
    gate_score: float = 0.0,
    is_verified: bool = False,
    tool_name: str = None,
    tool_args: str = None,
    outcome: str = None
) -> None:
    """
    Appends a new timestamped log entry to the encrypted audit log file.
    All parameters are optional to accommodate both verification failures
    and successful tool calls.
    """
    # 1. Create a new log entry dict
    entry = {
        "timestamp": datetime.now().isoformat(),
        "command": command,
        "gate_score": float(gate_score),
        "is_verified": bool(is_verified),
        "tool_name": tool_name,
        "tool_args": tool_args,
        "outcome": outcome
    }
    
    # 2. Retrieve existing logs (decrypt if file exists)
    logs = []
    log_path = config.AUDIT_LOG_PATH
    
    if os.path.exists(log_path):
        try:
            # Read encrypted bytes
            with open(log_path, 'rb') as f:
                encrypted_data = f.read()
                
            if encrypted_data:
                # Decrypt bytes to string
                decrypted_text = security.decrypt_log_data(encrypted_data)
                # Parse list of entries
                logs = json.loads(decrypted_text)
        except Exception as e:
            print(f"Warning: Failed to read/decrypt existing audit logs: {e}")
            print("Restarting audit log history.")
            logs = []
            
    # 3. Append the new entry
    logs.append(entry)
    
    # 4. Serialize and re-encrypt
    try:
        serialized_data = json.dumps(logs, indent=2)
        encrypted_data = security.encrypt_log_data(serialized_data)
        
        # Write back to disk
        with open(log_path, 'wb') as f:
            f.write(encrypted_data)
            
    except Exception as e:
        print(f"ERROR: Failed to write secure audit log entry: {e}")

def read_audit_entries() -> list:
    """
    Decrypts and parses the entire audit log history, returning a list of dicts.
    Returns an empty list if the log file doesn't exist or decryption fails.
    """
    log_path = config.AUDIT_LOG_PATH
    if not os.path.exists(log_path):
        return []
        
    try:
        with open(log_path, 'rb') as f:
            encrypted_data = f.read()
            
        if not encrypted_data:
            return []
            
        decrypted_text = security.decrypt_log_data(encrypted_data)
        return json.loads(decrypted_text)
    except Exception as e:
        print(f"Error reading audit log: {e}")
        return []
