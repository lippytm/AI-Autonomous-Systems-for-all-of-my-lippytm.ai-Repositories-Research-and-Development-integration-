import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import marvin


class RepositoryScanTests(unittest.TestCase):
    def test_discovers_git_repositories_and_skips_dependency_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".git").mkdir()
            nested = root / "project"
            (nested / ".git").mkdir(parents=True)
            dependency = root / "node_modules" / "ignored"
            (dependency / ".git").mkdir(parents=True)

            found = marvin.discover_repositories(root)

            self.assertEqual(found, [root.resolve(), nested.resolve()])

    def test_scan_reports_missing_project_basics_without_modifying_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            (repository / ".git").mkdir()
            with patch("marvin.subprocess.run") as git_status:
                git_status.return_value.returncode = 0
                git_status.return_value.stdout = "## main\n M tracked.txt\n"
                report = marvin.scan(repository)

            self.assertEqual(report["repository_count"], 1)
            self.assertEqual(
                report["repositories"][0]["git_status"],
                "has-uncommitted-changes",
            )
            checks = {
                finding["check"]
                for finding in report["repositories"][0]["findings"]
            }
            self.assertEqual(
                checks, {"readme", "tests", "continuous-integration"}
            )
            self.assertEqual(list(repository.iterdir()), [repository / ".git"])

    def test_scan_rejects_non_directory_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            file_path = Path(temporary) / "not-a-directory"
            file_path.write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                marvin.scan(file_path)

    def test_report_is_json_serializable(self):
        with tempfile.TemporaryDirectory() as temporary:
            json.dumps(marvin.scan(temporary))


class LearningTests(unittest.TestCase):
    def test_correct_answer_passes_lesson(self):
        output = []
        result = marvin.run_lesson(
            "repo-basics", input_fn=lambda _prompt: "A", output_fn=output.append
        )

        self.assertTrue(result)
        self.assertIn("Correct.", output[-1])

    def test_wrong_answer_does_not_pass_lesson(self):
        output = []
        result = marvin.run_lesson(
            "testing", input_fn=lambda _prompt: "C", output_fn=output.append
        )

        self.assertFalse(result)
        self.assertIn("Not quite.", output[-1])


if __name__ == "__main__":
    unittest.main()
