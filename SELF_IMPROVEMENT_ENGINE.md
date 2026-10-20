# 🔁 SELF-IMPROVEMENT ENGINE
# Feedback Loops, Lesson Capture, and Prompt Evolution for the lippytm.ai Swarm
# Author: Charles Earl Lipshay (lippytm)

---

## What Is the Self-Improvement Engine?

The Self-Improvement Engine is the mechanism by which the lippytm.ai AI Swarm gets **better over time without being manually reprogrammed**. It does this through three interconnected systems:

1. **Feedback Loops** — score every agent output and feed results back into routing logic
2. **Lesson Capture** — extract what worked and what failed from every completed task
3. **Prompt Evolution** — version and upgrade agent system prompts based on performance data

Together, these systems ensure the swarm continuously learns, adapts, and improves — becoming more capable with every task it completes.

---

## System 1 — Feedback Loop Architecture

### How It Works

Every time an agent completes a task, the output is scored across four dimensions:

| Dimension | Description | Score Range |
|---|---|---|
| Quality | How good is the output? (accuracy, completeness, correctness) | 0–100 |
| Speed | How fast was the execution vs. expected baseline? | 0–100 |
| Efficiency | Token and compute cost vs. output value | 0–100 |
| Relevance | Did the output address the actual request? | 0–100 |

**Composite Score = (Quality × 0.5) + (Speed × 0.2) + (Efficiency × 0.15) + (Relevance × 0.15)**

### Scoring Sources

1. **Auto-Scorer** — rule-based checks (code runs without errors, output length, format compliance)
2. **Peer Reviewer** — Marvin Review agent evaluates outputs of other agents
3. **Human Feedback** — Charles provides explicit feedback on outputs (thumbs up/down, notes)
4. **Outcome Tracking** — was the task's downstream result successful? (e.g., deployed code worked)

### Feedback Flow

```
Agent completes task
        │
        ▼
Auto-Scorer runs checks ──────────────► Score recorded in Feedback DB
        │
        ▼
Marvin Review evaluates output ───────► Score updated in Feedback DB
        │
        ▼ (async, 24h window)
Human feedback captured ──────────────► Score finalized
        │
        ▼
Routing Weight Updater adjusts agent
selection probabilities for task type
```

### Routing Weight System

Marvin Tower maintains a routing weight table. High-scoring agents get more task assignments; low-scoring agents are retrained or replaced.

```
Task Type: "write_python_code"
├── Agent A: score 87 → weight 0.45 (gets 45% of this task type)
├── Agent B: score 79 → weight 0.35
└── Agent C: score 61 → weight 0.20 (under review)
```

Weights update every 24 hours based on rolling 30-day performance averages.

---

## System 2 — Lesson Capture System

### The Lesson Agent (Marvin Learn)

After every completed task — success or failure — the **Lesson Agent** runs a structured post-task analysis:

#### Lesson Extraction Template

```
TASK ID: {task_id}
TASK TYPE: {task_type}
AGENT: {agent_name}
OUTCOME: SUCCESS | PARTIAL | FAILURE
COMPOSITE SCORE: {score}

WHAT WORKED:
- {observation_1}
- {observation_2}

WHAT FAILED OR COULD IMPROVE:
- {observation_1}
- {observation_2}

ROOT CAUSE (if failure):
- {root_cause}

PATTERN IDENTIFIED:
- {reusable_pattern_or_anti_pattern}

APPLICABLE TO AGENTS:
- {list_of_agents_that_should_learn_this}

CONFIDENCE: {HIGH | MEDIUM | LOW}
```

### Lesson Registry

All lessons are stored in the **Lesson Registry** — a searchable knowledge base organized by:
- Task type
- Agent
- Pattern type (success pattern / failure pattern / edge case)
- Confidence level
- Date

Before every task, relevant agents query the Lesson Registry for applicable lessons and incorporate them into their approach.

### Lesson Broadcast

High-confidence lessons (confidence = HIGH) are **broadcast to all applicable agents** via the Hermes Memory Broadcaster immediately. Lower-confidence lessons are batched and reviewed weekly.

---

## System 3 — Prompt Evolution

