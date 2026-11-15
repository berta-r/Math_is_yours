"""Exercise the real stdlib SLM transport against a loopback-only HTTP fixture."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from copilot.tutor import Tutor


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.response_status = 200
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                size = int(self.headers['Content-Length'])
                outer.requests.append((self.path, json.loads(self.rfile.read(size))))
                payload = json.dumps({'choices': [{'message': {'content':
                    'Subtraction compares amounts. What has been taken away?'}, 'finish_reason': 'stop'}],
                    'timings': {'prompt_n': 58, 'predicted_n': 14}}).encode()
                self.send_response(outer.response_status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.tutor = Tutor(enabled=True, port=self.server.server_port)

    def tearDown(self):
        self.tutor.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def generate(self):
        done, received = threading.Event(), []

        def completed(*args):
            received.append(args)
            done.set()

        # A broken environment proxy must not redirect board-local model calls.
        with patch.dict('os.environ', {'HTTP_PROXY': 'http://127.0.0.1:1', 'http_proxy': 'http://127.0.0.1:1',
                                       'NO_PROXY': '', 'no_proxy': ''}):
            self.tutor.generate_hint([{'role': 'user', 'content': 'Why does subtraction work?'}], completed)
            self.assertTrue(done.wait(3), 'Loopback tutor did not complete')
        self.assertEqual(len(received), 1)
        return received[0]

    def test_real_transport_sends_deterministic_bounded_generation(self):
        reply, source, timings = self.generate()
        self.assertEqual(reply, 'Subtraction compares amounts. What has been taken away?')
        self.assertEqual(source, 'local_model_generated')
        self.assertEqual(timings['prompt_n'], 58)
        self.assertEqual(len(self.requests), 1)
        path, payload = self.requests[0]
        self.assertEqual(path, '/v1/chat/completions')
        self.assertEqual(payload['temperature'], 0)
        self.assertEqual(payload['seed'], 42)
        self.assertEqual(payload['max_tokens'], 64)
        self.assertTrue(payload['cache_prompt'])
        self.assertNotIn('grammar', payload)  # This really requests prose, not a hint index.

    def test_unavailable_local_server_produces_explicit_fallback(self):
        self.response_status = 503
        reply, source, timings = self.generate()
        self.assertIsNone(reply)
        self.assertEqual(source, 'stored_unavailable')
        self.assertEqual(len(self.requests), 1)
        self.assertLess(timings['seconds'], 3)


if __name__ == '__main__':
    unittest.main()
