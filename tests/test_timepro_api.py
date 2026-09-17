import base64
import tempfile
import unittest
from pathlib import Path
from app.timepro_api import TimeProService, TimeProValidationError, calculate_total
class TimeProApiTests(unittest.TestCase):
    def test_calculates_worked_minutes(self): self.assertEqual(calculate_total("08:00","17:00",30),510)
    def test_rejects_invalid_range(self):
        with self.assertRaises(TimeProValidationError): calculate_total("17:00","08:00",30)
    def test_create_and_history_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=TimeProService(Path(tmp)/"timepro.db"); row=service.create_timesheet({"employee":"Danyllo","work_date":"2026-09-17","location":"Neuchâtel","start_time":"08:00","pause_minutes":30,"end_time":"17:00","note":""})
            self.assertEqual(row["total_minutes"],510); history=service.history("Danyllo"); self.assertEqual(len(history),1); self.assertEqual(history[0]["location"],"Neuchâtel")
    def test_dashboard_summarizes_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=TimeProService(Path(tmp)/"timepro.db")
            for day in ("2026-09-16","2026-09-17"): service.create_timesheet({"employee":"A","work_date":day,"location":"Site","start_time":"08:00","pause_minutes":30,"end_time":"16:30"})
            dashboard=service.dashboard(); self.assertEqual(dashboard["count"],2); self.assertEqual(dashboard["total_minutes"],960); self.assertEqual(dashboard["employees"],["A"])
    def test_attachment_and_signature_are_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=TimeProService(Path(tmp)/"timepro.db"); row=service.create_timesheet({"employee":"A","work_date":"2026-09-17","start_time":"08:00","end_time":"16:00"}); raw=b"fake-png-data"; encoded=base64.b64encode(raw).decode()
            attachment=service.add_attachment(row["id"],"chantier.png","image/png",encoded); self.assertEqual(attachment["filename"],"chantier.png")
            service.save_signature(row["id"],encoded); history=service.history(); self.assertTrue(history[0]["has_signature"]); self.assertEqual(len(history[0]["attachments"]),1)
    def test_delete_timesheet_removes_related_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=TimeProService(Path(tmp)/"timepro.db"); row=service.create_timesheet({"employee":"A","work_date":"2026-09-17","start_time":"08:00","end_time":"16:00"}); encoded=base64.b64encode(b"x").decode(); service.add_attachment(row["id"],"x.png","image/png",encoded); service.save_signature(row["id"],encoded); self.assertTrue(service.delete_timesheet(row["id"])); self.assertEqual(service.history(),[])
if __name__=="__main__": unittest.main()
