"""
Quorum — Data Models
"Always knows your last agreed-upon safe state."
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import uuid


class Deployment(BaseModel):
    id: str = Field(default_factory=lambda: f"dep-{uuid.uuid4().hex[:8]}")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    commit_sha: str
    commit_message: str
    author: str
    services_affected: list[str]
    cpu_at_deploy: float
    error_rate_at_deploy: float
    latency_at_deploy: float
    status: Literal["STABLE", "DEGRADED", "INCIDENT", "ROLLED_BACK"] = "STABLE"
    branch: str = "main"
    repo: str = ""


class Incident(BaseModel):
    id: str = Field(default_factory=lambda: f"inc-{uuid.uuid4().hex[:8]}")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    triggered_by_deployment: str
    symptoms: dict
    root_cause: str
    resolution: str
    rolled_back_to_deployment: str
    rolled_back_to_commit: str
    time_to_resolve_minutes: int
    severity: Literal["P1", "P2", "P3"] = "P2"


class Metrics(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    cpu: float
    error_rate: float
    latency_p99: float
    requests_per_second: float
    memory_usage: float
    status: Literal["healthy", "degraded", "critical"] = "healthy"


class QuorumAnalysis(BaseModel):
    triggered_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    anomaly_type: str
    current_metrics: dict
    recall_answer: str
    similar_incident_id: Optional[str] = None
    similar_incident_summary: str
    safe_state_deployment_id: str
    safe_state_commit: str
    safe_state_commit_message: str
    confidence: Literal["high", "medium", "low"] = "medium"
    graph_insights: list[dict] = []


class IngestDeploymentRequest(BaseModel):
    deployment: Deployment

class IngestIncidentRequest(BaseModel):
    incident: Incident

class RollbackRequest(BaseModel):
    target_deployment_id: str
    reason: str = "Quorum-recommended rollback to last agreed-upon safe state"

class SimulateIncidentRequest(BaseModel):
    scenario: Literal["cpu_spike", "error_storm", "latency_blowup", "memory_leak"] = "error_storm"
