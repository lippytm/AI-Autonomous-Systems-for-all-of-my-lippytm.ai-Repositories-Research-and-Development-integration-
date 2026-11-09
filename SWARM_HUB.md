# Swarm Hub

`swarm_hub/` is the working coordination layer for the lippytm AI Jarvis fleet. Its
parts are a registry of every repository agent, a Hermes message bus, a shared repair
playbook, and fleet-wide CI and PR triage. It uses only the Python standard library
(3.10+) and is **report-only**: it reads and recommends, but never pushes, merges,
comments or calls an AI provider.

```bash
python -m swarm_hub fleet                 # 18 agents, roles, capabilities
python -m swarm_hub selftest              # registry, every lesson and every prevention rule still work
python -m swarm_hub diagnose ci.log       # name known failures, the fix, and who owns it
python -m swarm_hub route lint "fix E501" # which agents a task goes to
GITHUB_TOKEN=... python -m swarm_hub health   # latest default-branch CI per repo
GITHUB_TOKEN=... python -m swarm_hub prs      # triage every open PR fleet-wide
python -m swarm_hub prevent ../repo-a ../repo-b  # find failure causes before CI runs them
python -m swarm_hub export-training -o training/swarm_repair.jsonl
```

`diagnose` exits `2` when it finds a blocking problem, so a workflow can gate on it.
Pipe a log in with `-`: `gh run view 123 --log-failed | python -m swarm_hub diagnose -`.

## How agents learn and teach: the repair loop

Every agent (Copilot, Claude, ChatGPT, Gemini, the Jarvis runtime) follows the same
five steps for any failure, so a lesson one agent learns is available to every other.

1. **Diagnose first.** Run `python -m swarm_hub diagnose` on the failing log. If a lesson
   matches, apply its fix. The `owners` field names the agents whose capability covers it.
2. **Reproduce before fixing.** Run the failing check locally and watch it fail.
3. **Fix the cause, not the symptom.** Keep the change as small as the failure needs.
   Never skip, delete or loosen a check to get green (lint ignore lists,
   dependency review, tests). If the cause is a repository *setting*, report it to the
   owner instead of working around it in code.
4. **Prove it.** Run the same check again and watch it pass, then run the repo's tests.
5. **Teach the swarm.** If no lesson matched, record one:

   ```bash
   python -m swarm_hub learn --id short-kebab-id \
     --match 'regex over the log line' \
     --diagnosis 'why it fails' --fix 'what to do' \
     --capability workflows --example 'the exact log line it came from' \
     --learned-from 'owner/repo run 12345'
   ```

   A lesson is only accepted if its regex matches its own example, and `selftest` (run
   in CI) re-proves every lesson on every push. Bad lessons cannot accumulate.

## Solving problems before they happen

Lessons describe a failure after it happened. **Prevention rules**
(`swarm_hub/prevent.py`) look for the cause in workflow source, so the failure never
happens in another repository. Each rule links to the lesson it prevents and carries a
bad and a good example; `selftest` proves every rule flags its bad example and passes
its good one.

| Rule | Severity | Stops |
|---|---|---|
| retired-artifact-action | error | `upload-artifact@v1-3` failing at "Set up job" |
| missing-referenced-file | error | `pip install -r` / `python x.py` on files that don't exist |
| push-without-write-permission | error | `git push` / create-pull-request with a read-only token |
| sarif-without-permission | error | upload-sarif without `security-events: write` |
| codeql-action-v3 | warning | CodeQL v3 retirement in December 2026 |
| outdated-core-action | warning | checkout/setup-python/setup-node on retired Node runtimes |
| unpinned-action | warning | third-party actions on `@master`/`@main` (supply chain) |
| dependency-review-needs-setting | info | dependency review failing while Dependency graph is off |

Run against the old, broken workflows, these rules flag every workflow-caused failure
from 2026-11-09 before it would have run. Run against the fleet, they found two
problems that had not yet failed: tower-control's CodeQL v3 (which would break in
December) and an unpinned `trivy-action@master` in AI-Time-Machines. Both are now fixed.

When you add a lesson whose cause is visible in source, add a rule with it, and set
`prevents` to the lesson's id.

## Training other AI systems

`python -m swarm_hub export-training` writes everything the swarm has verified as JSONL
chat examples ([training/swarm_repair.jsonl](training/swarm_repair.jsonl)), ready for
fine-tuning, few-shot prompts or evaluating any agent (ChatGPT, Gemini, Claude,
Copilot, Jarvis):

- `diagnose`: real CI log line → cause, fix, owner (one per lesson)
- `prevent`: risky workflow excerpt → problem and corrected excerpt (one per rule)
- `no-problem`: correct excerpt → "no problem found", so agents learn not to over-flag
- `guardrail`: tempting shortcut ("delete the check", "skip the test") → why not, and what to do

Every example comes from a self-tested lesson or rule, and a unit test fails if the
committed file falls out of date. After an agent runs `learn`, re-run `export-training` and commit the result.

## Lessons so far

`swarm_hub/playbook.json` holds ten lessons, all learned from real fleet failures on
2026-11-09: retired `upload-artifact@v3`, a missing `requirements.txt`, flake8
violations, Actions push denied, Dependency graph disabled, GitHub API rate limits,
missing Python modules, merge conflicts, missing SARIF upload permission, and template
schema mismatches. See [docs/FLEET_REVIEW_2026-11-09.md](docs/FLEET_REVIEW_2026-11-09.md)
for where each one came from.

## Pieces

| Module | Purpose |
|---|---|
| `fleet.py` + `fleet.json` | Agent registry: id, repository, role, capabilities |
| `bus.py` | Topic pub/sub (`swarm.*`, `swarm.#`), capability routing, dead letters; one failing handler cannot take down the others |
| `playbook.py` + `playbook.json` | Self-testing repair lessons: `diagnose`, `learn`, `selftest` |
| `triage.py` | Pure PR classifier: merge-ready, review, fix-ci, rebase, close-stale, … |
| `github.py` | GET-only GitHub client; sends `GITHUB_TOKEN` when set |

## Workflows

- **Swarm Hub CI**: lint, unit tests and playbook self-test on Python 3.10, 3.12 and 3.13.
- **AI Autonomous Improvements**: daily 02:00 UTC fleet patrol (health and PR triage) with
  the read-only job token, uploaded as an artifact.

To add a repository to the swarm, add one entry to `swarm_hub/fleet.json` and run
`python -m swarm_hub selftest`.
