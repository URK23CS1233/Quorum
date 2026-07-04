"""Unit tests for dataset name resolution — no cognee or vellum needed."""

import pytest

from cognee_integration_vellum.scoping import MemoryScope, resolve_dataset


class TestResolveDataset:
    def test_workflow_scope_default(self):
        name = resolve_dataset(MemoryScope.WORKFLOW, workflow_name="support-bot")
        assert name == "vellum_support-bot"

    def test_workflow_scope_sanitises_spaces(self):
        name = resolve_dataset(MemoryScope.WORKFLOW, workflow_name="My Workflow")
        assert " " not in name
        assert name == "vellum_my_workflow"

    def test_workflow_scope_sanitises_slashes(self):
        name = resolve_dataset(MemoryScope.WORKFLOW, workflow_name="prod/support")
        assert "/" not in name

    def test_user_scope_with_user_id(self):
        name = resolve_dataset(
            MemoryScope.USER, workflow_name="support-bot", user_id="alice"
        )
        assert "alice" in name
        assert name == "vellum_support-bot_u_alice"

    def test_user_scope_without_user_id_raises(self):
        with pytest.raises(ValueError, match="user_id"):
            resolve_dataset(MemoryScope.USER, workflow_name="wf")

    def test_global_scope_ignores_workflow_and_user(self):
        name = resolve_dataset(
            MemoryScope.GLOBAL, workflow_name="anything", user_id="anyone"
        )
        assert name == "vellum_global"

    def test_env_fallback(self, monkeypatch):
        monkeypatch.setenv("VELLUM_WORKFLOW_NAME", "env-workflow")
        name = resolve_dataset(MemoryScope.WORKFLOW)
        assert "env-workflow" in name

    def test_default_fallback_when_no_env(self, monkeypatch):
        monkeypatch.delenv("VELLUM_WORKFLOW_NAME", raising=False)
        name = resolve_dataset(MemoryScope.WORKFLOW, workflow_name="")
        assert name == "vellum_default"
