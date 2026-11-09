"""Command line for the swarm hub.

  python -m swarm_hub fleet                    list every agent and its capabilities
  python -m swarm_hub selftest                 verify the registry and every playbook lesson
  python -m swarm_hub diagnose LOGFILE|-       name known problems in a CI log, with fixes
  python -m swarm_hub route CAPABILITY TEXT    show which agents a task would go to
  python -m swarm_hub learn --id ... (see -h)  teach the swarm a new failure pattern
  python -m swarm_hub prevent [REPO ...]       find known failure causes before CI runs
  python -m swarm_hub export-training [-o F]   write verified knowledge as JSONL training data
  python -m swarm_hub health                   latest default-branch CI per repo (network)
  python -m swarm_hub prs [--repo ID]          triage open PRs fleet-wide (network)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date

from .bus import Bus
from .fleet import load_fleet
from .github import GitHub, GitHubError
from .playbook import SEVERITIES, Pattern, load_playbook
from .prevent import RULES, scan_repository
from .prevent import selftest as prevent_selftest
from .training import examples, to_jsonl
from .triage import ACTIONS, triage


def _fleet(args):
    fleet = load_fleet()
    for agent in fleet:
        print(f"{agent.id:16} {agent.role:18} {', '.join(sorted(agent.capabilities))}")
    print(f"\n{len(fleet)} agents, owner {fleet.owner}")
    return 0


def _selftest(args):
    fleet, playbook = load_fleet(), load_playbook()
    problems = playbook.selftest() + prevent_selftest()
    lesson_ids = {p.id for p in playbook.patterns}
    for rule in RULES:
        if rule.prevents and rule.prevents not in lesson_ids:
            problems.append(f"{rule.id}: prevents unknown lesson {rule.prevents!r}")
    capabilities = {c for a in fleet for c in a.capabilities} | {"owner"}
    for pattern in playbook.patterns:
        if pattern.capability not in capabilities:
            problems.append(f"{pattern.id}: no agent has capability {pattern.capability!r}")
    for problem in problems:
        print(f"FAIL {problem}")
    print(f"{len(fleet)} agents, {len(playbook.patterns)} lessons, "
          f"{len(RULES)} prevention rules, {len(problems)} problems")
    return 1 if problems else 0


def _diagnose(args):
    if args.log == "-":
        text = sys.stdin.read()
    else:
        with open(args.log, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    fleet, results = load_fleet(), load_playbook().diagnose(text)
    if args.json:
        print(json.dumps([{"id": d.pattern.id, "severity": d.pattern.severity, "count": d.count,
                           "evidence": d.evidence, "diagnosis": d.pattern.diagnosis, "fix": d.pattern.fix,
                           "owners": [a.id for a in fleet.with_capability(d.pattern.capability)]
                           or [d.pattern.capability]} for d in results], indent=2))
    else:
        if not results:
            print("No known pattern matched. Once you solve it, record it with `learn` "
                  "so every agent recognises it next time.")
        for d in results:
            owners = [a.id for a in fleet.with_capability(d.pattern.capability)] or [d.pattern.capability]
            print(f"[{d.pattern.severity}] {d.pattern.id} (x{d.count})\n  evidence: {d.evidence}\n"
                  f"  why: {d.pattern.diagnosis}\n  fix: {d.pattern.fix}\n  owners: {', '.join(owners)}\n")
    return 2 if any(d.pattern.severity == "blocking" for d in results) else 0


def _route(args):
    bus = Bus(load_fleet())
    agents = bus.route(args.capability, {"task": args.text})
    if not agents:
        print(f"No agent declares capability {args.capability!r}")
        return 1
    for agent in agents:
        print(f"-> {agent.id} ({agent.full_name})")
    return 0


def _learn(args):
    playbook = load_playbook()
    playbook.learn(Pattern(args.id, args.match, args.diagnosis, args.fix, args.capability,
                           args.severity, args.example, args.learned_from or ""))
    print(f"Learned {args.id}; the playbook now has {len(playbook.patterns)} lessons")
    return 0


def _prevent(args):
    findings = []
    for root in args.repos or ["."]:
        for f in scan_repository(root):
            findings.append({"repo": root, **f.__dict__})
    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        for f in findings:
            print(f"[{f['severity']}] {f['rule']}  {f['repo']}/{f['path']}:{f['line']}\n"
                  f"  {f['evidence']}\n  why: {f['message']}\n  fix: {f['fix']}\n")
        counts = Counter(f["severity"] for f in findings)
        print(", ".join(f"{k}={counts.get(k, 0)}" for k in ("error", "warning", "info")))
    return 2 if any(f["severity"] == "error" for f in findings) else 0


def _export_training(args):
    data = to_jsonl(examples(load_playbook()))
    if args.output == "-":
        sys.stdout.write(data)
    else:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(data)
        print(f"Wrote {data.count(chr(10))} examples to {args.output}", file=sys.stderr)
    return 0


def _health(args):
    fleet, gh = load_fleet(), GitHub()
    failing = 0
    for agent in fleet:
        try:
            latest = gh.default_branch_health(fleet.owner, agent.repo)
        except GitHubError as exc:
            print(f"{agent.id:16} ERROR {exc}")
            failing += 1
            continue
        bad = {k: v for k, v in latest.items() if v in ("failure", "timed_out", "startup_failure")}
        failing += bool(bad)
        state = "no workflows" if not latest else ("FAILING " + ", ".join(bad) if bad else "ok")
        print(f"{agent.id:16} {state}")
    return 1 if failing else 0


def _prs(args):
    fleet, gh, today = load_fleet(), GitHub(), date.today()
    agents = [fleet.get(args.repo)] if args.repo else list(fleet)
    rows = []
    for agent in agents:
        try:
            pulls = gh.open_pulls(fleet.owner, agent.repo, settle_seconds=args.settle)
        except GitHubError as exc:
            print(f"{agent.id}: {exc}", file=sys.stderr)
            continue
        for pr in pulls:
            verdict = triage(pr, today)
            rows.append({"agent": agent.id, "number": pr.number, "title": pr.title, "author": pr.author,
                         "action": verdict.action, "reason": verdict.reason,
                         "url": f"https://github.com/{agent.full_name}/pull/{pr.number}"})
    rows.sort(key=lambda r: (ACTIONS.index(r["action"]), r["agent"], r["number"]))
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        for r in rows:
            print(f"{r['action']:18} {r['agent']}#{r['number']:<4} {r['title'][:70]}  ({r['reason']})")
        print("\n" + ", ".join(f"{k}={v}" for k, v in Counter(r["action"] for r in rows).items()))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="swarm_hub", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("fleet").set_defaults(func=_fleet)
    sub.add_parser("selftest").set_defaults(func=_selftest)
    p = sub.add_parser("diagnose")
    p.add_argument("log")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_diagnose)
    p = sub.add_parser("route")
    p.add_argument("capability")
    p.add_argument("text")
    p.set_defaults(func=_route)
    p = sub.add_parser("learn")
    for name in ("id", "match", "diagnosis", "fix", "capability", "example"):
        p.add_argument(f"--{name}", required=True)
    p.add_argument("--severity", choices=SEVERITIES, default="blocking")
    p.add_argument("--learned-from")
    p.set_defaults(func=_learn)
    p = sub.add_parser("prevent")
    p.add_argument("repos", nargs="*", help="repository roots (default: .)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_prevent)
    p = sub.add_parser("export-training")
    p.add_argument("-o", "--output", default="-")
    p.set_defaults(func=_export_training)
    sub.add_parser("health").set_defaults(func=_health)
    p = sub.add_parser("prs")
    p.add_argument("--repo", help="agent id from `fleet`")
    p.add_argument("--settle", type=float, default=2.0, help="seconds to wait for mergeability")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_prs)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
