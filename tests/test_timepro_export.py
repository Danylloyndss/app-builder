import csv
import io
import unittest
from unittest.mock import patch

from app.server import Handler


class TimeProExportTests(unittest.TestCase):
    def test_csv_contains_expected_columns(self):
        class DummyTimePro:
            def history(self):
                return [{"id": 1, "employee": "A", "work_date": "2026-09-17", "location": "Site", "start_time": "08:00", "pause_minutes": 30, "end_time": "17:00", "total_minutes": 510, "note": "", "has_signature": True, "attachments": [{"id": 2}]}]
        class DummyHandler: pass
        DummyHandler._send_csv = Handler._send_csv
        with patch("app.server.TIMEPRO", DummyTimePro()):
            # Exercise the method without opening a socket.
            class W:
                def __init__(self): self.headers=[]; self.body=None
                def send_response(self, s): self.status=s
                def send_header(self, k, v): self.headers.append((k,v))
                def end_headers(self): pass
                def write(self, b): self.body=b
            w=W(); obj=DummyHandler(); obj.send_response=w.send_response; obj.send_header=w.send_header; obj.end_headers=w.end_headers; obj.wfile=w
            Handler._send_csv(obj)
            rows=list(csv.reader(io.StringIO(w.body.decode("utf-8-sig"))))
            self.assertEqual(rows[0][1], "Employé")
            self.assertEqual(rows[1][1], "A")
            self.assertEqual(rows[1][8], "8h 30min")
            self.assertEqual(rows[1][10], "oui")
            self.assertEqual(rows[1][11], "1")


if __name__ == "__main__": unittest.main()
