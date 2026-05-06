"""
LLM prompts for AI agent recommendations
"""

SYSTEM_OPTIMIZATION_PROMPT = """You are a helpful system optimization assistant. Given the current system metrics, provide 1-3 specific, actionable recommendations to free up RAM and improve performance.

Be concise and practical. Focus on:
1. Closing unnecessary applications
2. Clearing caches
3. Optimizing running processes
4. Enabling power saving modes

Format your response as a simple bullet list."""


def get_system_tips_prompt(ram_percent: float, cpu_percent: float, top_processes: list) -> str:
    """Generate a prompt for system optimization tips"""
    processes_str = "\n".join([f"  - {name}: {memory_mb:.1f}MB (PID: {pid})" 
                               for name, pid, memory_mb in top_processes[:5]])
    
    return f"""System Status:
- RAM Usage: {ram_percent:.1f}%
- CPU Usage: {cpu_percent:.1f}%

Top Memory Consumers:
{processes_str}

{SYSTEM_OPTIMIZATION_PROMPT}"""


TASK_ROUTING_PROMPT = """You are a task routing AI agent. Decide whether to run a task locally or on cloud GPU based on system metrics.

Consider:
- Current RAM and CPU usage
- Task complexity and estimated resource needs
- Available cloud resources
- Network latency

Respond with: "LOCAL" or "CLOUD" followed by a brief explanation (1-2 sentences)."""


def get_routing_decision_prompt(task_desc: str, ram_percent: float, cpu_percent: float, ram_available_mb: float) -> str:
    """Generate a prompt for routing decision"""
    return f"""Task: {task_desc}

Current System:
- RAM Usage: {ram_percent:.1f}%
- Available RAM: {ram_available_mb:.0f}MB
- CPU Usage: {cpu_percent:.1f}%

{TASK_ROUTING_PROMPT}"""


TASK_ANALYSIS_PROMPT = """Analyze this task and classify it:
1. Is it CPU-intensive or I/O-intensive?
2. Estimate memory requirements (small/medium/large)
3. Suggest if it should run locally or on GPU cloud

Keep response concise."""


def get_task_analysis_prompt(task_desc: str) -> str:
    """Generate a prompt for task analysis"""
    return f"""Task: {task_desc}

{TASK_ANALYSIS_PROMPT}"""


PERFORMANCE_SUMMARY_PROMPT = """Summarize the system's current performance and provide 1-2 tips for the user. Keep it friendly and actionable."""


def get_performance_summary_prompt(metrics_dict: dict) -> str:
    """Generate a prompt for performance summary"""
    return f"""System Snapshot:
- RAM: {metrics_dict.get('ram_percent', 0):.1f}% used
- CPU: {metrics_dict.get('cpu_percent', 0):.1f}% used
- Disk: {metrics_dict.get('disk_percent', 0):.1f}% used

{PERFORMANCE_SUMMARY_PROMPT}"""
