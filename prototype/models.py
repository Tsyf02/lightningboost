"""
LightningBoost · shared/models.py  (MERGED PERFECT)
─────────────────────────────────────────────────────
CJ's dataclasses + additional fields for I/O rates and battery
(needed by Tsyf's dashboard and the threaded monitor).
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from shared.config import TaskType, ExecutionLocation, TaskStatus


@dataclass
class SystemMetrics:
    """Full system resource snapshot — collected by the background monitor."""
    timestamp:        datetime         = field(default_factory=datetime.now)
    ram_percent:      float            = 0.0
    ram_used_mb:      float            = 0.0
    ram_available_mb: float            = 0.0
    cpu_percent:      float            = 0.0
    disk_percent:     float            = 0.0
    process_count:    int              = 0
    top_processes:    List[Tuple]      = field(default_factory=list)
    # I/O rates (added vs CJ's original)
    net_sent_mb_s:    float            = 0.0
    net_recv_mb_s:    float            = 0.0
    disk_read_mb_s:   float            = 0.0
    disk_write_mb_s:  float            = 0.0
    # Battery (for laptops — the whole point of the project!)
    battery_percent:  Optional[float]  = None
    battery_plugged:  Optional[bool]   = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @property
    def should_offload(self) -> bool:
        """Quick check — True when system is under pressure."""
        from shared.config import RAM_THRESHOLD_HIGH, CPU_THRESHOLD_HIGH
        return (self.ram_percent > RAM_THRESHOLD_HIGH or
                self.cpu_percent > CPU_THRESHOLD_HIGH or
                self.ram_available_mb < 500)


@dataclass
class Task:
    """A unit of work routed by LightningBoost."""
    id:                  str
    task_type:           TaskType
    description:         str
    input_data:          Dict[str, Any]
    status:              TaskStatus             = TaskStatus.PENDING
    execution_location:  Optional[ExecutionLocation] = None
    created_at:          datetime               = field(default_factory=datetime.now)
    started_at:          Optional[datetime]     = None
    completed_at:        Optional[datetime]     = None
    result:              Optional[Dict[str, Any]] = None
    error:               Optional[str]          = None

    @property
    def duration_s(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return round((self.completed_at - self.started_at).total_seconds(), 2)
        return None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['task_type']          = self.task_type.value
        data['status']             = self.status.value
        data['execution_location'] = self.execution_location.value if self.execution_location else None
        data['created_at']         = self.created_at.isoformat()
        data['started_at']         = self.started_at.isoformat() if self.started_at else None
        data['completed_at']       = self.completed_at.isoformat() if self.completed_at else None
        data['duration_s']         = self.duration_s
        return data


@dataclass
class RoutingDecision:
    """Decision made by the Task Router agent."""
    task_id:                   str
    location:                  ExecutionLocation
    confidence:                float              # 0.0 – 1.0
    reasoning:                 str
    estimated_time_local_sec:  Optional[float]   = None
    estimated_time_cloud_sec:  Optional[float]   = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id':                  self.task_id,
            'location':                 self.location.value,
            'confidence':               self.confidence,
            'reasoning':                self.reasoning,
            'estimated_time_local_sec': self.estimated_time_local_sec,
            'estimated_time_cloud_sec': self.estimated_time_cloud_sec,
        }


@dataclass
class SystemRecommendation:
    """AI-generated optimization recommendation."""
    severity:              str              # "high" | "medium" | "low"
    recommendation:        str
    action_command:        Optional[str]   = None
    estimated_ram_freed_mb:Optional[float] = None
    process_to_target:     Optional[str]   = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
