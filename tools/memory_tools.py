# tools/memory_tools.py

memory_manager = None  # Injected by JarvisCore on initialization

def store_memory(key: str, value: str, category: str, importance: str = "medium") -> str:
    """
    Stores or updates a fact/preference in long-term memory.
    Use this to remember facts like user name, preferences (coding models, UI layout), 
    or details about folders and tasks.
    """
    global memory_manager
    if not memory_manager:
        return "Error: Memory system not initialized."
    try:
        # Sanitize keys
        clean_key = key.strip().lower()
        memory_manager.store_semantic_memory(clean_key, value.strip(), category.strip().lower(), importance.strip())
        return f"Successfully stored memory: '{clean_key}' = '{value}' (Category: {category})"
    except Exception as e:
        return f"Error storing memory: {e}"

def retrieve_memories(category: str = None) -> str:
    """
    Retrieves stored memories. Optionally filters by category (e.g. preference, identity, project).
    """
    global memory_manager
    if not memory_manager:
        return "Error: Memory system not initialized."
    try:
        m_list = memory_manager.retrieve_semantic_memories(category)
        if not m_list:
            return "No memories found."
        lines = []
        for m in m_list:
            lines.append(f"- [{m['category']}] {m['key']}: {m['value']}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error retrieving memories: {e}"

def delete_memory(key: str) -> str:
    """
    Deletes a memory fact from the database by its key.
    """
    global memory_manager
    if not memory_manager:
        return "Error: Memory system not initialized."
    try:
        clean_key = key.strip().lower()
        deleted = memory_manager.delete_semantic_memory(clean_key)
        if deleted:
            return f"Successfully deleted memory with key: '{clean_key}'"
        else:
            return f"Memory with key '{clean_key}' not found."
    except Exception as e:
        return f"Error deleting memory: {e}"

def set_context(project: str = None, task: str = None, goal: str = None, blockers: str = None) -> str:
    """
    Updates the active short-term context (Project, Task, Goal, Blockers) of Jarvis.
    """
    global memory_manager
    if not memory_manager:
        return "Error: Memory system not initialized."
    try:
        updated = []
        if project is not None:
            memory_manager.set_short_term("active_project", project)
            updated.append(f"Project={project}")
        if task is not None:
            memory_manager.set_short_term("active_task", task)
            updated.append(f"Task={task}")
        if goal is not None:
            memory_manager.set_short_term("active_goal", goal)
            updated.append(f"Goal={goal}")
        if blockers is not None:
            memory_manager.set_short_term("blockers", blockers)
            updated.append(f"Blockers={blockers}")
        return f"Successfully updated short-term context: {', '.join(updated)}"
    except Exception as e:
        return f"Error updating context: {e}"
