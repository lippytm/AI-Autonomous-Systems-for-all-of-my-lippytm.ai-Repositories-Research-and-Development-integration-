"""Tests for RepoManager."""

import pytest

from src.integration.repo_manager import RepoInfo, RepoManager


def _fake_client(url, headers):
    return [
        {
            "name": "my-repo",
            "full_name": "lippytm/my-repo",
            "description": "A test repo",
            "html_url": "https://github.com/lippytm/my-repo",
            "default_branch": "main",
            "language": "Python",
            "stargazers_count": 5,
            "open_issues_count": 2,
        }
    ]


def _empty_client(url, headers):
    return []


def _error_client(url, headers):
    raise RuntimeError("network error")


class TestRepoInfo:
    def test_to_dict_keys(self):
        r = RepoInfo(name="r", full_name="o/r", description="d", url="u")
        d = r.to_dict()
        assert "name" in d and "stars" in d and "fetched_at" in d


class TestRepoManagerInit:
    def test_empty_org_raises(self):
        with pytest.raises(ValueError):
            RepoManager(org="")

    def test_valid_init(self):
        mgr = RepoManager(org="lippytm", dry_run=True)
        assert mgr.org == "lippytm"


class TestDiscover:
    def test_discover_with_fake_client(self):
        mgr = RepoManager(org="lippytm", http_client=_fake_client)
        repos = mgr.discover()
        assert len(repos) == 1
        assert repos[0].name == "my-repo"

    def test_discover_empty_response(self):
        mgr = RepoManager(org="lippytm", http_client=_empty_client)
        repos = mgr.discover()
        assert repos == []

    def test_discover_client_error_returns_empty(self):
        mgr = RepoManager(org="lippytm", http_client=_error_client)
        repos = mgr.discover()  # must not raise
        assert repos == []

    def test_dry_run_uses_stub(self):
        mgr = RepoManager(org="lippytm", dry_run=True)
        repos = mgr.discover()
        assert len(repos) == 1
        assert repos[0].full_name == "lippytm/stub-repo"

    def test_discovered_repos_cached(self):
        mgr = RepoManager(org="lippytm", http_client=_fake_client)
        mgr.discover()
        assert mgr.get_repo("lippytm/my-repo") is not None

    def test_list_repos_after_discover(self):
        mgr = RepoManager(org="lippytm", http_client=_fake_client)
        mgr.discover()
        assert len(mgr.list_repos()) == 1

    def test_get_nonexistent_repo(self):
        mgr = RepoManager(org="lippytm", http_client=_fake_client)
        mgr.discover()
        assert mgr.get_repo("lippytm/no-such-repo") is None


class TestRepoInfoFields:
    def test_repo_fields_populated(self):
        mgr = RepoManager(org="lippytm", http_client=_fake_client)
        repos = mgr.discover()
        r = repos[0]
        assert r.language == "Python"
        assert r.stars == 5
        assert r.open_issues == 2
        assert r.default_branch == "main"
