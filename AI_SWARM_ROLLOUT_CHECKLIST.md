# AI Swarm Rollout Checklist

## Portfolio control plane
- [ ] Use the private **AI Jarvis Swarm Portfolio** GitHub Project as the task ledger.
- [ ] For each task, fill Business, Priority, Approval Needed, Next Action, Repository, and Status.
- [ ] Add only active, actionable issues and pull requests; do not bulk-import every historical issue.

## Assistant connections
- [ ] Connect each assistant separately to approved tools; do not assume this Hostinger Agent's GitHub authorization is shared with Hermes, ChatGPT Business, Claude Cowork, or Gemini.
- [ ] Pilot on one low-risk repository with read-only access first.
- [ ] Use a scoped MCP connector for shared tools only after reviewing its permissions.
- [ ] Store provider credentials in the provider's secure settings, never in this repository or an issue.
- [ ] Record the active provider and model in the Managed Hermes settings, without recording credentials.

## Repository rollout
- [ ] Review each repository's existing guidance before adding `AI_CONTEXT.md`.
- [ ] Use `AI_CONTEXT_TEMPLATE.md` only after filling its facts from the repository and its owner.
- [ ] Detect the actual language, package manager, and test commands before adding CI.
- [ ] Add Dependabot entries only for ecosystems and manifest locations that exist in that repository.
- [ ] Open pull requests for repository changes. Do not commit to the default branch, merge, deploy, or publish automatically.

## Review cadence
- [ ] Review the project view weekly for blocked, stale, due-soon, and approval-needed items.
- [ ] Keep business-specific context and customer data isolated.
- [ ] Expand from the pilot to additional repositories only after the permissions and validation results are reviewed.