### How Agent Prompts Evolve

Every agent's system prompt is **versioned**. A new version is created when:
- Composite score drops below 70 for 5+ consecutive tasks of the same type
- A high-confidence lesson suggests a specific prompt improvement
- Charles explicitly requests a prompt update
- A new tool, language, or framework has been added to the swarm

### Prompt Version Schema

```
AGENT: {agent_name}
PROMPT VERSION: {major}.{minor}.{patch}
CREATED: {date}
REASON FOR UPDATE: {reason}
TRIGGERED BY: {lesson_id | feedback_id | human_request}
CHANGES FROM PREVIOUS VERSION:
  - {change_1}
  - {change_2}
PERFORMANCE IMPROVEMENT TARGET: +{X} points on {dimension}
A/B TEST STATUS: {PENDING | IN_TEST | ADOPTED | REJECTED}
```

### Prompt A/B Testing

New prompt versions are **A/B tested** before full adoption:
1. New prompt version is assigned to 20% of incoming tasks of the target type
2. Existing prompt handles the other 80%
3. After 20+ samples, if new version scores ≥ 5 points higher → adopted
4. If new version scores lower → rejected and logged as a failed attempt
5. Results inform the next iteration

### Prompt Archive

All prompt versions — adopted and rejected — are archived permanently. This allows:
- Rollback to a previous version if a new version performs poorly in production
- Analysis of what prompt strategies work and why
- Training data for the next generation of prompt engineers

---

## Self-Improvement Engine Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  SELF-IMPROVEMENT ENGINE                    │
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌───────────────┐   │
│  │   FEEDBACK   │   │    LESSON    │   │    PROMPT     │   │
│  │    LOOP      │   │   CAPTURE    │   │   EVOLUTION   │   │
│  │              │   │              │   │               │   │
│  │ Score every  │──►│ Extract what │──►│ Update agent  │   │
│  │ agent output │   │ worked/failed│   │ prompts based │   │
│  │              │   │              │   │ on lessons    │   │
│  └──────┬───────┘   └──────┬───────┘   └───────┬───────┘   │
│         │                  │                   │           │
│         ▼                  ▼                   ▼           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   KNOWLEDGE BASE                     │  │
│  │                                                      │  │
│  │  Feedback DB │ Lesson Registry │ Prompt Version DB   │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                │
│                           ▼                                │
│                  ┌─────────────────┐                       │
│                  │  ROUTING WEIGHT │                       │
│                  │    UPDATER      │                       │
│                  │                 │                       │
│                  │ Adjusts Marvin  │                       │
│                  │ Tower routing   │                       │
│                  └─────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Continuous Learning Cycle

The swarm operates on a **24-hour learning cycle**:

```
Hour 0–23: Agents execute tasks, all outputs scored in real time
Hour 23: Lesson Agent processes all completed tasks from the day
Hour 23.5: High-confidence lessons broadcast to all agents via Hermes
Hour 23.75: Routing weights updated based on 30-day rolling scores
Hour 24: Prompt A/B tests evaluated; winning versions adopted
Hour 0: New cycle begins — every agent starts smarter than yesterday
```

---

## Self-Improvement KPIs

| Metric | Target | Measurement |
|---|---|---|
| Average composite score | ≥ 80/100 | Rolling 30-day average |
| Score improvement rate | +2 points/month | Month-over-month delta |
| Lesson capture rate | 100% of tasks | Lessons logged / tasks completed |
| Prompt adoption rate | ≥ 1 upgrade/agent/month | Prompt version history |
| Human escalation rate | < 10% of tasks | Escalations / total tasks |
| Failed task recovery rate | ≥ 90% | Recovered failures / total failures |

---

## Integration with Marvin Swarm

| Marvin Agent | Self-Improvement Role |
|---|---|
| Marvin Tower | Applies routing weights; triggers escalation |
| Marvin Learn | Runs Lesson Capture after every task |
| Marvin Review | Provides peer scoring for Feedback Loop |
| All other agents | Receive updated prompts; query Lesson Registry before tasks |

---

## Next Action

Implement the Feedback Loop Scorer and connect it to Marvin Review so every completed task begins generating performance data immediately.
