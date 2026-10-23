# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


import hashlib
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from localdrop import AppServer, State, safe_filename


class LocalDropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.tmp.name) / "videoclipuri"
        cls.state = State(cls.folder, pin="123456")
        cls.server = AppServer(("127.0.0.1", 0), cls.state)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.tmp.cleanup()

    def request(self, method, path, body=None, authorized=True, mime="application/json"):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        headers = {}
        if authorized:
            headers["X-LocalDrop-Token"] = self.state.token
        if body is not None:
            headers["Content-Type"] = mime
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        raw = response.read()
        status = response.status
        conn.close()
        try:
            content = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            content = raw
        return status, content

    def post_json(self, path, data, authorized=True):
        return self.request("POST", path, json.dumps(data).encode(), authorized)

    def test_pair_and_authorization(self):
        code, _ = self.request("GET", "/api/info", authorized=False)
        self.assertEqual(code, 401)
        code, _ = self.post_json("/api/pair", {"pin": "000000"}, False)
        self.assertEqual(code, 403)
        code, data = self.post_json("/api/pair", {"pin": "123456"}, False)
        self.assertEqual(code, 200)
        self.assertEqual(data["token"], self.state.token)
        code, info = self.request("GET", "/api/info")
        self.assertEqual(code, 200)
        self.assertEqual(info["pin"], "123456")

    def test_static_assets(self):
        for resource in ["/", "/style.css", "/app.js"]:
            code, content = self.request("GET", resource, authorized=False)
            self.assertEqual(code, 200)
            self.assertGreater(len(content), 100)
        code, html = self.request("GET", "/", authorized=False)
        self.assertIn(self.state.token.encode(), html)

    def test_resume_and_complete(self):
        original = b"AAAA" + b"\x01\x02\x03" + b"end"
        meta = {"client": "a" * 32, "name": "filmare.MOV", "size": len(original), "mtime": 1234, "fingerprint": "abc12345de678901"}
        code, started = self.post_json("/api/init", meta)
        self.assertEqual(code, 200)
        identifier = started["id"]
        self.assertEqual(started["offset"], 0)
        code, progress = self.request("PUT", f"/api/upload/{identifier}?offset=0",
                                      original[:4], mime="application/octet-stream")
        self.assertEqual(code, 200)
        self.assertEqual(progress["offset"], 4)
        code, resumed = self.post_json("/api/init", {**meta, "mtime": 9999})
        self.assertEqual(code, 200)
        self.assertEqual(resumed["offset"], 4)
        code, conflict = self.request("PUT", f"/api/upload/{identifier}?offset=0",
                                      original[4:], mime="application/octet-stream")
        self.assertEqual(code, 409)
        self.assertEqual(conflict["offset"], 4)
        code, progress = self.request("PUT", f"/api/upload/{identifier}?offset=4",
                                      original[4:], mime="application/octet-stream")
        self.assertEqual(code, 200)
        self.assertEqual(progress["offset"], len(original))
        code, finished = self.request("POST", f"/api/finish/{identifier}", b"{}")
        self.assertEqual(code, 200)
        self.assertEqual((self.folder / finished["name"]).read_bytes(), original)

    def test_duplicate_filename_and_empty_file(self):
        for idx in range(2):
            meta = {"client": f"{idx + 1:032x}", "name": "filmare.MOV", "size": 0,
                    "mtime": idx, "fingerprint": "12345678abcdef01"}
            code, started = self.post_json("/api/init", meta)
            self.assertEqual(code, 200)
            code, finished = self.request("POST", f"/api/finish/{started['id']}", b"{}")
            self.assertEqual(code, 200)
            if idx == 1:
                self.assertNotEqual(finished["name"], "filmare.MOV")
            self.assertTrue((self.folder / finished["name"]).exists())

    def test_streaming_multiple_chunks(self):
        blob = b"Z" * (8 * 1024 * 1024) + b"C" * 197
        meta = {"client": "f" * 32, "name": "mare.mp4", "size": len(blob),
                "mtime": 4567, "fingerprint": "12345678abcdef01"}
        code, started = self.post_json("/api/init", meta)
        self.assertEqual(code, 200)
        upload_id = started["id"]
        chunk_size = 2 * 1024 * 1024
        chunks = [blob[i:i + chunk_size] for i in range(0, len(blob), chunk_size)]
        offset = 0
        for chunk in chunks:
            code, progress = self.request("PUT", f"/api/upload/{upload_id}?offset={offset}",
                                          chunk, mime="application/octet-stream")
            self.assertEqual(code, 200)
            offset = progress["offset"]
        code, result = self.request("POST", f"/api/finish/{upload_id}", b"{}")
        self.assertEqual(code, 200)
        final = self.folder / result["name"]
        self.assertEqual(hashlib.sha256(final.read_bytes()).hexdigest(), hashlib.sha256(blob).hexdigest())

    def test_sequential_chunks_with_connection_close(self):
        # Mirrors sequential browser PUTs across closed/reopened connections.
        meta = {"client": "9" * 32, "name": "keepalive-test.mov", "size": 9,
                "mtime": 34, "fingerprint": "34567890abcdef12"}
        _, initialized = self.post_json("/api/init", meta)
        upload_id = initialized["id"]
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=4)
        try:
            for offset, piece in [(0, b"abc"), (3, b"def"), (6, b"ghi")]:
                connection.request("PUT", f"/api/upload/{upload_id}?offset={offset}", body=piece,
                                   headers={"X-LocalDrop-Token": self.state.token})
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertTrue(response.will_close)
                data = json.loads(response.read())
                self.assertEqual(data["offset"], offset + len(piece))
        finally:
            connection.close()
        code, complete = self.request("POST", f"/api/finish/{upload_id}", b"{}")
        self.assertEqual(code, 200)
        self.assertEqual((self.folder / complete["name"]).read_bytes(), b"abcdefghi")

    def test_local_speed_benchmark_and_auth(self):
        code, _ = self.request("PUT", "/api/bench", b"X" * 4096,
                               authorized=False, mime="application/octet-stream")
        self.assertEqual(code, 401)
        body = b"z" * (2 * 1024 * 1024)
        code, data = self.request("PUT", "/api/bench", body,
                                  mime="application/octet-stream")
        self.assertEqual(code, 200)
        self.assertEqual(data["bytes"], len(body))
        self.assertGreaterEqual(data["serverReadMs"], 0)
        code, _ = self.request("PUT", "/api/bench", b"",
                               mime="application/octet-stream")
        self.assertEqual(code, 400)

    def test_chunk_reports_timings(self):
        meta = {"client": "7" * 32, "name": "diagnostic.mov", "size": 13,
                "mtime": 123, "fingerprint": "abc12345de678901"}
        code, init = self.post_json("/api/init", meta)
        self.assertEqual(code, 200)
        code, progress = self.request("PUT", f"/api/upload/{init['id']}?offset=0",
                                      b"hello world!!", mime="application/octet-stream")
        self.assertEqual(code, 200)
        for field in ("serverReadMs", "serverWriteMs", "serverSyncMs", "serverTotalMs"):
            self.assertIn(field, progress)
            self.assertGreaterEqual(progress[field], 0)
        code, result = self.request("POST", f"/api/finish/{init['id']}", b"{}")
        self.assertEqual(code, 200)
        self.assertEqual((self.folder / result["name"]).read_bytes(), b"hello world!!")

    def test_path_sanitization(self):
        self.assertEqual(safe_filename("../../inregistrare.mov"), "inregistrare.mov")
        self.assertTrue(safe_filename("CON.mov").startswith("fisier_"))


if __name__ == "__main__":
    unittest.main()
