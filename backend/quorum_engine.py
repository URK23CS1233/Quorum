"""
Quorum — Core Engine
"Always knows your last agreed-upon safe state."

Watches live metrics, detects anomalies, queries Cognee memory
for matching incident patterns, and determines the safe rollback target.
AI removes human error from the DECISION. Human stays in control of the ACTION.
"""

import asyncio
import logging
from typing import Any
from models import Deployment, QuorumAnalysis, Metrics
import cognee_service
import metrics_simulator

logger = logging.getLogger(__name__)

THRESHOLDS = {
    "cpu_critical":      85.0,
    "error_critical":     5.0,
    "latency_critical": 2000.0,
    "cpu_degraded":      65.0,
    "error_degraded":     1.5,
    "latency_degraded":  500.0,
}

_active_incident: QuorumAnalysis | None = None
_incident_history: list[QuorumAnalysis] = []
_analysis_in_progress = False


def get_active_incident() -> QuorumAnalysis | None:
    return _active_incident

def get_incident_history() -> list[QuorumAnalysis]:
    return _incident_history[-20:]

def clear_active_incident():
    global _active_incident
    _active_incident = None


def detect_anomaly(m: Metrics) -> str | None:
    reasons = []

    if m.error_rate > THRESHOLDS["error_critical"]:
        reasons.append(f"error rate critical ({m.error_rate:.1f}%)")
    elif m.error_rate > THRESHOLDS["error_degraded"]:
        reasons.append(f"error rate elevated ({m.error_rate:.1f}%)")

    if m.cpu > THRESHOLDS["cpu_critical"]:
        reasons.append(f"CPU critical ({m.cpu:.1f}%)")
    elif m.cpu > THRESHOLDS["cpu_degraded"]:
        reasons.append(f"CPU elevated ({m.cpu:.1f}%)")

    if m.latency_p99 > THRESHOLDS["latency_critical"]:
        reasons.append(f"latency critical ({m.latency_p99:.0f}ms)")
    elif m.latency_p99 > THRESHOLDS["latency_degraded"]:
        reasons.append(f"latency elevated ({m.latency_p99:.0f}ms)")

    if not reasons:
        return None

    is_critical = (
        m.error_rate > THRESHOLDS["error_critical"] or
        m.cpu > THRESHOLDS["cpu_critical"] or
        m.latency_p99 > THRESHOLDS["latency_critical"]
    )
    return "; ".join(reasons) if is_critical else None


async def run_analysis(m: Metrics, anomaly_desc: str) -> QuorumAnalysis:
    logger.info(f"Quorum analysis triggered: {anomaly_desc}")

    recall_result = await cognee_service.recall(
        cpu=m.cpu, error_rate=m.error_rate,
        latency=m.latency_p99, anomaly_desc=anomaly_desc
    )

    safe_dep = _resolve_safe_state(recall_result)
    confidence = _score_confidence(recall_result, safe_dep)
    summary = _build_summary(recall_result)

    return QuorumAnalysis(
        anomaly_type=anomaly_desc,
        current_metrics={
            "cpu": m.cpu, "error_rate": m.error_rate,
            "latency_p99": m.latency_p99, "memory": m.memory_usage,
        },
        recall_answer=recall_result.get("answer", "No matching pattern yet. Seed incident history first."),
        similar_incident_summary=summary,
        safe_state_deployment_id=safe_dep.id if safe_dep else "unknown",
        safe_state_commit=safe_dep.commit_sha if safe_dep else "unknown",
        safe_state_commit_message=safe_dep.commit_message if safe_dep else "No safe state identified yet",
        confidence=confidence,
        graph_insights=recall_result.get("insights", []),
    )


async def monitor_loop():
    global _active_incident, _analysis_in_progress
    logger.info("Quorum monitor loop started.")

    while True:
        await asyncio.sleep(3)

        if _active_incident or _analysis_in_progress:
            continue

        m_dict = metrics_simulator._generate_metrics()
        m = Metrics(**m_dict)

        anomaly = detect_anomaly(m)
        if not anomaly:
            continue

        _analysis_in_progress = True
        logger.warning(f"🚨 QUORUM: {anomaly}")
        try:
            analysis = await run_analysis(m, anomaly)
            _active_incident = analysis
            _incident_history.append(analysis)
            logger.info(f"Analysis complete. Safe state: {analysis.safe_state_deployment_id}")
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
        finally:
            _analysis_in_progress = False


async def execute_rollback(target_dep_id: str, reason: str) -> dict[str, Any]:
    from models import Incident

    target = cognee_service.get_deployment(target_dep_id)
    if not target:
        return {"status": "error", "message": f"Deployment {target_dep_id} not found."}

    metrics_simulator.resolve_incident()

    global _active_incident
    if _active_incident:
        inc = Incident(
            triggered_by_deployment=_active_incident.safe_state_deployment_id,
            symptoms=_active_incident.current_metrics,
            root_cause=_active_incident.recall_answer[:500],
            resolution=f"Rolled back to {target_dep_id} ({target.commit_sha[:7]}): {target.commit_message}",
            rolled_back_to_deployment=target_dep_id,
            rolled_back_to_commit=target.commit_sha,
            time_to_resolve_minutes=3,
            severity="P1",
        )
        await cognee_service.remember_incident(inc)
        logger.info(f"Quorum learned from this rollback: {inc.id}")

    _active_incident = None

    return {
        "status": "ok",
        "message": f"Rolled back to {target.commit_sha[:7]}: {target.commit_message}",
        "deployment_id": target_dep_id,
        "commit": target.commit_sha,
    }


def _resolve_safe_state(recall_result: dict) -> Deployment | None:
    hint_id = recall_result.get("safe_deployment_hint")
    if hint_id:
        dep = cognee_service.get_deployment(hint_id)
        if dep:
            return dep
    return cognee_service.get_last_stable_deployment()

def _score_confidence(recall_result: dict, safe_dep: Deployment | None) -> str:
    answer   = recall_result.get("answer", "")
    insights = recall_result.get("insights", [])
    if len(answer) > 200 and len(insights) >= 3 and safe_dep:
        return "high"
    elif len(answer) > 50 and safe_dep:
        return "medium"
    return "low"

def _build_summary(recall_result: dict) -> str:
    summaries = recall_result.get("summaries", [])
    answer    = recall_result.get("answer", "")
    if summaries:
        return summaries[0][:300]
    if answer:
        return answer[:300]
    return "No similar incident in Quorum memory yet. Add incident history to improve recall accuracy."
