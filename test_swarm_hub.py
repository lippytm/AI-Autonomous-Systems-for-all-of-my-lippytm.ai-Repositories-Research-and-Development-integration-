import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from unittest.mock import patch

from swarm_hub import Bus, Message, PullRequest, load_fleet, load_playbook, triage
from swarm_hub.bus import topic_matches
from swarm_hub.cli import main
from swarm_hub.github import GitHub, GitHubError
from swarm_hub.playbook import DEFAULT_PLAYBOOK, Pattern

TODAY = date(2026, 11, 9)


def pr(**overrides):
    base = dict(repo="r", number=1, title="t", author="lippytm", draft=False, mergeable=True,
                mergeable_state="clean", additions=10, changed_files=1, created=date(2026, 11, 1), ci="pass")
    return PullRequest(**(base | overrides))


class FleetTests(unittest.TestCase):
    def test_registry_covers_the_lippytm_fleet(self):
        fleet = load_fleet()
        self.assertEqual(18, len(fleet))
        self.assertEqual("lippytm/Factory.ai", fleet.get("factory").full_name)
        self.assertEqual("hub", fleet.by_repo("lippytm/AI-Autonomous-Systems-for-all-of-my-lippytm.ai-"
                                              "Repositories-Research-and-Development-integration-").id)
        self.assertIsNone(fleet.by_repo("not-in-fleet"))
        with self.assertRaises(KeyError):
            fleet.get("missing")

    def test_every_repo_is_listed_once(self):
        repos = [a.repo.casefold() for a in load_fleet()]
        self.assertEqual(len(repos), len(set(repos)))


class BusTests(unittest.TestCase):
    def test_topic_wildcards(self):
        self.assertTrue(topic_matches("swarm.*", "swarm.tasks"))
        self.assertFalse(topic_matches("swarm.*", "swarm.tasks.ci"))
        self.assertTrue(topic_matches("swarm.#", "swarm.tasks.ci"))
        self.assertTrue(topic_matches("swarm.#", "swarm"))
        self.assertFalse(topic_matches("swarm.#", "other.tasks"))
        self.assertTrue(topic_matches("a.b", "a.b"))

    def test_publish_delivers_and_isolates_failing_handlers(self):
        bus, seen = Bus(), []
        bus.subscribe("swarm.*", lambda m: seen.append(m.payload["n"]), "good")
        bus.subscribe("swarm.*", lambda m: 1 / 0, "broken")
        bus.publish(Message("swarm.tasks", {"n": 1}))
        self.assertEqual([1], seen)
        self.assertIn("broken: ZeroDivisionError", bus.dead_letters[0][1])

    def test_unhandled_messages_are_dead_lettered(self):
        bus = Bus()
        bus.publish(Message("nobody.listens", {}))
        self.assertEqual("no subscriber", bus.dead_letters[0][1])

    def test_route_by_capability(self):
        bus, got = Bus(load_fleet()), []
        bus.subscribe("agent.*.tasks", lambda m: got.append(m.topic))
        agents = bus.route("lint", {"task": "fix flake8"})
        self.assertEqual(["factory"], [a.id for a in agents])
        self.assertEqual(["agent.factory.tasks"], got)
        self.assertEqual([], bus.route("teleportation", {}))
        self.assertEqual("no agent has capability", bus.dead_letters[-1][1])


