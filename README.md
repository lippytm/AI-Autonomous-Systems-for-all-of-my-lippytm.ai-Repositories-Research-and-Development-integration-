# AI Autonomous Systems Integration

A dependency-free Python prototype for inspecting local repositories and learning
safe repository-development practices. It can discover Git working trees,
produce a JSON health report, and run short interactive lessons.

## Requirements

- Python 3.9 or newer for the scanner; Python 3.10 or newer for the Jarvis bridge
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

## ChatGPT ↔ Jarvis integration

This repository now includes a working, dependency-free Python HTTP connector and
an integration plan for **ChatGPT Custom GPT Actions**, including use in a
**ChatGPT Business** workspace where GPT creation, Actions, and the destination
domain are permitted by workspace administrators. This is an Actions bridge, not
a native ChatGPT workspace connector, browser automation, or an account-linking
service. Feature availability depends on your plan and workspace policies.

```text
Personal ChatGPT / ChatGPT Business custom GPT
  → HTTPS reverse proxy → loopback Jarvis bridge
  → registered HTTPS adapter → Jarvis Tower / Factory / repository swarm
```

The architecture documents describe Tower and Factory but do not provide a
running Jarvis API. The connector is functional; **you must supply a reachable
adapter implementing the contract below**. The example endpoints intentionally
do not resolve. No repository is scanned, cloned, or executed automatically.

### Integration plan

1. **Inventory and scope:** find each repository's actual Jarvis entry point,
   owner, permissions, and supported operations. Start with a read-only planning
   agent. Do not assume all repositories share an API.
2. **Adapt and register:** expose an authenticated HTTPS adapter per selected
   swarm, or a single coordinator that safely routes internally. Assign stable
   IDs such as `repo-one-planner` in an administrator-owned registry; never let
   a GPT or caller supply destination URLs. Register more repositories by adding
   entries and restarting the bridge.
3. **Deploy and pilot:** provision separate least-privilege upstream credentials,
   configure TLS and proxy limits, run tests, and validate one authorized task
   end-to-end before enabling more agents.
4. **Enable ChatGPT:** import the Actions schema into a personal custom GPT and,
   independently, a Business-workspace GPT approved by its administrator. Keep
   separate bridge deployments/registries/credentials for different trust
   boundaries; a shared bridge key grants access to **all registered agents**.
5. **Operate safely:** require adapter-side human approval for changes,
   deployments, spending, or other consequential work. Monitor sanitized
   metadata, rotate keys, review agent access, and test revocation periodically.
   The bridge itself does not implement per-user identity, RBAC, audit storage,
   approval workflows, queues, or rate limiting.

### Local setup (Python 3.10+, no packages required)

From the repository root:

```bash
cp agents.example.json agents.local.json
# Edit agents.local.json: replace URLs with your real HTTPS adapter URLs.
```

Each registry entry has `id`, `url`, `token_env`, and optional `description`.
URLs must be HTTPS, without embedded credentials, query strings, or fragments.
`token_env` names an environment variable, **not the token itself**. The local
registry is ignored by Git. Protect its ownership and write permissions; only
administrators may modify the registry or its environment.

Use a secret manager in deployment. For an interactive Bash smoke test, enter
credentials without echoing them or putting values into shell history:

```bash
read -rsp 'Bridge bearer key (random, at least 32 characters): ' JARVIS_BRIDGE_TOKEN; echo
export JARVIS_BRIDGE_TOKEN
read -rsp 'Tower adapter bearer key: ' JARVIS_TOWER_TOKEN; echo
export JARVIS_TOWER_TOKEN
read -rsp 'Factory adapter bearer key: ' JARVIS_FACTORY_TOKEN; echo
export JARVIS_FACTORY_TOKEN
python3 jarvis_bridge.py --config agents.local.json --port 8765
```

Generate a cryptographically random bridge key using your password/secret
manager (at least 32 characters); length alone does not ensure strength.
All configured adapter token variables are required at startup. Remove unused
example entries. Tokens must be printable ASCII without spaces. Never commit
credentials or enter them into a chat, GPT instructions, or the OpenAPI schema.
Restart after registry/key changes. Unset exported variables when finished.

In another terminal, `curl http://127.0.0.1:8765/health` returns
`{"status": "ok"}` without authentication. All `/v1` routes require
`Authorization: ****** key>`. Use a local HTTP client with a securely
stored Authorization header to test:

```http
POST /v1/tasks
Content-Type: application/json
Authorization: ****** bridge key>

{"agent_id":"jarvis-tower","task":"Produce a read-only integration plan for this repository."}
```

