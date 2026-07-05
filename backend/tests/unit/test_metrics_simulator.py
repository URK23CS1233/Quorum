"""Unit tests for the production metrics simulator."""

import asyncio

import pytest

import metrics_simulator as ms


# ── subscribe / unsubscribe ───────────────────────────────────────
def test_subscribe_registers_queue():
    q = ms.subscribe()
    assert isinstance(q, asyncio.Queue)
    assert q in ms._subscribers


def test_unsubscribe_removes_queue():
    q = ms.subscribe()
    ms.unsubscribe(q)
    assert q not in ms._subscribers


def test_unsubscribe_unknown_queue_is_safe():
    stray = asyncio.Queue()
    # Should not raise even though it was never subscribed.
    ms.unsubscribe(stray)


# ── mode transitions ──────────────────────────────────────────────
def test_trigger_and_resolve_incident():
    assert ms.current_mode() == "healthy"
    ms.trigger_incident("error_storm")
    assert ms.current_mode() == "critical"
    assert ms._state["scenario"] == "error_storm"
    assert ms._state["incident_tick"] == 0

    ms.resolve_incident()
    assert ms.current_mode() == "healthy"
    assert ms._state["scenario"] is None


# ── _generate_metrics ─────────────────────────────────────────────
def test_generate_metrics_healthy_shape_and_bounds():
    m = ms._generate_metrics()
    for key in ("timestamp", "cpu", "error_rate", "latency_p99",
                "requests_per_second", "memory_usage", "status"):
        assert key in m
    assert m["status"] == "healthy"
    assert 0.5 <= m["cpu"] <= 99.9
    assert 0.0 <= m["error_rate"] <= 99.9
    assert m["latency_p99"] >= 5.0
    assert m["requests_per_second"] >= 0.0
    assert 5.0 <= m["memory_usage"] <= 99.0


@pytest.mark.parametrize("scenario", ["error_storm", "cpu_spike",
                                      "latency_blowup", "memory_leak"])
def test_each_scenario_eventually_goes_critical(scenario):
    ms.trigger_incident(scenario)
    statuses = [ms._generate_metrics()["status"] for _ in range(15)]
    assert "critical" in statuses


def test_incident_tick_increments_during_incident():
    ms.trigger_incident("cpu_spike")
    ms._generate_metrics()
    ms._generate_metrics()
    assert ms._state["incident_tick"] == 2


def test_memory_leak_grows_over_time():
    ms.trigger_incident("memory_leak")
    first = ms._generate_metrics()["memory_usage"]
    for _ in range(8):
        last = ms._generate_metrics()["memory_usage"]
    assert last > first


def test_values_are_clamped_within_bounds_under_stress():
    ms.trigger_incident("latency_blowup")
    for _ in range(20):
        m = ms._generate_metrics()
        assert 0.5 <= m["cpu"] <= 99.9
        assert 0.0 <= m["error_rate"] <= 99.9
        assert 5.0 <= m["memory_usage"] <= 99.0


# ── broadcast_loop ────────────────────────────────────────────────
async def test_broadcast_loop_pushes_to_subscribers(monkeypatch):
    q = ms.subscribe()

    async def fake_sleep(_):
        raise asyncio.CancelledError

    monkeypatch.setattr(ms.asyncio, "sleep", fake_sleep)
    with pytest.raises(asyncio.CancelledError):
        await ms.broadcast_loop(0.01)

    assert not q.empty()
    payload = q.get_nowait()
    assert "cpu" in payload and "status" in payload


async def test_broadcast_loop_drops_full_subscribers(monkeypatch):
    q = ms.subscribe()
    for _ in range(q.maxsize):          # fill so put_nowait raises QueueFull
        q.put_nowait({"filler": True})

    async def fake_sleep(_):
        raise asyncio.CancelledError

    monkeypatch.setattr(ms.asyncio, "sleep", fake_sleep)
    with pytest.raises(asyncio.CancelledError):
        await ms.broadcast_loop(0.01)

    assert q not in ms._subscribers
