import http.client
from http.server import ThreadingHTTPServer
from io import BytesIO
import json
from email.message import Message
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

import jarvis_bridge as bridge


TOKEN = "unit-test-only-not-a-real-secret-" + "x" * 16


class ConfigTests(unittest.TestCase):
    def load(self, entry):
        content = json.dumps({"agents": [entry]}).encode()
        with patch("builtins.open") as source, patch.dict("os.environ", {"AGENT_TOKEN": TOKEN}):
            source.return_value.__enter__.return_value.read.return_value = content
            return bridge.load_agents("unused-test-path")

    def entry(self, url="https://jarvis.example.invalid/task"):
        return {"id": "tower", "url": url, "token_env": "AGENT_TOKEN"}

    def test_https_registry(self):
        agents = self.load(self.entry())
        self.assertEqual(agents["tower"].token, TOKEN)
        self.assertNotIn(TOKEN, repr(agents["tower"]))

    def test_reject_unsafe_urls(self):
        for url in [
            "http://jarvis.example.invalid/task", "file:///etc/passwd",
            "******jarvis.example.invalid/task",
            "https:///task", "https://jarvis.example.invalid/#fragment",
            "https://jarvis.example.invalid/?credential=value",
            "https://jarvis.example.invalid/#", "https://jarvis.example.invalid:99999/",
            "https://jarvis.example.invalid/ bad", "https://jarvis.example.invalid\\evil",
        ]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.load(self.entry(url))

    def test_invalid_registry(self):
        for changes in [
            {"id": "../tower"}, {"description": 42}, {"token_env": "BAD NAME"},
            {"unknown": True}, {"description": "\ud800"},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.load(dict(self.entry(), **changes))

    def test_missing_and_weak_credentials(self):
        for value in ["", "short", "x" * 32 + "\n", "é" * 32]:
            with patch.dict("os.environ", {"JARVIS_BRIDGE_TOKEN": value}):
                with self.assertRaises(ValueError):
                    bridge.read_token("JARVIS_BRIDGE_TOKEN", 32)

    def test_strict_json(self):
        for raw in [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b"\xff"]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                bridge.decode_json(raw)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = bridge.Agent("tower", "https://jarvis.example.invalid/task", TOKEN, "Coordinator")
        cls.dispatcher = Mock(return_value={"answer": "done"})
        cls.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            bridge.make_handler({"tower": cls.agent}, TOKEN, cls.dispatcher),
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.dispatcher.reset_mock()
        self.dispatcher.side_effect = None

    def request(self, method="POST", path="/v1/tasks", body=None, auth=TOKEN, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        request_headers = {"Content-Type": "application/json"}
        if auth is not None:
            request_headers["Authorization"] = "Bearer " + auth
        request_headers.update(headers or {})
        conn.request(method, path, body=body, headers=request_headers)
        response = conn.getresponse()
        result = response.status, json.loads(response.read())
        conn.close()
        return result

    def test_health_is_minimal_and_public(self):
        self.assertEqual(self.request("GET", "/health", auth=None), (200, {"status": "ok"}))

    def test_auth_required_on_both_routes(self):
        for method, path in [("GET", "/v1/agents"), ("POST", "/v1/tasks")]:
            for auth in [None, "wrong", TOKEN + "extra"]:
                with self.subTest(path=path, auth=auth):
                    self.assertEqual(self.request(method, path, auth=auth)[0], 401)
        self.dispatcher.assert_not_called()

    def test_listing_does_not_disclose_endpoints_or_tokens(self):
        status, body = self.request("GET", "/v1/agents")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"agents": [{"id": "tower", "description": "Coordinator"}]})

    def test_registered_dispatch(self):
        status, body = self.request(body=json.dumps({"agent_id": "tower", "task": "Plan 🛰"}))
        self.assertEqual(status, 200)
        self.assertEqual(body, {"agent_id": "tower", "result": {"answer": "done"}})
        self.dispatcher.assert_called_once_with(self.agent, "Plan 🛰")

    def test_unknown_agent(self):
        self.assertEqual(self.request(body='{"agent_id":"other","task":"Plan"}')[0], 404)
        self.dispatcher.assert_not_called()

    def test_invalid_payloads(self):
        payloads = [
            "", "[]", "null", "{", '{"agent_id":"tower","task":false}',
            '{"agent_id":"tower","task":"   "}',
            '{"agent_id":42,"task":"Plan"}',
            '{"agent_id":"tower","task":"Plan","url":"https://evil.invalid"}',
            '{"agent_id":"tower","task":"Plan","task":"Again"}',
            '{"agent_id":"tower","task":"\\ud800"}',
            json.dumps({"agent_id": "tower", "task": "a" * (bridge.MAX_TASK_CHARS + 1)}),
        ]
        for body in payloads:
            with self.subTest(body=body[:80]):
                self.assertEqual(self.request(body=body)[0], 400)
        self.dispatcher.assert_not_called()

    def test_request_bound_and_media_type(self):
        self.assertEqual(self.request(body="a" * (bridge.MAX_REQUEST_BYTES + 1))[0], 413)
        self.assertEqual(self.request(body="{}", headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request(body="{}", headers={"Transfer-Encoding": "chunked"})[0], 411)
        self.assertEqual(self.request(body="{}", headers={"Content-Length": "-1"})[0], 400)
        self.dispatcher.assert_not_called()

    def test_sanitized_upstream_failure(self):
        self.dispatcher.side_effect = bridge.UpstreamError("secret details")
        status, body = self.request(body='{"agent_id":"tower","task":"Plan"}')
        self.assertEqual(status, 502)
        self.assertNotIn("secret", json.dumps(body))

    def test_unknown_routes(self):
        self.assertEqual(self.request("GET", "/v1/agents?url=evil")[0], 404)
        self.assertEqual(self.request(path="/other", body="{}")[0], 404)


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.agent = bridge.Agent("tower", "https://jarvis.example.invalid/task", TOKEN)

    def response(self, data=b'{"answer":"done"}', media_type="application/json", status=200):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.status = status
        response.headers = Message()
        response.headers["Content-Type"] = media_type
        response.read.return_value = data
        return response

    def test_upstream_contract(self):
        response = self.response()
        with patch.object(bridge, "build_opener") as builder:
            builder.return_value.open.return_value = response
            self.assertEqual(bridge.dispatch(self.agent, "Plan"), {"answer": "done"})
            request = builder.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, self.agent.url)
            self.assertEqual(request.get_header("Authorization"), "Bearer " + TOKEN)
            self.assertEqual(json.loads(request.data), {"task": "Plan"})
            self.assertEqual(builder.return_value.open.call_args.kwargs["timeout"], bridge.IO_TIMEOUT)
            response.read.assert_called_once_with(bridge.MAX_RESPONSE_BYTES + 1)
            self.assertTrue(any(isinstance(handler, bridge.NoRedirect) for handler in builder.call_args.args))

    def test_invalid_upstream_responses(self):
        for response in [
            self.response(b"[]"), self.response(b"not json"), self.response(b'{"x":NaN}'),
            self.response(b'{"x":"\\ud800"}'),
            self.response(media_type="text/html"), self.response(status=302),
            self.response(b"x" * (bridge.MAX_RESPONSE_BYTES + 1)),
        ]:
            with patch.object(bridge, "build_opener") as builder:
                builder.return_value.open.return_value = response
                with self.assertRaises(bridge.UpstreamError):
                    bridge.dispatch(self.agent, "Plan")

    def test_transport_errors_and_redirects_are_sanitized(self):
        for error in [
            URLError("private endpoint"), TimeoutError("private endpoint"),
            http.client.IncompleteRead(b"partial secret response"),
            HTTPError(self.agent.url, 302, "redirect", {}, BytesIO(b"secret")),
            HTTPError(self.agent.url, 500, "error", {}, BytesIO(b"secret")),
        ]:
            with patch.object(bridge, "build_opener") as builder:
                builder.return_value.open.side_effect = error
                with self.assertRaises(bridge.UpstreamError) as raised:
                    bridge.dispatch(self.agent, "Plan")
                self.assertEqual(str(raised.exception), "")

    def test_redirect_handler_never_creates_followup_request(self):
        handler = bridge.NoRedirect()
        for status in [301, 302, 303, 307, 308]:
            self.assertIsNone(handler.redirect_request(
                Request(self.agent.url), None, status, "redirect", {}, "https://evil.invalid"
            ))


class SchemaTests(unittest.TestCase):
    def test_schema_routes_and_security_match_bridge(self):
        from pathlib import Path
        with Path(__file__).with_name("openapi.json").open() as source:
            schema = json.load(source)
        self.assertEqual(schema["openapi"], "3.1.0")
        self.assertEqual(set(schema["paths"]), {"/v1/agents", "/v1/tasks"})
        self.assertEqual(schema["security"], [{"bridgeBearer": []}])
        self.assertTrue(schema["paths"]["/v1/tasks"]["post"]["x-openai-isConsequential"])


if __name__ == "__main__":
    unittest.main()
