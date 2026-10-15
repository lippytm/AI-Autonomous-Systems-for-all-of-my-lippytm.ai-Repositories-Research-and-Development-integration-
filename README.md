# AI Autonomous Systems Integration

A dependency-free Python prototype for inspecting local repositories and learning
safe repository-development practices. It can discover Git working trees,
produce a JSON health report, and run short interactive lessons.

## Requirements

- Python 3.9 or newer
- Git for repository status checks (optional; findings remain available without it)

No package installation is required.

## Scan repositories

Point the scanner at a directory containing one or more Git repositories:

```sh
python3 marvin.py scan /path/to/your/repositories
```

Write the JSON report to a file when desired:

```sh
python3 marvin.py scan /path/to/your/repositories --output health-report.json
```

The scanner searches up to five directory levels and skips common dependency,
build, and version-control directories. It reports README, test, GitHub Actions,
and Git worktree status observations, with suggested next steps.

**Safety:** scans are report-only. They do not edit repositories, inspect Git
remotes, read credentials, contact external services, or run project commands.
Review recommendations and make changes separately. This prototype does not
generate or execute arbitrary code, and it is not yet connected to an AI service
or GitHub account.

## Interactive lessons

Show the available lessons:

```sh
python3 marvin.py learn
```

Start a lesson and answer its knowledge check:

```sh
python3 marvin.py learn --lesson automation-safety
```

Available lessons: `repo-basics`, `testing`, and `automation-safety`.

## Tests

Run the standard-library test suite:

```sh
python3 -m unittest -v
```

## Growing the prototype

Add repository checks as explicit, report-only rules first. Any future repair
automation should be opt-in, narrowly scoped, preview its exact diff, preserve
the repository's existing work, and require approval before applying changes.