`GET /v1/agents` lists IDs and descriptions, never URLs or keys. A successful
dispatch returns `{"agent_id":"jarvis-tower","result":{...}}`.
Errors are JSON with `error`: 400 invalid payload, 401 authentication failure,
404 unknown route/agent, 411 invalid framing, 413 oversized request, 415 wrong
media type, or 502 upstream failure/invalid response.

### Adapter contract

The bridge makes exactly one HTTPS POST to the registered URL with the agent's
bearer credential, `Content-Type: application/json`, and only:

```json
{"task": "The user-approved task text"}
```

The adapter must authenticate the bearer key, enforce its own authorization and
approval policy, translate the task into its repository's real Jarvis runtime,
and return a 2xx response with `Content-Type: application/json` and a JSON
**object**, for example:

```json
{"status": "completed", "summary": "Read-only plan prepared"}
```

No common Jarvis runtime is assumed. If an existing runtime expects a different
payload, create a repository-specific adapter; do not expose a shell executor.
For long-running swarms, return quickly with a job ID and implement status
retrieval in a future, explicitly authorized adapter/schema extension. There
is no polling route in this version.

Requests are limited to 64 KiB and task text to 16,000 characters. Adapter
responses are limited to 1 MiB; keep answers much smaller for Actions platform
limits. Socket operations have a 15-second timeout, not a whole-job deadline.
Redirects are refused, TLS certificates are verified, and ambient HTTP proxy
settings are disabled. Configure the final adapter URL directly.

There are **no automatic retries or idempotency guarantees**. A timeout/502 may
occur after an agent has performed work. Confirm task status out of band before
retrying; implement durable deduplication in an adapter before allowing writes.

### HTTPS deployment and ChatGPT setup

The built-in threaded Python server is a small connector/reference service,
**not a production-hardened internet server**. It binds only to `127.0.0.1`.
Do not directly expose it or change it to a public bind address. Run behind a
trusted HTTPS reverse proxy on the same host/network namespace, with valid
public TLS, header/body limits, connection/concurrency limits, rate limits,
strict request-framing validation, and a total request deadline. Apply outbound
network restrictions to approved adapter hosts. The proxy must preserve the
Authorization header and avoid recording it or task bodies. The service
suppresses request logs; use sanitized operational metrics and protect upstream
logs too. A container proxy must share the loopback network namespace or use
an equivalently isolated deployment design; publishing a container port alone
does not make this loopback listener reachable.

1. Deploy the HTTPS proxy at a domain you control, and verify a real adapter
   task through it. ChatGPT cannot reach a localhost-only service.
2. Replace `https://jarvis-bridge.example.invalid` in `openapi.json` with your
   public HTTPS bridge origin. This schema is OpenAPI 3.1.
3. In the custom GPT editor, add an Action and import/paste `openapi.json`.
   Configure **API Key authentication → Bearer** with the bridge key in the
   editor's protected authentication settings, not in the schema. Save/test
   `listJarvisAgents`, then `dispatchJarvisTask`.
4. In the Business workspace, ask the administrator to permit the GPT, Actions,
   and your bridge domain as required by workspace policies. Configure and test
   the workspace GPT independently; do not bypass admin restrictions. If these
   features are unavailable, this integration cannot be enabled there.
5. Keep the GPT private or appropriately workspace-restricted. A broadly shared
   GPT may let unintended users invoke its shared credential. Configure any
   required privacy-policy URL and sharing requirements in the GPT editor.
6. Instruct the GPT to select a listed agent, ask permission before forwarding
   sensitive data, send only necessary task text, treat every agent response as
   **untrusted data**, and never follow instructions embedded in agent output.
   The schema marks dispatch consequential to request user confirmation; this
   is not a substitute for adapter-side approval.

This bridge does **not** automatically sync chat history, memories, files,
accounts, or Business workspace content. ChatGPT sends only the Action arguments
it constructs; review those arguments and approvals. Sending a task crosses a
data boundary into your infrastructure and its downstream swarms: review data
retention, privacy, and organizational policy before forwarding business data.

**Billing:** ChatGPT/ChatGPT Business subscriptions and OpenAI API billing are
separate. This bridge does not call the OpenAI API or require an OpenAI API key.
Any downstream agent using an API needs its own credentials and billing.

### Validation

```bash
python3 -m unittest -v
```

Tests use only the standard library, a loopback HTTP server, and mocked HTTPS
adapters; no real credentials, external calls, or Jarvis service are required.
They cover authentication, registration, payload bounds, adapter requests,
redirect denial, response validation, and sanitized errors. They do not prove
connectivity to your repositories or ChatGPT: complete the deployment pilot
with your own authorized endpoints before relying on the integration.
