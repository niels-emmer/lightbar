from pydantic import BaseModel
from typing import Any, List, Optional
from datetime import datetime


class Experiment(BaseModel):
    id: str
    theme: str
    inspiration: str
    description: str
    duration_minutes: int
    acts: List[dict[str, Any]]   # [{pattern, duration_sec, ...params}]
    created_at: datetime
    prompted_by: Optional[str] = None


class EngineStatus(BaseModel):
    running: bool
    light_on: bool
    timer_paused: bool
    device_online: bool
    current_experiment: Optional[Experiment]
    current_step_index: int
    current_hue: float
    current_saturation: float
    current_value: float
    experiment_started_at: Optional[datetime]
    next_experiment_in_seconds: Optional[int]


class PowerRequest(BaseModel):
    on: bool


class PauseRequest(BaseModel):
    paused: bool


class LogEntry(BaseModel):
    timestamp: datetime
    level: str       # "info" | "ai" | "device" | "error" | "user"
    message: str
    data: Optional[dict] = None


class PromptRequest(BaseModel):
    prompt: str
