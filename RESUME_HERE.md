# 🔖 Resume here: bookmark from 2026-11-09

The bookmark for picking up the AI Jarvis swarm work. Start with **Step 1**. Everything after
it can be done by typing one of the chat phrases below.

---

## Step 1 · Two clicks only you can do (2 minutes)

These are repository **settings**. GitHub doesn't let a chat session change settings, so each one
is a single click in your browser. Sign in to GitHub as `lippytm`, then:

| # | Click this link | Then click |
|---|---|---|
| 1 | [AI-Time-Machines → security settings](https://github.com/lippytm/AI-Time-Machines/settings/security_analysis) | **Dependency graph → Enable** |
| 2 | [tower-control → security settings](https://github.com/lippytm/lippytm-lippytm.ai-tower-control-ai/settings/security_analysis) | **Dependency graph → Enable** |
| 3 *(optional)* | [AI-Time-Machines → Actions settings](https://github.com/lippytm/AI-Time-Machines/settings/actions) | Under *Workflow permissions*, tick **Allow GitHub Actions to create and approve pull requests** → **Save** |

**Can't find it?** On the repo page, click the **Settings** tab, then **Advanced Security** in the
left sidebar (older layout: **Code security and analysis**). If the button says **Disable**, the
setting is already on.

---

## Step 2 · Then just type these in chat

| Type this | What happens |
|---|---|
| **`I'm back, Dependency graph is on`** | Claude re-checks #51 and #95 and confirms they turned green |
| **`merge them`** | Merges the PRs that are green and approved (see the status table) |
| **`close the stale PRs`** | Closes the 45 old, conflicting PRs, each with a short note |
| **`check my repos`** | Checks CI on all 18 repos and explains anything broken |
| **`which PRs can I merge?`** | Sorts every open PR into merge, review, fix, rebase or close |
| **`prevent problems`** | Scans workflows for known failure causes before CI runs |
| **`teach the swarm`** | Records a new lesson so every agent recognises that failure next time |

These work because of the **swarm-hub skill** (`.claude/skills/swarm-hub/SKILL.md`), which teaches
Claude what each phrase means.

---

## Where things stand

| PR | What it does | Status | Next |
|---|---|---|---|
| [hub #9](https://github.com/lippytm/AI-Autonomous-Systems-for-all-of-my-lippytm.ai-Repositories-Research-and-Development-integration-/pull/9) | Swarm Hub: registry, playbook, prevention, auto-fix, training data, skill | ✅ CI green; all 17 review threads resolved; final review running | Merge after the last review |
| [Factory.ai #13](https://github.com/lippytm/Factory.ai/pull/13) | Fixes CI and Validate Templates (red since August) | ✅ Green and approved | **Ready to merge** |
| [DOG #24](https://github.com/lippytm/AI-Jarvis-Assistant-ChatGPT-Gemini-AI-GitHub-Claude-and-all-of-my-Repositories-DOG-Dog-dog-/pull/24) | Stops `jarvis-audit` failing on rate limits | ✅ Green and approved | **Ready to merge** |
| [AI-Time-Machines #51](https://github.com/lippytm/AI-Time-Machines/pull/51) | Security-scan upload permission, pinned trivy-action | ⛔ Dependency Review red | Step 1, link 1 |
| [tower-control #95](https://github.com/lippytm/lippytm-lippytm.ai-tower-control-ai/pull/95) | CodeQL v3 → v4 before the December retirement | ⛔ Dependency Review red (approved) | Step 1, link 2 |
| [AI-Time-Machines #50](https://github.com/lippytm/AI-Time-Machines/pull/50) | Dependency-update push permission | ✅ **Merged** | — |

Turning on Dependency graph (Step 1, link 2) also unblocks **17 other tower-control PRs**, mostly
Dependabot updates. Some of those are major-version upgrades (express 5, eslint 10, jest 30), so
merge them one at a time.

---

## What was built (one-line recap)

- **Fixed 7 broken workflows** across Factory.ai, AI-Time-Machines, the DOG repo and this hub.
- **Swarm Hub** (`python -m swarm_hub`):
  - `diagnose`: explains a failing CI log.
  - `prevent`: catches errors before CI runs.
  - `autofix`: safe version bumps only.
  - `prs` / `health`: fleet-wide PR triage and CI health.
  - `learn`: records new lessons.
  - `export-training`: writes 33 verified training examples.
- **10 lessons, 8 prevention rules, 67+ tests.** Every lesson and rule tests itself.
- **The full PR review** is in [docs/FLEET_REVIEW_2026-11-09.md](docs/FLEET_REVIEW_2026-11-09.md). How agents use the hub is in [SWARM_HUB.md](SWARM_HUB.md).

---

<sub>¹ **Footnote:** all work is on branch `claude/sleepy-rubin-2514me` in each repo. Nothing is
merged except AI-Time-Machines #50, which you approved. Claude merges, closes or comments only when
you ask in chat. Repository settings (Dependency graph, Actions permissions, secrets, branch
protection) always need your click, because GitHub blocks chat sessions from changing them.</sub>