class PlaybookTests(unittest.TestCase):
    def test_every_lesson_recognises_its_example(self):
        self.assertEqual([], load_playbook().selftest())

    def test_cli_selftest_passes(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(0, main(["selftest"]))

    def test_diagnoses_todays_real_failures(self):
        playbook = load_playbook()
        cases = {
            "deprecated-artifact-action": "2026-11-08T02:00:01Z ##[error]This request has been automatically "
                                          "failed because it uses a deprecated version of "
                                          "`actions/upload-artifact: v3`. Learn more",
            "flake8-violations": "./bots/marvin_dca_bot.py:39:59: E231 missing whitespace after ','\n"
                                 "./bots/marvin_dca_bot.py:49:1: E302 expected 2 blank lines, found 1\n"
                                 "##[error]Process completed with exit code 1.",
            "actions-push-denied": "remote: Permission to lippytm/AI-Time-Machines.git denied to "
                                   "github-actions[bot].\nfatal: unable to access",
            "github-api-rate-limit": "jarvis.github_inventory.GitHubInventoryError: GitHub returned HTTP 403",
        }
        for expected, log in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(expected, playbook.diagnose(log)[0].pattern.id)
        flake = playbook.diagnose(cases["flake8-violations"])[0]
        self.assertEqual(2, flake.count)
        self.assertIn("E231", flake.evidence)

    def test_clean_log_has_no_diagnosis(self):
        self.assertEqual([], load_playbook().diagnose("Ran 25 tests in 0.6s\n\nOK\n"))

    def test_blocking_problems_sort_first(self):
        log = "GitHub returned HTTP 403\nE   ModuleNotFoundError: No module named 'yaml'\n"
        self.assertEqual(["missing-python-module", "github-api-rate-limit"],
                         [d.pattern.id for d in load_playbook().diagnose(log)])

    def test_learning_persists_and_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "playbook.json"
            shutil.copy(DEFAULT_PLAYBOOK, path)
            playbook = load_playbook(path)
            lesson = Pattern("npm-ci-lockfile", r"npm ci.*package-lock\.json", "Lockfile missing.",
                             "Commit package-lock.json.", "node", "blocking",
                             "npm ERR! npm ci can only install with an existing package-lock.json")
            playbook.learn(lesson)
            self.assertEqual("npm-ci-lockfile", load_playbook(path).patterns[-1].id)
            with self.assertRaises(ValueError):
                playbook.learn(lesson)
            with self.assertRaisesRegex(ValueError, "own example"):
                playbook.learn(Pattern("bad-lesson", "xyz", "d", "f", "node", "blocking", "abc"))
            with self.assertRaisesRegex(ValueError, "missing fix"):
                playbook.learn(Pattern("empty-fix", "abc", "d", " ", "node", "blocking", "abc"))
            self.assertEqual("npm-ci-lockfile", load_playbook(path).patterns[-1].id)
        with self.assertRaises(ValueError):
            Pattern("ok-id", "(", "d", "f", "c", "blocking", "e")
        with self.assertRaises(ValueError):
            Pattern("ok-id", "x", "d", "f", "c", "catastrophic", "x")

    def test_concurrent_learners_never_lose_a_lesson(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "playbook.json"
            shutil.copy(DEFAULT_PLAYBOOK, path)
            first, second = load_playbook(path), load_playbook(path)  # both read the same snapshot
            first.learn(Pattern("lesson-one", "one", "d", "f", "node", "blocking", "one"))
            second.learn(Pattern("lesson-two", "two", "d", "f", "node", "blocking", "two"))
            ids = [p.id for p in load_playbook(path).patterns]
            self.assertEqual(["lesson-one", "lesson-two"], ids[-2:])
            with self.assertRaisesRegex(ValueError, "already known"):
                first.learn(Pattern("lesson-two", "two", "d", "f", "node", "blocking", "two"))
            self.assertFalse(any(p.suffix == ".tmp" for p in Path(tmp).iterdir()))

    def test_diagnose_cli_exit_codes(self):
        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as log:
            log.write("remote: Permission to a/b.git denied to github-actions[bot].\n")
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(2, main(["diagnose", log.name, "--json"]))
        result = json.loads(out.getvalue())
        self.assertEqual("actions-push-denied", result[0]["id"])
        self.assertEqual(["hub", "dog", "copilot-healing"], result[0]["owners"])
        Path(log.name).write_text("all good\n")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(0, main(["diagnose", log.name]))
        Path(log.name).unlink()


class TriageTests(unittest.TestCase):
    def test_actions(self):
        cases = [
            (pr(), "merge-ready"),
            (pr(author="dependabot[bot]", ci="none"), "merge-ready"),
            (pr(ci="none"), "review-then-merge"),
            (pr(draft=True), "review-then-merge"),
            (pr(ci="fail"), "fix-ci"),
            (pr(ci="pending"), "wait"),
            (pr(mergeable=None, mergeable_state="unknown"), "wait"),
            (pr(mergeable=False, mergeable_state="dirty"), "rebase"),
            (pr(mergeable=False, mergeable_state="dirty", created=date(2025, 9, 1)), "close-stale"),
            (pr(additions=181_996, changed_files=228), "split-or-reject"),
            (pr(additions=0, changed_files=0), "close-empty"),
        ]
        for case, expected in cases:
            with self.subTest(expected=expected, case=case):
                self.assertEqual(expected, triage(case, TODAY).action)


class PrsCommandTests(unittest.TestCase):
    def test_incomplete_scan_fails(self):
        def broken(*args, **kwargs):
            raise GitHubError("GET /x -> HTTP 403")

        out, err = io.StringIO(), io.StringIO()
        with patch("swarm_hub.cli.GitHub.open_pulls", broken), redirect_stdout(out), \
                patch("sys.stderr", err):
            self.assertEqual(1, main(["prs", "--repo", "factory", "--json"]))
        self.assertEqual([], json.loads(out.getvalue()))
        self.assertIn("Incomplete: could not read factory", err.getvalue())


class Response:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class GitHubClientTests(unittest.TestCase):
    def test_open_pulls_builds_triage_records(self):
        pages = {
            "/repos/lippytm/r/pulls?state=open&per_page=100": [{"number": 7}],
            "/repos/lippytm/r/pulls/7": {"title": "Fix", "user": {"login": "lippytm"}, "draft": False,
                                         "mergeable": True, "mergeable_state": "clean", "additions": 3,
                                         "changed_files": 1, "created_at": "2026-11-01T00:00:00Z",
                                         "head": {"sha": "abc"}},
            "/repos/lippytm/r/commits/abc/check-runs?per_page=100": {"check_runs": [{"conclusion": "success"}]},
        }
        requests = []

        def opener(request, timeout):
            requests.append(request)
            return Response(pages[request.full_url.removeprefix("https://api.github.com")])

        pulls = GitHub(token="t", opener=opener).open_pulls("lippytm", "r")
        self.assertEqual("merge-ready", triage(pulls[0], TODAY).action)
        self.assertEqual("Bearer t", requests[0].get_header("Authorization"))
        self.assertTrue(all(r.get_method() == "GET" for r in requests))

    def test_no_token_sends_no_header_and_errors_are_explained(self):
        from email.message import Message as Headers
        from urllib.error import HTTPError
        headers = Headers()
        headers["X-RateLimit-Remaining"] = "0"

        def opener(request, timeout):
            self.assertIsNone(request.get_header("Authorization"))
            raise HTTPError(request.full_url, 403, "limited", headers, None)

        with patch.dict("os.environ", {}, clear=True):
            client = GitHub(opener=opener)
        with self.assertRaisesRegex(GitHubError, "rate limit"):
            client.get("/repos/lippytm/r")


class PreventionTests(unittest.TestCase):
    def test_every_rule_flags_bad_and_passes_good(self):
        from swarm_hub.prevent import selftest
        self.assertEqual([], selftest())

    def test_catches_the_real_failures_before_they_run(self):
        from swarm_hub.prevent import scan_text
        broken = (
            "on: push\n"
            "jobs:\n"
            "  scan:\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - uses: aquasecurity/trivy-action@master\n"
            "      - uses: github/codeql-action/upload-sarif@v3\n"
            "      - run: pip install -r requirements.txt\n"
            "      - uses: actions/upload-artifact@v3\n"
            "      - uses: peter-evans/create-pull-request@v6\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            found = scan_text(broken, "ci.yml", Path(tmp))
        self.assertEqual(
            ["sarif-without-permission", "missing-referenced-file", "retired-artifact-action",
             "push-without-write-permission", "unpinned-action", "codeql-action-v3"],
            [f.rule for f in found])
        self.assertEqual(7, found[0].line)
        self.assertEqual("error", found[0].severity)

    def test_fixed_workflow_is_clean(self):
        from swarm_hub.prevent import scan_text
        fixed = (
            "permissions:\n  contents: write\n  pull-requests: write\n  security-events: write\n"
            "jobs:\n  scan:\n    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25  # v0.36.0\n"
            "      - uses: github/codeql-action/upload-sarif@v4\n"
            "      - run: python -m unittest\n"
            "      - uses: actions/upload-artifact@v4\n"
            "      - uses: peter-evans/create-pull-request@v6\n"
            "      # git push is mentioned only in a comment\n"
        )
        self.assertEqual([], scan_text(fixed, "ci.yml", Path(".")))

    def test_files_resolve_against_each_steps_own_working_directory(self):
        from swarm_hub.prevent import scan_text
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "backend").mkdir()
            (root / "frontend").mkdir()
            (root / "backend" / "requirements.txt").write_text("")
            (root / "requirements.txt").write_text("")
            text = ("    steps:\n"
                    "      - name: backend deps\n"
                    "        working-directory: backend\n"
                    "        run: pip install -r requirements.txt\n"
                    "      - name: frontend deps\n"
                    "        working-directory: frontend\n"
                    "        run: |\n"
                    "          pip install -r requirements.txt\n"
                    "      - name: root deps\n"
                    "        run: pip install -r requirements.txt\n")
            found = scan_text(text, "ci.yml", root)
        self.assertEqual([("missing-referenced-file", 8)], [(f.rule, f.line) for f in found])

    def test_job_defaults_working_directory_applies_to_steps(self):
        from swarm_hub.prevent import scan_text
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app").mkdir()
            (root / "app" / "requirements.txt").write_text("")
            text = ("jobs:\n  test:\n    defaults:\n      run:\n        working-directory: app\n"
                    "    steps:\n      - run: pip install -r requirements.txt\n")
            self.assertEqual([], scan_text(text, "ci.yml", root))
            (root / "app" / "requirements.txt").unlink()
            (root / "requirements.txt").write_text("")
            self.assertEqual(["missing-referenced-file"], [f.rule for f in scan_text(text, "ci.yml", root)])

    def test_permissions_are_resolved_per_job(self):
        from swarm_hub.prevent import scan_text
        text = ("permissions:\n  contents: read\n"
                "jobs:\n"
                "  release:\n"
                "    permissions:\n      contents: write\n      security-events: write\n"
                "    steps:\n      - run: git push origin main\n"
                "  update:\n"
                "    steps:\n      - uses: peter-evans/create-pull-request@v6\n"
                "  scan:\n"
                "    steps:\n      - uses: github/codeql-action/upload-sarif@v4\n")
        found = [(f.rule, f.line) for f in scan_text(text, "ci.yml")]
        self.assertEqual([("push-without-write-permission", 12), ("sarif-without-permission", 15)], found)

    def test_workflow_permissions_apply_unless_a_job_overrides_them(self):
        from swarm_hub.prevent import scan_text
        text = ("permissions:\n  contents: write\n"
                "jobs:\n"
                "  ok:\n    steps:\n      - run: git push\n"
                "  narrowed:\n    permissions:\n      contents: read\n    steps:\n      - run: git push\n"
                "  all:\n    permissions: write-all\n    steps:\n      - run: git push\n")
        self.assertEqual([("push-without-write-permission", 11)],
                         [(f.rule, f.line) for f in scan_text(text, "ci.yml")])

    def test_flow_style_permissions_are_recognised(self):
        from swarm_hub.prevent import scan_text
        text = ("permissions: {contents: write, pull-requests: write}\n"
                "jobs:\n  update:\n    steps:\n      - uses: peter-evans/create-pull-request@v6\n"
                "  scan:\n    permissions: { contents: read }\n"
                "    steps:\n      - uses: github/codeql-action/upload-sarif@v4\n")
        self.assertEqual(["sarif-without-permission"], [f.rule for f in scan_text(text, "ci.yml")])

    def test_working_directory_defaults_do_not_leak_between_jobs(self):
        from swarm_hub.prevent import scan_text
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app").mkdir()
            (root / "requirements.txt").write_text("")
            text = ("jobs:\n"
                    "  first:\n    defaults:\n      run:\n        working-directory: app\n"
                    "    steps:\n      - run: echo hi\n"
                    "  second:\n    steps:\n      - run: pip install -r requirements.txt\n")
            self.assertEqual([], scan_text(text, "ci.yml", root))

    def test_this_repository_has_no_prevention_errors(self):
        from swarm_hub.prevent import scan_repository
        errors = [f for f in scan_repository(Path(__file__).parent) if f.severity == "error"]
        self.assertEqual([], errors)

    def test_prevent_cli_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflows = Path(tmp) / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "ci.yml").write_text("      - uses: actions/upload-artifact@v3\n")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(2, main(["prevent", tmp, "--json"]))
            self.assertEqual("retired-artifact-action", json.loads(out.getvalue())[0]["rule"])


class AutofixTests(unittest.TestCase):
    def test_fixes_versions_and_keeps_everything_else(self):
        from swarm_hub.prevent import autofix_text
        text = ("      - uses: actions/upload-artifact@v3   # keep comment\n"
                "      - uses: 'actions/setup-python@v4.7.1'\n"
                "      - uses: github/codeql-action/analyze@v3\n"
                "      - uses: actions/checkout@v4\n"
                "      - run: echo actions/upload-artifact@v3 is only text here\n")
        fixed, applied = autofix_text(text)
        self.assertEqual(
            "      - uses: actions/upload-artifact@v4   # keep comment\n"
            "      - uses: 'actions/setup-python@v5'\n"
            "      - uses: github/codeql-action/analyze@v4\n"
            "      - uses: actions/checkout@v4\n"
            "      - run: echo actions/upload-artifact@v3 is only text here\n", fixed)
        self.assertEqual(["codeql-action-v3", "outdated-core-action", "retired-artifact-action"], applied)
        self.assertEqual((fixed, []), autofix_text(fixed))

    def test_dry_run_then_write(self):
        from swarm_hub.prevent import autofix_repository, scan_repository
        with tempfile.TemporaryDirectory() as tmp:
            workflows = Path(tmp) / ".github" / "workflows"
            workflows.mkdir(parents=True)
            path = workflows / "ci.yml"
            path.write_text("    steps:\n      - uses: actions/upload-artifact@v3\n")
            changes = autofix_repository(tmp)
            self.assertIn("+      - uses: actions/upload-artifact@v4", changes[0]["diff"])
            self.assertIn("@v3", path.read_text())
            autofix_repository(tmp, write=True)
            self.assertEqual([], scan_repository(tmp))
            self.assertEqual([], autofix_repository(tmp))

    def test_only_whole_version_tokens_are_rewritten(self):
        from swarm_hub.prevent import autofix_text
        text = ("      - uses: actions/checkout@v1-custom\n"
                "      - uses: actions/checkout@v10\n"
                "      - uses: actions/setup-node@v3.8.1\n")
        fixed, applied = autofix_text(text)
        self.assertEqual("      - uses: actions/checkout@v1-custom\n"
                         "      - uses: actions/checkout@v10\n"
                         "      - uses: actions/setup-node@v4\n", fixed)
        self.assertEqual(["outdated-core-action"], applied)

    def test_structural_problems_are_not_auto_fixed(self):
        from swarm_hub.prevent import autofix_text
        text = "      - uses: peter-evans/create-pull-request@v6\n"
        self.assertEqual((text, []), autofix_text(text))


class TrainingTests(unittest.TestCase):
    def test_dataset_covers_every_lesson_and_rule(self):
        from swarm_hub.prevent import RULES
        from swarm_hub.training import GUARDRAILS, examples
        playbook = load_playbook()
        data = examples(playbook)
        kinds = [d["meta"]["kind"] for d in data]
        self.assertEqual(len(playbook.patterns), kinds.count("diagnose"))
        self.assertEqual(len(RULES), kinds.count("prevent"))
        self.assertEqual(sum(r.source_fix for r in RULES), kinds.count("no-problem"))
        self.assertEqual(len(GUARDRAILS), kinds.count("guardrail"))
        from swarm_hub.prevent import AUTOFIXES
        self.assertEqual(len(AUTOFIXES), kinds.count("autofix"))
        for item in data:
            self.assertEqual(["system", "user", "assistant"], [m["role"] for m in item["messages"]])
            self.assertTrue(all(m["content"].strip() for m in item["messages"]))

    def test_setting_only_rules_never_teach_removing_the_check(self):
        from swarm_hub.training import examples
        for item in examples(load_playbook()):
            if item["meta"].get("rule") == "dependency-review-needs-setting":
                answer = item["messages"][2]["content"]
                self.assertNotIn("Corrected", answer)
                self.assertNotIn("actions/checkout", answer)
                self.assertIn("Keep this step", answer)

    def test_committed_dataset_is_up_to_date(self):
        from swarm_hub.training import examples, to_jsonl
        committed = Path(__file__).parent / "training" / "swarm_repair.jsonl"
        self.assertEqual(to_jsonl(examples(load_playbook())), committed.read_text(encoding="utf-8"),
                         "Regenerate: python -m swarm_hub export-training -o training/swarm_repair.jsonl")


if __name__ == "__main__":
    unittest.main()
