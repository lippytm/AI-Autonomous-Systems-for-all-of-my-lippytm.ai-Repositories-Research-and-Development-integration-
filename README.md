# lippytm.ai — AI Autonomous Systems Platform

> **Quality and Quality Assurance are Always Job #1**

A unified Research & Development platform that autonomously generates content,
manages advertising campaigns, conducts AI research, and enforces quality
standards — across **all** lippytm.ai repositories.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Modules](#modules)
6. [CLI Usage](#cli-usage)
7. [Running Tests](#running-tests)
8. [CI / CD](#ci--cd)
9. [Contributing](#contributing)

---

## Overview

The platform runs as a set of composable, testable Python modules wired
together by an **Orchestrator**.  Every external call (HTTP, subprocess,
ad-platform SDK) is injected through a callable dependency so the entire
system can be tested without credentials or network access.

Key capabilities:

| Capability | Module |
|---|---|
| Autonomous content creation (blog, social, video) | `src/autonomous/content_generator.py` |
| Advertising campaign management | `src/autonomous/ad_manager.py` |
| Continuous R&D research ingestion | `src/autonomous/research_agent.py` |
| Quality assurance (lint, test, coverage) | `src/quality/qa_monitor.py` |
| GitHub repository discovery & caching | `src/integration/repo_manager.py` |
| Full-cycle orchestration | `src/orchestrator.py` |
| CLI entry-point | `main.py` |

---

## Architecture

```
main.py  ──►  Orchestrator
                 ├── ContentGenerator   (platforms × topics → ContentItem)
                 ├── AdManager          (platforms × topics → Campaign)
                 ├── ResearchAgent      (sources × query  → ResearchFinding)
                 ├── QAMonitor          (checks × root    → CheckResult)
                 └── RepoManager        (org              → RepoInfo)
```

Each subsystem accepts an injectable `dry_run` flag and an injectable
I/O callable (publisher / ad_client / fetcher / runner / http_client)
so it can be used in tests, staging, or production without code changes.

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/lippytm/AI-Autonomous-Systems-...
cd AI-Autonomous-Systems-...

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run a full dry-run cycle (no credentials required)
python main.py --config config/config.yaml --mode once
```

---

## Configuration

Copy `config/config.yaml` and edit the values:

```yaml
system:
  dry_run: false          # Set true to preview without executing

content:
  platforms: [blog, social_media, youtube]
  topics: [AI research, autonomous systems]
  max_items_per_run: 5

advertising:
  enabled: true
  budget_limit_usd: 100.0
  target_platforms: [google_ads, social_media]

research:
  sources: [arxiv, github_trending]

quality:
  checks: [lint, test, coverage]
  coverage_threshold: 80

integration:
  github:
    org: lippytm
```

Sensitive values (tokens, API keys) should be set as environment
variables and never committed to the repository.

---

## Modules

### ContentGenerator

Generates titles and body copy for blog posts, social-media updates,
and video scripts, then delivers each item to a configurable publisher.

```python
from src.autonomous.content_generator import ContentGenerator

gen = ContentGenerator(
    platforms=["blog", "social_media"],
    topics=["AI", "autonomous systems"],
    max_items_per_run=3,
    publisher=my_publish_fn,   # or omit for logging stub
)
items = gen.run()
```

### AdManager

Creates advertising campaigns with budget allocation and tracks
impressions, clicks, and spend.

```python
from src.autonomous.ad_manager import AdManager

mgr = AdManager(
    platforms=["google_ads"],
    budget_limit_usd=100.0,
    ad_client=my_ad_sdk_fn,
)
campaigns = mgr.run(topics=["AI research", "machine learning"])
print(mgr.summary())
```

### ResearchAgent

Fetches structured research findings from configurable sources.

```python
from src.autonomous.research_agent import ResearchAgent

agent = ResearchAgent(sources=["arxiv", "github_trending"], fetcher=my_fetcher)
findings = agent.run("large language models")
```

### QAMonitor

Runs lint, test, and coverage checks and reports pass/fail.

```python
from src.quality.qa_monitor import QAMonitor

monitor = QAMonitor(project_root=".", checks=["lint", "test"], coverage_threshold=80)
results = monitor.run()
assert monitor.all_passed(results)
```

### RepoManager

Discovers GitHub repositories for an organisation.

```python
from src.integration.repo_manager import RepoManager

mgr = RepoManager(org="lippytm", token=os.environ["GITHUB_TOKEN"])
repos = mgr.discover()
```

### Orchestrator

Ties everything together:

```python
from src.orchestrator import Orchestrator

orch = Orchestrator.from_config("config/config.yaml")
summary = orch.run_once()
print(summary)
```

---

## CLI Usage

```
python main.py [--config PATH] [--mode MODE] [--topics ...] [--log-level LEVEL]

Modes:
  once      Full cycle across all subsystems (default)
  qa        Quality-assurance checks only
  content   Content generation only
  ads       Advertising campaigns only (requires --topics)

Examples:
  python main.py --mode once
  python main.py --mode qa
  python main.py --mode content
  python main.py --mode ads --topics "AI research" "machine learning"
```

---

## Running Tests

```bash
# All tests + coverage
pytest --cov=src --cov-report=term-missing

# Single module
pytest tests/test_content_generator.py -v
```

Current coverage: **95 %** across all modules.

---

## CI / CD

The `.github/workflows/ci.yml` pipeline runs on every push and pull
request across Python 3.10, 3.11, and 3.12:

1. **Lint** — `flake8` with `--max-line-length=99`
2. **Test** — `pytest` with coverage enforcement
3. **Artifact** — coverage XML uploaded for the Python 3.11 run

---

## Contributing

1. Fork the repository and create a feature branch.
2. Add or update tests to cover your changes.
3. Ensure `flake8` and `pytest` pass locally before opening a PR.
4. Quality Assurance is Job #1 — the CI pipeline must be green.
