import http.client
import threading
import unittest
from functools import partial
from pathlib import Path

import run_viewer


class ViewerRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = Path(run_viewer.__file__).resolve().parent
        cls.server = run_viewer.ThreadingHTTPServer(
            ("127.0.0.1", 0),
            partial(run_viewer.QuietHandler, directory=str(directory)),
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request("GET", path)
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        connection.close()
        return response.status, dict(response.getheaders()), body

    def test_exp_viewer_request_redirects_and_preserves_query(self):
        status, headers, _ = self.request("/pilot_viewer.html?token=abc&viewer=exp&group=a")

        self.assertEqual(status, 302)
        self.assertEqual(headers["Location"], "/exp_viewer.html?token=abc&viewer=exp&group=a")

    def test_default_viewer_request_keeps_pilot_viewer(self):
        status, headers, body = self.request("/pilot_viewer.html?token=abc")

        self.assertEqual(status, 200)
        self.assertIn("파일럿 과제 뷰어", body)
        self.assertEqual(headers["Cache-Control"], "no-store, must-revalidate")

    def test_ping_endpoint_is_unchanged(self):
        status, _, body = self.request("/ping")

        self.assertEqual(status, 200)
        self.assertIn('"service": "pilot-runner"', body)


if __name__ == "__main__":
    unittest.main()
