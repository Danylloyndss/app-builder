"""HTTP control plane for App Builder V1 and TimePro."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import csv, hmac, io, json, os, threading, zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from .approvals import ApprovalStore
from .manager import Manager
from .timepro_api import TimeProService, TimeProValidationError
WORKSPACE="workspace"; ROOT=Path(__file__).resolve().parent; INDEX=ROOT/"static"/"index.html"; TIMEPRO_INDEX=ROOT/"static"/"timepro.html"; TIMEPRO_MANIFEST=ROOT/"static"/"timepro-manifest.json"; TIMEPRO_SW=ROOT/"static"/"timepro-sw.js"; APPROVALS=ApprovalStore(f"{WORKSPACE}/approvals.json"); RUN_LOCK=threading.Lock(); TIMEPRO=TimeProService()
class Handler(BaseHTTPRequestHandler):
    def _send(self,status,payload):
        body=json.dumps(payload,ensure_ascii=False).encode(); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(body)
    def _send_html(self,path):
        body=path.read_bytes(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(body)
    def _send_manifest(self):
        body=TIMEPRO_MANIFEST.read_bytes(); self.send_response(200); self.send_header("Content-Type","application/manifest+json"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def _send_sw(self):
        body=TIMEPRO_SW.read_bytes(); self.send_response(200); self.send_header("Content-Type","application/javascript; charset=utf-8"); self.send_header("Service-Worker-Allowed","/"); self.send_header("Cache-Control","no-cache"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def _filters(self):
        q=parse_qs(urlparse(self.path).query); return q.get("employee",[None])[0],q.get("company",[None])[0],q.get("date_from",[None])[0],q.get("date_to",[None])[0]
    def _send_csv(self):
        employee,company,date_from,date_to=self._filters(); output=io.StringIO(); writer=csv.writer(output); writer.writerow(["ID","Employé","Entreprise","Date","Lieu","Début","Pause (min)","Fin","Total (min)","Total","Recado","Signature","Pièces jointes"])
        for r in TIMEPRO.history(employee,company,date_from,date_to): writer.writerow([r["id"],r["employee"],r.get("company",""),r["work_date"],r["location"],r["start_time"],r["pause_minutes"],r["end_time"],r["total_minutes"],f'{int(r["total_minutes"])//60}h {int(r["total_minutes"])%60:02d}min',r["note"],"oui" if r.get("has_signature") else "non",len(r.get("attachments",[]))])
        body=output.getvalue().encode("utf-8-sig"); self.send_response(200); self.send_header("Content-Type","text/csv; charset=utf-8"); self.send_header("Content-Disposition","attachment; filename=timepro-feuilles.csv"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def _send_attachment(self):
        q=parse_qs(urlparse(self.path).query)
        try: aid=int(q.get("id",[None])[0])
        except (TypeError,ValueError): self._send(400,{"error":"attachment id is required"}); return
        row=TIMEPRO.db.fetch_one("SELECT filename,stored_path,mime_type FROM timesheet_attachments WHERE id=?",(aid,))
        if not row: self._send(404,{"error":"attachment not found"}); return
        path=Path(row["stored_path"]).resolve(); root=TIMEPRO.root.resolve()
        if root not in path.parents or not path.is_file(): self._send(404,{"error":"attachment not found"}); return
        body=path.read_bytes(); self.send_response(200); self.send_header("Content-Type",row["mime_type"]); self.send_header("Content-Disposition",f'inline; filename="{Path(row["filename"]).name}"'); self.send_header("X-Content-Type-Options","nosniff"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def _authorized(self):
        configured=os.environ.get("APP_BUILDER_API_KEY","").strip(); supplied=self.headers.get("X-App-Builder-Key",""); return not configured or (supplied and hmac.compare_digest(supplied,configured))
    def _status_payload(self,memory): return {"mission":memory.mission,"status":memory.status,"current_task":memory.current_task,"plan":memory.plan,"completed":memory.completed,"errors":memory.errors,"task_statuses":memory.task_statuses,"history":memory.history[-20:],"approvals":APPROVALS.list_pending()}
    def _artifact_files(self):
        root=Path(WORKSPACE); return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts) if root.exists() else []
    def _artifact_zip(self):
        root=Path(WORKSPACE); buf=io.BytesIO()
        with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
            for rel in self._artifact_files(): z.write(root/rel,arcname=rel)
        return buf.getvalue()
    def _timepro_id(self):
        try: return int(parse_qs(urlparse(self.path).query).get("id",[None])[0])
        except (TypeError,ValueError): return None
    def _read_json(self):
        length=int(self.headers.get("Content-Length","0"));
        if length>7_000_000: raise ValueError("request too large")
        return json.loads(self.rfile.read(length) or b"{}")
    def do_GET(self):
        if self.path=="/health": self._send(200,{"status":"ok","service":"app-builder-agent"}); return
        if self.path in ("/","/index.html"): self._send_html(INDEX); return
        if self.path in ("/timepro","/timepro/"): self._send_html(TIMEPRO_INDEX); return
        if self.path=="/timepro-manifest.json": self._send_manifest(); return
        if self.path=="/timepro-sw.js": self._send_sw(); return
        if self.path=="/status": self._send(200,self._status_payload(Manager(workspace=WORKSPACE).memory)); return
        if self.path=="/approvals": self._send(200,{"approvals":APPROVALS.list_pending()}); return
        if self.path=="/artifacts": self._send(200,{"files":self._artifact_files()}); return
        if self.path=="/artifacts.zip":
            body=self._artifact_zip(); self.send_response(200); self.send_header("Content-Type","application/zip"); self.send_header("Content-Disposition","attachment; filename=app-builder-artifacts.zip"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body); return
        parsed=urlparse(self.path)
        if parsed.path=="/api/timepro/export.csv": self._send_csv(); return
        if parsed.path=="/api/timepro/attachments": self._send_attachment(); return
        if parsed.path=="/api/timepro/history":
            employee,company,date_from,date_to=self._filters(); self._send(200,{"timesheets":TIMEPRO.history(employee,company,date_from,date_to)}); return
        if parsed.path=="/api/timepro/dashboard":
            employee,company,date_from,date_to=self._filters(); self._send(200,TIMEPRO.dashboard(employee,company,date_from,date_to)); return
        self._send(404,{"error":"not found"})
    def do_POST(self):
        try:
            if not self._authorized(): self._send(401,{"error":"authentication required"}); return
            data=self._read_json(); parsed=urlparse(self.path)
            if parsed.path=="/api/timepro/timesheets": self._send(201,{"timesheet":TIMEPRO.create_timesheet(data)}); return
            if parsed.path=="/api/timepro/attachments": self._send(201,{"attachment":TIMEPRO.add_attachment(data.get("timesheet_id"),data.get("filename",""),data.get("mime_type",""),data.get("content_base64",""))}); return
            if parsed.path=="/api/timepro/signature": TIMEPRO.save_signature(data.get("timesheet_id"),data.get("content_base64","")); self._send(201,{"saved":True}); return
            if parsed.path in ("/run","/resume"):
                mission=str(data.get("mission","")).strip()
                if not mission or len(mission)>20000: self._send(400,{"error":"mission is required and must be <= 20000 characters"}); return
                if not RUN_LOCK.acquire(blocking=False): self._send(409,{"error":"another build is already running"}); return
                try: memory=Manager(workspace=WORKSPACE).run(mission,resume=parsed.path=="/resume")
                finally: RUN_LOCK.release()
                self._send(200,self._status_payload(memory)); return
            if parsed.path=="/approval":
                action=str(data.get("action","")).strip(); reason=str(data.get("reason","")).strip()
                if not action or not reason: self._send(400,{"error":"action and reason are required"}); return
                request=APPROVALS.create(action,reason); self._send(201,{"approval":request.__dict__}); return
            if parsed.path=="/approval/decision":
                result=APPROVALS.decide(str(data.get("id","")),bool(data.get("approved",False)))
                if result is None: self._send(404,{"error":"approval not found"}); return
                self._send(200,{"approval":result}); return
            self._send(404,{"error":"not found"})
        except json.JSONDecodeError: self._send(400,{"error":"invalid JSON"})
        except TimeProValidationError as exc: self._send(422,{"error":str(exc)})
        except ValueError as exc: self._send(413 if str(exc)=="request too large" else 400,{"error":str(exc)})
        except (TypeError,KeyError): self._send(400,{"error":"invalid request"})
        except Exception as exc: self._send(500,{"error":str(exc)})
    def do_PUT(self):
        if not self._authorized(): self._send(401,{"error":"authentication required"}); return
        if urlparse(self.path).path!="/api/timepro/timesheets": self._send(404,{"error":"not found"}); return
        try:
            record_id=self._timepro_id()
            if record_id is None: self._send(400,{"error":"timesheet id is required"}); return
            record=TIMEPRO.update_timesheet(record_id,self._read_json())
            if not record: self._send(404,{"error":"timesheet not found"}); return
            self._send(200,{"timesheet":record})
        except json.JSONDecodeError: self._send(400,{"error":"invalid JSON"})
        except TimeProValidationError as exc: self._send(422,{"error":str(exc)})
        except ValueError as exc: self._send(413 if str(exc)=="request too large" else 400,{"error":str(exc)})
    def do_DELETE(self):
        if not self._authorized(): self._send(401,{"error":"authentication required"}); return
        if urlparse(self.path).path!="/api/timepro/timesheets": self._send(404,{"error":"not found"}); return
        try:
            record_id=self._timepro_id()
            if record_id is None: self._send(400,{"error":"timesheet id is required"}); return
            if not TIMEPRO.delete_timesheet(record_id): self._send(404,{"error":"timesheet not found"}); return
            self._send(200,{"deleted":True,"id":record_id})
        except TimeProValidationError as exc: self._send(422,{"error":str(exc)})
    def log_message(self,format,*args): return
def serve():
    port=int(os.environ.get("PORT","8080")); server=ThreadingHTTPServer(("0.0.0.0",port),Handler); print(f"App Builder V1 listening on {port}"); server.serve_forever()
if __name__=="__main__": serve()
