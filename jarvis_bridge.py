"""Small ChatGPT Actions bridge to explicitly registered Jarvis HTTP adapters."""

import argparse
from dataclasses import dataclass, field
import hmac
from http.client import HTTPException
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener


MAX_REQUEST_BYTES = 65_536
MAX_RESPONSE_BYTES = 1_048_576
MAX_TASK_CHARS = 16_000
IO_TIMEOUT = 15
ID_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}")
ENV_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("Nonstandard JSON constant")


def decode_json(data):
    return json.loads(
        data.decode("utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=_invalid_constant,
    )


def read_token(name, minimum=1):
    if not isinstance(name, str) or not ENV_PATTERN.fullmatch(name):
        raise ValueError("Invalid credential environment variable name")
    value = os.environ.get(name, "")
    if len(value) < minimum or len(value) > 4096 or not all(
        33 <= ord(char) <= 126 for char in value
    ):
        raise ValueError("Missing or invalid credential environment variable")
    return value


@dataclass(frozen=True)
class Agent:
    id: str
    url: str
    token: str = field(repr=False)
    description: str = ""


def load_agents(path):
    with open(path, "rb") as source:
        raw = source.read(MAX_REQUEST_BYTES + 1)
    if len(raw) > MAX_REQUEST_BYTES:
        raise ValueError("Agent configuration is too large")
    config = decode_json(raw)
    if not isinstance(config, dict) or set(config) != {"agents"}:
        raise ValueError("Configuration must contain only agents")
    entries = config["agents"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 100:
        raise ValueError("Configure between 1 and 100 agents")
    agents = {}
    for entry in entries:
        if not isinstance(entry, dict) or not {"id", "url", "token_env"} <= entry.keys():
            raise ValueError("Each agent needs id, url and token_env")
        if entry.keys() - {"id", "url", "token_env", "description"}:
            raise ValueError("Unknown agent configuration field")
        agent_id, url = entry["id"], entry["url"]
        description = entry.get("description", "")
        if not isinstance(agent_id, str) or not ID_PATTERN.fullmatch(agent_id):
            raise ValueError("Invalid agent ID")
        if agent_id in agents:
            raise ValueError("Duplicate agent ID")
        if not isinstance(description, str) or len(description) > 500:
            raise ValueError("Description must be a string of at most 500 characters")
        description.encode("utf-8")
        if (
            not isinstance(url, str)
            or len(url) > 2048
            or not url.startswith("https://")
            or any(ord(char) <= 32 or ord(char) >= 127 for char in url)
            or "\\" in url
            or "#" in url
            or "?" in url
        ):
            raise ValueError("Agent URLs must be plain HTTPS URLs without queries or fragments")
        parsed = urlsplit(url)
        if not parsed.hostname or parsed.username is not None or parsed.password is not None:
            raise ValueError("Agent URLs must have a host and no embedded credentials")
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError("Invalid agent URL port")
        agents[agent_id] = Agent(agent_id, url, read_token(entry["token_env"]), description)
    return agents


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class UpstreamError(Exception):
    pass


def dispatch(agent, task):
    # Disable redirects and ambient proxy settings: credentials go only to the configured URL.
    opener = build_opener(
        ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context()), NoRedirect()
    )
    request = Request(
        agent.url,
        data=json.dumps({"task": task}, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + agent.token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with opener.open(request, timeout=IO_TIMEOUT) as response:
            if not 200 <= response.status < 300:
                raise UpstreamError()
            if response.headers.get_content_type() != "application/json":
                raise UpstreamError()
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise UpstreamError()
            result = decode_json(raw)
            if not isinstance(result, dict):
                raise UpstreamError()
            encoded = json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")
            if len(encoded) > MAX_RESPONSE_BYTES:
                raise UpstreamError()
            return result
    except HTTPError as error:
        error.close()
        raise UpstreamError() from None
    except (URLError, OSError, HTTPException, ValueError, RecursionError):
        raise UpstreamError() from None


def make_handler(agents, bridge_token, dispatcher=dispatch):
    expected_auth = ("Bearer " + bridge_token).encode("ascii")

    class Handler(BaseHTTPRequestHandler):
        server_version = "JarvisBridge"
        sys_version = ""
        timeout = IO_TIMEOUT

        def log_message(self, format, *args):
            # Never log task bodies, credentials, upstream URLs or exception details.
            pass

        def send_json(self, status, body):
            raw = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            self.wfile.write(raw)

        def authorized(self):
            headers = self.headers.get_all("Authorization", [])
            if len(headers) != 1 or not hmac.compare_digest(
                headers[0].encode("utf-8"), expected_auth
            ):
                self.send_json(401, {"error": "Unauthorized"})
                return False
            return True

        def do_GET(self):
            if self.path == "/health":
                self.send_json(200, {"status": "ok"})
            elif self.authorized():
                if self.path == "/v1/agents":
                    self.send_json(200, {"agents": [
                        {"id": agent.id, "description": agent.description}
                        for agent in agents.values()
                    ]})
                else:
                    self.send_json(404, {"error": "Not found"})

        def do_POST(self):
            if not self.authorized():
                return
            if self.path != "/v1/tasks":
                self.send_json(404, {"error": "Not found"})
                return
            lengths = self.headers.get_all("Content-Length", [])
            if self.headers.get("Transfer-Encoding") or len(lengths) != 1:
                self.send_json(411, {"error": "One Content-Length is required; no chunking"})
                return
            if not re.fullmatch(r"[0-9]{1,10}", lengths[0]):
                self.send_json(400, {"error": "Invalid Content-Length"})
                return
            length = int(lengths[0])
            if length > MAX_REQUEST_BYTES:
                self.send_json(413, {"error": "Request too large"})
                return
            if self.headers.get_content_type() != "application/json":
                self.send_json(415, {"error": "Use application/json"})
                return
            try:
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError()
                body = decode_json(raw)
                if not isinstance(body, dict) or set(body) != {"agent_id", "task"}:
                    raise ValueError()
                agent_id, task = body["agent_id"], body["task"]
                if not isinstance(agent_id, str) or not ID_PATTERN.fullmatch(agent_id):
                    raise ValueError()
                if not isinstance(task, str) or not task.strip() or len(task) > MAX_TASK_CHARS:
                    raise ValueError()
                # Reject lone surrogates before sending UTF-8 to the adapter.
                task.encode("utf-8")
            except (ValueError, OSError, RecursionError):
                self.send_json(400, {"error": "Expected agent_id and a nonempty task (max 16000 characters)"})
                return
            agent = agents.get(agent_id)
            if agent is None:
                self.send_json(404, {"error": "Unknown agent"})
                return
            try:
                result = dispatcher(agent, task)
            except UpstreamError:
                self.send_json(502, {"error": "Agent unavailable or invalid adapter response"})
                return
            self.send_json(200, {"agent_id": agent_id, "result": result})

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Admin-owned agent registry JSON")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        token = read_token("JARVIS_BRIDGE_TOKEN", minimum=32)
        agents = load_agents(args.config)
    except (OSError, ValueError, RecursionError):
        parser.exit(2, "Invalid configuration or missing credentials; check registry and environment.\n")
    # Deliberately loopback-only. Terminate TLS and enforce limits at a trusted reverse proxy.
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(agents, token))
    print("Jarvis bridge listening on loopback port", server.server_port, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
