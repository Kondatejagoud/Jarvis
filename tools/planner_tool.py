# tools/planner_tool.py

class ExecutionPlan:
    """
    Tracks the active multi-step plan registered by the LLM.
    Used by the orchestrator loop to coordinate sequential task execution.
    """
    def __init__(self):
        self.steps = []
        self.current_index = -1
        self.status = "idle"  # idle, active, completed, failed

    def register(self, steps: list[str]):
        self.steps = [str(s).strip() for s in steps if str(s).strip()]
        self.current_index = 0
        self.status = "active" if self.steps else "idle"

    def get_current_step(self) -> str:
        if self.status == "active" and 0 <= self.current_index < len(self.steps):
            return self.steps[self.current_index]
        return None

    def advance(self):
        if self.status == "active":
            self.current_index += 1
            if self.current_index >= len(self.steps):
                self.status = "completed"

    def fail(self):
        self.status = "failed"

    def reset(self):
        self.steps = []
        self.current_index = -1
        self.status = "idle"

# Global active plan instance
active_plan = ExecutionPlan()

def register_plan(steps: list[str]) -> str:
    """
    Registers a list of sequential steps to achieve a complex goal.
    This registers the plan so the orchestrator can execute it step-by-step.
    """
    if not steps or not isinstance(steps, list):
        return "Error: 'steps' parameter must be a list containing at least one step."
        
    active_plan.register(steps)
    formatted_steps = "\n".join([f"{i+1}. {step}" for i, step in enumerate(active_plan.steps)])
    return f"Plan successfully registered with {len(active_plan.steps)} steps:\n{formatted_steps}\nStarting execution of Step 1..."
