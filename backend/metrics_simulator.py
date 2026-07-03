"""
Quorum — Production Metrics Simulator
Emits realistic metrics that can be triggered into incident mode
to demo Quorum's anomaly detection live.
"""

import asyncio
import random

_state = {
    "mode": "healthy",
    "scenario": None,
    "incident_tick": 0,
    "base_cpu": 28.0,
    "base_error": 0.08,
    "base_latency": 95.0,
    "base_rps": 340.0,
    "base_memory": 52.0,
}

_subscribers: list[asyncio.Queue] = []


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=50)
    _subscribers.append(q)
    return q

def unsubscribe(q: asyncio.Queue):
    if q in _subscribers:
        _subscribers.remove(q)

def trigger_incident(scenario: str):
    _state["mode"] = "critical"
    _state["scenario"] = scenario
    _state["incident_tick"] = 0

def resolve_incident():
    _state["mode"] = "healthy"
    _state["scenario"] = None
    _state["incident_tick"] = 0

def current_mode() -> str:
    return _state["mode"]


def _generate_metrics() -> dict:
    t = _state["incident_tick"]
    scenario = _state["scenario"]
    mode = _state["mode"]

    def noise(base, pct):
        return base + base * pct * (random.random() - 0.5)

    cpu     = noise(_state["base_cpu"],     0.15)
    error   = noise(_state["base_error"],   0.30)
    latency = noise(_state["base_latency"], 0.12)
    rps     = noise(_state["base_rps"],     0.08)
    memory  = noise(_state["base_memory"],  0.06)

    if mode == "degraded":
        cpu *= 1.6; error *= 4.0; latency *= 2.2

    elif mode == "critical" and scenario:
        ramp = min(t / 8.0, 1.0)

        if scenario == "error_storm":
            error   = 0.08 + ramp * 18.0 + random.random() * 2.0
            latency = 95   + ramp * 1800  + random.random() * 200
            cpu     = 28   + ramp * 35    + random.random() * 8

        elif scenario == "cpu_spike":
            cpu     = 28  + ramp * 68 + random.random() * 5
            latency = 95  + ramp * 600 + random.random() * 80
            error   = 0.08 + ramp * 2.5

        elif scenario == "latency_blowup":
            latency = 95   + ramp * 4200 + random.random() * 500
            error   = 0.08 + ramp * 6.0  + random.random()
            cpu     = 28   + ramp * 25

        elif scenario == "memory_leak":
            memory  = 52  + t * 3.5 + random.random() * 2
            cpu     = 28  + t * 2.0
            latency = 95  + t * 80  + random.random() * 30
            error   = 0.08 + (t / 20.0) * 8.0

        _state["incident_tick"] += 1

    cpu     = max(0.5,  min(cpu,     99.9))
    error   = max(0.0,  min(error,   99.9))
    latency = max(5.0,  latency)
    rps     = max(0.0,  rps)
    memory  = max(5.0,  min(memory,  99.0))

    if error > 5.0 or cpu > 85.0 or latency > 2000:
        status = "critical"; _state["mode"] = "critical"
    elif error > 1.5 or cpu > 65.0 or latency > 500:
        status = "degraded"
        if _state["mode"] == "healthy": _state["mode"] = "degraded"
    else:
        status = "healthy"

    return {
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        "cpu": round(cpu, 2),
        "error_rate": round(error, 3),
        "latency_p99": round(latency, 1),
        "requests_per_second": round(rps, 1),
        "memory_usage": round(memory, 2),
        "status": status,
    }


async def broadcast_loop(interval_seconds: float = 2.0):
    while True:
        payload = _generate_metrics()
        dead = []
        for q in _subscribers:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            unsubscribe(q)
        await asyncio.sleep(interval_seconds)
