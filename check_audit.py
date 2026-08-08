import os
import json
from datetime import datetime
import config
from audit_log import read_audit_entries

def main():
    print("=" * 60)
    print("               JARVIS DECRYPTED AUDIT LOGS")
    print("=" * 60)
    
    log_path = config.AUDIT_LOG_PATH
    if not os.path.exists(log_path):
        print(f"No audit log file found at: {log_path}")
        print("Run the assistant first and speak some commands.")
        return
        
    entries = read_audit_entries()
    if not entries:
        print("Audit log is empty or could not be decrypted.")
        return
        
    print(f"Total Logged Actions: {len(entries)}")
    print("-" * 60)
    
    for idx, entry in enumerate(entries, 1):
        # Format timestamp
        ts_raw = entry.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_raw).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            ts = ts_raw
            
        print(f"\n[{idx}] Timestamp: {ts}")
        
        # Verification details
        is_verified = entry.get("is_verified", False)
        status_color = "\033[1;32mVERIFIED (Access Granted)\033[0m" if is_verified else "\033[1;31mUNVERIFIED (Access Denied)\033[0m"
        print(f"    Status:   {status_color}")
        print(f"    Speaker Gate Cosine Similarity: {entry.get('gate_score', 0.0):.4f}")
        
        if entry.get("command"):
            print(f"    Spoken Command: \"{entry.get('command')}\"")
            
        if entry.get("tool_name"):
            print(f"    Tool Called:    {entry.get('tool_name')}")
            print(f"    Tool Arguments: {entry.get('tool_args')}")
            
        # Outcome
        outcome = entry.get("outcome", "")
        # Truncate output if long
        if outcome and len(outcome) > 300:
            outcome = outcome[:300] + "... [truncated]"
        print(f"    Outcome:        {outcome}")
        print("-" * 60)

if __name__ == "__main__":
    main()
