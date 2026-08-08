import os
import sqlite3
from datetime import datetime

class MemoryManager:
    """
    Manages Project Jarvis's memory subsystem.
    Combines Short-Term RAM-based tracking (active task/project/goal)
    with SQLite-backed Long-Term Memory (user identity, preferences, histories).
    """
    def __init__(self, db_path: str = "memory.db"):
        self.db_path = db_path
        
        # Short-Term Memory (RAM)
        self.short_term = {
            "active_project": "None",
            "active_task": "None",
            "active_goal": "None",
            "blockers": "None"
        }
        
        self._init_db()
        self._restore_session_context()

    def _init_db(self) -> None:
        """Initializes SQLite database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Long-Term Semantic Memory Table (Facts, Identity, Preferences)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semantic_memory (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT NOT NULL,
                importance TEXT DEFAULT 'medium',
                updated_at TEXT NOT NULL
            )
        """)
        
        # Long-Term Episodic Memory Table (Past session summaries)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_summary TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        
        # Persistent Short-Term Session Context Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_context (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()

    def _restore_session_context(self) -> None:
        """Loads saved context parameters from SQLite back into RAM on boot."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM session_context")
            rows = cursor.fetchall()
            for row in rows:
                k, v = row[0], row[1]
                if k in self.short_term:
                    self.short_term[k] = v
            conn.close()
        except Exception as e:
            print(f"Warning: Failed to restore session context: {e}")

    def get_restored_greeting(self) -> str:
        """Generates a customized voice greeting based on the loaded context."""
        try:
            # Look up username in long-term identity memory
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM semantic_memory WHERE key = 'user_name'")
            row = cursor.fetchone()
            conn.close()
            user_name = row[0] if row else "Spiderman"
        except:
            user_name = "Spiderman"
            
        project = self.get_short_term("active_project")
        task = self.get_short_term("active_task")
        
        proj_clean = project.strip() if project else "None"
        task_clean = task.strip() if task else "None"
        
        if proj_clean not in ("", "None", "none"):
            if task_clean not in ("", "None", "none"):
                return f"Welcome back, {user_name}! Resuming work on Project {proj_clean}, task: {task_clean}."
            return f"Welcome back, {user_name}! Resuming work on Project {proj_clean}."
            
        return f"Welcome back, {user_name}! Jarvis is active."

    # --- Short-Term Memory (RAM) Methods ---
    def set_short_term(self, key: str, value: str) -> None:
        """Sets a key in active RAM-based short term memory and persists it to SQLite."""
        if key in self.short_term:
            self.short_term[key] = value
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO session_context (key, value)
                    VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """, (key, value))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Warning: Failed to persist short term context '{key}': {e}")

    def get_short_term(self, key: str) -> str:
        """Retrieves active RAM-based short term memory value."""
        return self.short_term.get(key, "None")

    # --- Long-Term Semantic Memory Methods ---
    def store_semantic_memory(self, key: str, value: str, category: str, importance: str = "medium") -> None:
        """Inserts or updates a fact in the SQLite semantic store."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO semantic_memory (key, value, category, importance, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value=excluded.value,
                category=excluded.category,
                importance=excluded.importance,
                updated_at=excluded.updated_at
        """, (key, value, category, importance, now))
        
        conn.commit()
        conn.close()

    def retrieve_semantic_memories(self, category: str = None) -> list[dict]:
        """Retrieves semantic memories. Filters by category if provided."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if category:
            cursor.execute("""
                SELECT key, value, category, importance, updated_at 
                FROM semantic_memory 
                WHERE category = ?
            """, (category,))
        else:
            cursor.execute("""
                SELECT key, value, category, importance, updated_at 
                FROM semantic_memory
            """)
            
        rows = cursor.fetchall()
        conn.close()
        
        memories = []
        for row in rows:
            memories.append({
                "key": row[0],
                "value": row[1],
                "category": row[2],
                "importance": row[3],
                "updated_at": row[4]
            })
        return memories

    def delete_semantic_memory(self, key: str) -> bool:
        """Deletes a fact from the SQLite semantic store by its key."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM semantic_memory WHERE key = ?", (key,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return deleted

    def get_memory_context_string(self) -> str:
        """Formats active short-term and semantic memories into a prompt instruction context string."""
        memories = self.retrieve_semantic_memories()
        
        lines = []
        lines.append("=== SYSTEM CONTEXT & MEMORIES ===")
        lines.append(f"Active Project: {self.get_short_term('active_project')}")
        lines.append(f"Active Task: {self.get_short_term('active_task')}")
        lines.append(f"Active Goal: {self.get_short_term('active_goal')}")
        lines.append(f"Current Blockers: {self.get_short_term('blockers')}")
        lines.append("")
        
        if memories:
            lines.append("Stored Facts and Preferences:")
            for m in memories:
                lines.append(f"- [{m['category']}] {m['key']}: {m['value']}")
        else:
            lines.append("Stored Facts: No records found yet.")
            
        lines.append("=================================")
        return "\n".join(lines)
