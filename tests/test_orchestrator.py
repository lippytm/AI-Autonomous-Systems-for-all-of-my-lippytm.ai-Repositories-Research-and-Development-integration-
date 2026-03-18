"""Tests for the top-level Orchestrator."""

import pytest

from src.orchestrator import Orchestrator


BASE_CONFIG = {
    "system": {"name": "test", "dry_run": True},
    "content": {
        "platforms": ["blog"],
        "topics": ["AI"],
        "max_items_per_run": 2,
    },
    "advertising": {
        "target_platforms": ["google_ads"],
        "budget_limit_usd": 50.0,
        "max_campaigns_per_run": 2,
    },
    "research": {
        "sources": ["arxiv"],
    },
    "quality": {
        "checks": ["lint", "test"],
        "coverage_threshold": 80,
    },
    "integration": {
        "github": {"org": "lippytm"},
    },
}


class TestOrchestratorInit:
    def test_builds_from_config(self):
        orch = Orchestrator(BASE_CONFIG)
        assert orch.content_generator is not None
        assert orch.ad_manager is not None
        assert orch.research_agent is not None
        assert orch.qa_monitor is not None
        assert orch.repo_manager is not None


class TestOrchestratorRunOnce:
    def test_run_once_returns_summary(self):
        orch = Orchestrator(BASE_CONFIG)
        summary = orch.run_once()
        assert "repos_discovered" in summary
        assert "research_findings" in summary
        assert "content_items" in summary
        assert "qa_passed" in summary

    def test_run_once_content_count(self):
        orch = Orchestrator(BASE_CONFIG)
        summary = orch.run_once()
        assert summary["content_items"] == 2

    def test_qa_passed_in_dry_run(self):
        orch = Orchestrator(BASE_CONFIG)
        summary = orch.run_once()
        assert summary["qa_passed"] is True


class TestOrchestratorSubsystems:
    def test_run_qa_only(self):
        orch = Orchestrator(BASE_CONFIG)
        results = orch.run_qa_only()
        assert len(results) == 2  # lint + test
        assert all(r.passed for r in results)

    def test_run_content_only(self):
        orch = Orchestrator(BASE_CONFIG)
        items = orch.run_content_only()
        assert len(items) == 2

    def test_run_ads_only(self):
        orch = Orchestrator(BASE_CONFIG)
        campaigns = orch.run_ads_only(["AI", "ML"])
        assert len(campaigns) == 2

    def test_run_ads_empty_topics(self):
        orch = Orchestrator(BASE_CONFIG)
        campaigns = orch.run_ads_only([])
        assert campaigns == []


class TestFromConfig:
    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            Orchestrator.from_config(str(tmp_path / "nonexistent.yaml"))

    def test_loads_yaml(self, tmp_path):
        import yaml
        cfg_path = tmp_path / "config.yaml"
        cfg_path.write_text(yaml.dump(BASE_CONFIG))
        orch = Orchestrator.from_config(str(cfg_path), project_root=str(tmp_path))
        assert orch is not None
