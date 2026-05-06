"""
Data models for LightningBoost
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
import json

from config import TaskType, ExecutionLocation, TaskStatus


@dataclass
class SystemMetrics:
    """Current system resource metrics"""
    timestamp: datetime = field(default_factory=datetime.now)
    ram_percent: float = 0.0  # 0-100%
    ram_used_mb: float = 0.0
    ram_available_mb: float = 0.0
    cpu_percent: float = 0.0  # 0-100%
    disk_percent: float = 0.0  # 0-100%
    process_count: int = 0
    top_processes: list = field(default_factory=list)  # [(name, pid, memory_mb), ...]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class Task:
    """Task representation"""
    id: str
    task_type: TaskType
    description: str
    input_data: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    execution_location: Optional[ExecutionLocation] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['task_type'] = self.task_type.value
        data['status'] = self.status.value
        data['execution_location'] = self.execution_location.value if self.execution_location else None
        data['created_at'] = self.created_at.isoformat()
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return data


@dataclass
class RoutingDecision:
    """Decision made by the routing agent"""
    task_id: str
    location: ExecutionLocation
    confidence: float  # 0-1
    reasoning: str
    estimated_time_local_sec: Optional[float] = None
    estimated_time_cloud_sec: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'location': self.location.value,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'estimated_time_local_sec': self.estimated_time_local_sec,
            'estimated_time_cloud_sec': self.estimated_time_cloud_sec,
        }


@dataclass
class SystemRecommendation:
    """AI-powered system optimization recommendation"""
    severity: str  # "high", "medium", "low"
    recommendation: str
    action_command: Optional[str] = None
    estimated_ram_freed_mb: Optional[float] = None
    process_to_target: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
