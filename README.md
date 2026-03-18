# AI Autonomous Systems — R&D Integration

> **Automated improvements across all lippytm.ai repositories, projects, and platforms.**

This repository provides a Python-based AI Autonomous Systems framework that continuously analyzes your GitHub repositories, surfaces improvement opportunities, and (optionally) takes automated actions — all powered by large language models.

---

## Architecture

```
src/
├── agents/
│   ├── base_agent.py              # Abstract agent interface & AgentResult
│   ├── code_improvement_agent.py  # Analyses source files for code quality
│   ├── repository_agent.py        # Checks repo health & standards
│   └── research_agent.py          # AI-driven R&D recommendations
├── core/
│   ├── config.py                  # YAML + env-var configuration
│   ├── logger.py                  # Structured logging
│   └── orchestrator.py            # Coordinates all agents across all repos
├── integrations/
│   ├── ai_integration.py          # OpenAI / Anthropic unified interface
│   └── github_integration.py      # PyGitHub wrapper
└── utils/
    └── helpers.py                 # General utilities
main.py                            # CLI entry point
config.yml                         # Default configuration
.github/workflows/
├── ai-autonomous-improvements.yml # Scheduled autonomous-run workflow
└── ci.yml                         # CI tests & lint
```

### Agents

| Agent | Purpose |
|-------|---------|
| **RepositoryAgent** | Checks for missing standard files (`README.md`, `.gitignore`, `LICENSE`, `SECURITY.md`), CI configuration, and open issue backlog. |
| **CodeImprovementAgent** | Scans source files and uses an LLM to suggest readability, performance, and security improvements. |
| **ResearchAgent** | Summarises each repository and generates targeted R&D recommendations for topics like best practices, security, and performance. |

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/lippytm/AI-Autonomous-Systems-for-all-of-my-lippytm.ai-Repositories-Research-and-Development-integration-
cd AI-Autonomous-Systems-for-all-of-my-lippytm.ai-Repositories-Research-and-Development-integration-
pip install -r requirements.txt
```

### 2. Configure environment

```bash
# Required
export GITHUB_TOKEN="ghp_..."          # Personal access token with repo + issues scopes
export OPENAI_API_KEY="sk-..."         # Or ANTHROPIC_API_KEY for Anthropic

# Optional — override config.yml
export GITHUB_REPOSITORIES="owner/repo1,owner/repo2"
export AI_PROVIDER="openai"            # "openai" | "anthropic"
export AI_MODEL="gpt-4o"
```

### 3. Edit `config.yml`

Open `config.yml` and set your target repositories and preferences (see inline comments).

### 4. Run

```bash
# Single run against configured repositories
python main.py run

# Target a specific repository
python main.py run --repo lippytm/my-project

# Run continuously (respects orchestrator.run_interval in config.yml)
python main.py run --continuous
```

Reports are saved as JSON files in the `reports/` directory.

---

## GitHub Actions

### Scheduled autonomous improvements

The workflow `.github/workflows/ai-autonomous-improvements.yml` runs daily at 02:00 UTC.

**Required repository secrets:**

| Secret | Description |
|--------|-------------|
| `AI_SYSTEM_GITHUB_TOKEN` | PAT with `repo` + `issues` + `pull_requests` scopes |
| `OPENAI_API_KEY` | OpenAI API key (if using OpenAI provider) |
| `ANTHROPIC_API_KEY` | Anthropic API key (if using Anthropic provider) |

You can also trigger it manually via **Actions → AI Autonomous Improvements → Run workflow**.

### CI

`.github/workflows/ci.yml` runs on every push/PR:
- Tests across Python 3.10, 3.11, 3.12
- Linting with `ruff`

---

## Configuration reference

See [`config.yml`](config.yml) for all options with inline documentation. Key sections:

- **`github`** — token, target repositories, PR labels
- **`ai`** — provider, model, temperature, retries
- **`agents`** — per-agent enable/disable and tuning parameters
- **`orchestrator`** — run interval, concurrency, log level, reports directory
- **`notifications`** — GitHub issue creation, assignees

---

## Running tests

```bash
pytest tests/ -v
```

---

## Security

- Secrets are never committed. All credentials are consumed via environment variables.
- The GitHub token only requires the minimum scopes needed (`repo`, `issues`).
- AI requests contain only repository metadata and source code — no credentials.
