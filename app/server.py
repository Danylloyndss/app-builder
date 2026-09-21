"""HTTP control plane for App Builder V1 and TimePro."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import csv, hmac, io, json, os, threading, zipfile, unicodedata
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from .approvals import ApprovalStore
from .manager import JobCancelled, Manager
from .timepro_api import TimeProService, TimeProValidationError
WORKSPACE="workspace"; ROOT=Path(__file__).resolve().parent; INDEX=ROOT/"static"/"index.html"; TIMEPRO_INDEX=ROOT/"static"/"timepro.html"; TIMEPRO_MANIFEST=ROOT/"static"/"timepro-manifest.json"; TIMEPRO_SW=ROOT/"static"/"timepro-sw.js"; APPROVALS=ApprovalStore(f"{WORKSPACE}/approvals.json"); RUN_LOCK=threading.Lock(); TIMEPRO=TimeProService()

def _job_store_path():
    p=Path(WORKSPACE)/".app-builder"/"jobs.json"; p.parent.mkdir(parents=True,exist_ok=True); return p

def _load_jobs():
    p=_job_store_path()
    if not p.exists(): return []
    try: return json.loads(p.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError): return []

def _save_jobs(jobs):
    p=_job_store_path(); tmp=p.with_suffix(".tmp"); tmp.write_text(json.dumps(jobs,indent=2,ensure_ascii=False),encoding="utf-8"); tmp.replace(p)

def _enqueue_job(mission,resume=False):
    from datetime import datetime,timezone
    jobs=_load_jobs(); job={"id":os.urandom(8).hex(),"mission":mission,"resume":resume,"status":"pending","created_at":datetime.now(timezone.utc).isoformat(),"started_at":None,"finished_at":None,"error":"","attempts":0,"current_task":"","completed_count":0,"error_count":0,"cancel_requested":False,"events":[],"last_heartbeat_at":None,"diagnostics":{}}; jobs.append(job); _save_jobs(jobs); return job

def _job_event(job, event, detail=""):
    jobs=_load_jobs(); current=next((j for j in jobs if j.get("id")==job.get("id")),None)
    if not current: return
    events=current.setdefault("events",[])
    events.append({"event":event,"detail":detail})
    current["events"]=events[-100:]
    current["last_heartbeat_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    _save_jobs(jobs)

def _run_pending_jobs():
    if not RUN_LOCK.acquire(blocking=False): return
    from datetime import datetime,timezone
    try:
        jobs=_load_jobs()
        changed=False
        for stale in jobs:
            if stale.get("status")=="running":
                if stale.get("cancel_requested"):
                    stale["status"]="cancelled"; stale["error"]="Cancelled during worker restart"; stale["finished_at"]=datetime.now(timezone.utc).isoformat()
                else:
                    _recover_stale_job(stale, datetime.now(timezone.utc).isoformat())
                changed=True
        if changed: _save_jobs(jobs)
        while True:
            jobs=_load_jobs(); job=next((j for j in jobs if j.get("status")=="pending"),None)
            if not job:
                return
            job["status"]="running"; job["cancel_requested"]=False; job["started_at"]=datetime.now(timezone.utc).isoformat(); job["attempts"]=int(job.get("attempts",0))+1; job["error"]=""
            job["diagnostics"]=dict(job.get("diagnostics") or {})
            job["diagnostics"]["worker_attempt"]=job["attempts"]
            job["diagnostics"]["worker_started_at"]=job["started_at"]
            _save_jobs(jobs)
            _job_event(job,"started",job.get("mission","")[:160])
            try:
                def progress(memory, state):
                    jobs_check=_load_jobs()
                    check=next((j for j in jobs_check if j.get("id")==job["id"]),None)
                    if check and check.get("cancel_requested"):
                        raise JobCancelled("Background job cancellation requested")
                    jobs_now=_load_jobs()
                    current_now=next((j for j in jobs_now if j.get("id")==job["id"]),None)
                    if current_now:
                        current_now["current_task"]=memory.current_task
                        current_now["result_status"]=state
                        current_now["completed_count"]=len(memory.completed)
                        current_now["diagnostics"]=dict(memory.diagnostics)
                        current_now["diagnostics"]["last_worker_heartbeat"]=datetime.now(timezone.utc).isoformat()
                        current_now["error_count"]=len(memory.errors)
                        current_now["diagnostics"]=dict(memory.diagnostics)
                        if state=="waiting_for_approval":
                            approval_id = memory.diagnostics.get("approval_id")
                            if approval_id:
                                current_now["approval_id"] = approval_id
                        _save_jobs(jobs_now)
                        _job_event(current_now,"progress",f"{state}: {memory.current_task}" if memory.current_task else str(state))
                memory=Manager(workspace=WORKSPACE, progress_callback=progress).run(job["mission"],resume=bool(job.get("resume")))
                jobs=_load_jobs(); current=next((j for j in jobs if j.get("id")==job["id"]),job); current["current_task"]=memory.current_task; current["status"]="waiting_for_approval" if memory.status=="waiting_for_approval" else ("completed" if memory.status != "cancelled" else "cancelled"); current["result_status"]=memory.status; current["diagnostics"]=dict(memory.diagnostics); current["finished_at"]=datetime.now(timezone.utc).isoformat(); _save_jobs(jobs)
                _job_event(current,"finished",memory.status)
            except JobCancelled as exc:
                jobs=_load_jobs(); current=next((j for j in jobs if j.get("id")==job["id"]),job); current["status"]="cancelled"; current["error"]=str(exc); current["finished_at"]=datetime.now(timezone.utc).isoformat(); _save_jobs(jobs)
                _job_event(current,"cancelled",str(exc))
            except Exception as exc:
                jobs=_load_jobs(); current=next((j for j in jobs if j.get("id")==job["id"]),job); current["status"]="failed"; current["error"]=str(exc); current["finished_at"]=datetime.now(timezone.utc).isoformat(); _save_jobs(jobs)
                _job_event(current,"failed",str(exc))
    finally: RUN_LOCK.release()

def _recover_stale_job(job, now):
    """Make worker-recovered jobs explicitly resumable and diagnosable."""
    if job.get("status") != "running" or job.get("cancel_requested"):
        return False
    job["status"] = "pending"
    job["error"] = "Recovered after worker restart"
    job["started_at"] = None
    diagnostics = dict(job.get("diagnostics") or {})
    diagnostics["recovery_reason"] = "worker_restart"
    diagnostics["recovered_at"] = now
    diagnostics["recovery_count"] = int(diagnostics.get("recovery_count", 0)) + 1
    diagnostics["resume_eligible"] = True
    job["diagnostics"] = diagnostics
    return True

def _start_job_worker(): threading.Thread(target=_run_pending_jobs,name="app-builder-job-worker",daemon=True).start()

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
    def _send_pdf(self):
        employee,company,date_from,date_to=self._filters()
        rows=TIMEPRO.history(employee,company,date_from,date_to)
        lines=["TimePro - Feuille d'heures","Rapport exporte"]
        if employee: lines.append("Employe: "+employee)
        if company: lines.append("Entreprise: "+company)
        if date_from or date_to: lines.append("Periode: "+(date_from or "...")+" -> "+(date_to or "..."))
        lines.append("")
        lines.append(f"Feuilles: {len(rows)} | Total: {sum(int(r['total_minutes']) for r in rows)//60}h {sum(int(r['total_minutes']) for r in rows)%60:02d}")
        lines.append("")
        for r in rows:
            total=int(r["total_minutes"]); lines.append(f"{r['work_date']} | {r['employee']} | {r.get('company','')} | {r.get('location','')} | {r['start_time']}-{r['end_time']} | {total//60}h {total%60:02d}")
        lines=lines[:48]
        def clean(v):
            return unicodedata.normalize("NFKD",str(v)).encode("ascii","ignore").decode().replace("\\","\\\\").replace("(","\\(").replace(")","\\)")
        stream="BT /F1 10 Tf 42 800 Td 14 TL "+" ".join(["("+clean(line)+") Tj T* " for line in lines])+"ET"
        objects=["<< /Type /Catalog /Pages 2 0 R >>","<< /Type /Pages /Kids [3 0 R] /Count 1 >>","<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>","<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",f"<< /Length {len(stream.encode('latin-1'))} >>\\nstream\\n{stream}\\nendstream"]
        out=bytearray(b"%PDF-1.4\\n"); offsets=[0]
        for i,obj in enumerate(objects,1):
            offsets.append(len(out)); out.extend(f"{i} 0 obj\\n{obj}\\nendobj\\n".encode("latin-1"))
        xref=len(out); out.extend(f"xref\\n0 {len(objects)+1}\\n0000000000 65535 f \\n".encode())
        for off in offsets[1:]: out.extend(f"{off:010d} 00000 n \\n".encode())
        out.extend(f"trailer\\n<< /Size {len(objects)+1} /Root 1 0 R >>\\nstartxref\\n{xref}\\n%%EOF".encode())
        body=bytes(out); self.send_response(200); self.send_header("Content-Type","application/pdf"); self.send_header("Content-Disposition","attachment; filename=timepro-feuilles.pdf"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def _send_csv(self):
        employee,company,date_from,date_to=self._filters() if hasattr(self, "_filters") else (None,None,None,None); output=io.StringIO(); writer=csv.writer(output); writer.writerow(["ID","Employé","Entreprise","Date","Lieu","Début","Pause (min)","Fin","Total (min)","Total","Recado","Signature","Pièces jointes"])
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
    def _start_background(self, mission, resume=False):
        job=_enqueue_job(mission,resume); _start_job_worker(); return job
    def _status_payload(self,memory):
        from datetime import datetime,timezone
        jobs=_load_jobs()
        now=datetime.now(timezone.utc)
        enriched=[]
        for job in jobs[-20:]:
            item=dict(job)
            heartbeat=item.get("last_heartbeat_at")
            if heartbeat:
                try: item["heartbeat_age_seconds"]=max(0,int((now-datetime.fromisoformat(heartbeat)).total_seconds()))
                except (TypeError,ValueError): item["heartbeat_age_seconds"]=None
            else: item["heartbeat_age_seconds"]=None
            events=item.get("events") or []
            item["last_event"]=events[-1] if events else None
            status=item.get("status")
            if status=="waiting_for_approval":
                item["phase"]="approval"
            elif status in {"failed","cancelled","completed"}:
                item["phase"]="stopped"
            elif status=="pending":
                item["phase"]="queued"
            else:
                item["phase"]="building"
            enriched.append(item)
        return {"mission":memory.mission,"status":memory.status,"current_task":memory.current_task,"plan":memory.plan,"completed":memory.completed,"errors":memory.errors,"task_statuses":memory.task_statuses,"history":memory.history[-20:],"diagnostics":dict(memory.diagnostics),"approvals":APPROVALS.list_pending(),"jobs":enriched}
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
        if self.path=="/jobs": self._send(200,{"jobs":_load_jobs()}); return
        if self.path.startswith("/jobs/") and self.path.count("/") == 2:
            job_id=self.path.split("/",2)[2]; job=next((j for j in _load_jobs() if j.get("id")==job_id),None)
            if not job: self._send(404,{"error":"job not found"}); return
            self._send(200,{"job":job}); return
        if self.path=="/artifacts": self._send(200,{"files":self._artifact_files()}); return
        if self.path=="/artifacts.zip":
            body=self._artifact_zip(); self.send_response(200); self.send_header("Content-Type","application/zip"); self.send_header("Content-Disposition","attachment; filename=app-builder-artifacts.zip"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body); return
        parsed=urlparse(self.path)
        if parsed.path=="/api/timepro/export.csv": self._send_csv(); return
        if parsed.path=="/api/timepro/export.pdf": self._send_pdf(); return
        if parsed.path=="/api/timepro/attachments": self._send_attachment(); return
        if parsed.path=="/api/timepro/signature":
            record_id=self._timepro_id()
            if record_id is None: self._send(400,{"error":"timesheet id is required"}); return
            signature=TIMEPRO.get_signature(record_id)
            if not signature: self._send(404,{"error":"signature not found"}); return
            path=Path(signature["stored_path"]).resolve(); root=TIMEPRO.root.resolve()
            if root not in path.parents or not path.is_file(): self._send(404,{"error":"signature not found"}); return
            body=path.read_bytes(); self.send_response(200); self.send_header("Content-Type","image/png"); self.send_header("Content-Disposition","inline; filename=signature.png"); self.send_header("X-Content-Type-Options","nosniff"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body); return
        if parsed.path=="/api/timepro/timesheet":
            record_id=self._timepro_id()
            if record_id is None: self._send(400,{"error":"timesheet id is required"}); return
            row=TIMEPRO.get_timesheet(record_id)
            if not row: self._send(404,{"error":"timesheet not found"}); return
            self._send(200,{"timesheet":row}); return
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
            if parsed.path=="/api/timepro/attachments": self._send(201,{"attachment":TIMEPRO.add_attachment(data.get("timesheet_id"),data.get("filename",""),data.get("mime_type",""),data.get("content_base64", ""),data.get("client_id",""))}); return
            if parsed.path=="/api/timepro/signature": TIMEPRO.save_signature(data.get("timesheet_id"),data.get("content_base64","")); self._send(201,{"saved":True}); return
            if parsed.path=="/jobs/retry":
                job_id=str(data.get("id","")).strip(); jobs=_load_jobs(); job=next((j for j in jobs if j.get("id")==job_id),None)
                if not job: self._send(404,{"error":"job not found"}); return
                if job.get("status") not in ("failed","completed","cancelled"): self._send(409,{"error":"job is not retryable"}); return
                job["status"]="pending"; job["error"]=""; job["started_at"]=None; job["finished_at"]=None; job["cancel_requested"]=False; job["result_status"]="retry_queued"; job["last_heartbeat_at"]=None
                job["events"]=(job.get("events") or [])[-50:]
                _save_jobs(jobs); _job_event(job,"retry_queued","Retry requested"); _start_job_worker(); self._send(202,{"status":"queued","job":job}); return
            if parsed.path=="/jobs/cancel":
                job_id=str(data.get("id","")).strip(); jobs=_load_jobs(); job=next((j for j in jobs if j.get("id")==job_id),None)
                if not job: self._send(404,{"error":"job not found"}); return
                if job.get("status")=="pending":
                    job["status"]="cancelled"; job["result_status"]="cancelled"; job["finished_at"]=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
                elif job.get("status")=="running":
                    job["cancel_requested"]=True
                else:
                    self._send(409,{"error":"job is not running or pending"}); return
                _save_jobs(jobs); _job_event(job,"cancel_requested","User requested cancellation"); self._send(202,{"status":"cancellation_requested" if job.get("status")=="running" else "cancelled","job":job}); return
            if parsed.path in ("/run/background","/resume/background"):
                mission=str(data.get("mission","")).strip()
                if not mission or len(mission)>20000: self._send(400,{"error":"mission is required and must be <= 20000 characters"}); return
                job=self._start_background(mission,resume=parsed.path=="/resume/background"); self._send(202,{"status":"queued","background":True,"job":job}); return
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
                approval_id=str(data.get("id",""))
                result=APPROVALS.decide(approval_id,bool(data.get("approved",False)))
                if result is None: self._send(404,{"error":"approval not found"}); return
                resumed=False
                rejected=False
                jobs=_load_jobs()
                now=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
                for job in jobs:
                    if job.get("status")=="waiting_for_approval" and job.get("approval_id")==approval_id:
                        if result.get("status")=="approved":
                            job["status"]="pending"; job["resume"]=True; job["error"]=""; job["started_at"]=None; job["finished_at"]=None; resumed=True
                        else:
                            job["status"]="failed"; job["error"]="Human approval rejected"; job["finished_at"]=now; rejected=True
                if resumed or rejected:
                    _save_jobs(jobs)
                    if resumed: _start_job_worker()
                    for job in jobs:
                        if job.get("approval_id")==approval_id and job.get("status")=="failed":
                            _job_event(job,"approval_rejected","Human approval rejected the requested action")
                self._send(200,{"approval":result,"resumed":resumed,"rejected":rejected}); return
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
        parsed=urlparse(self.path)
        try:
            record_id=self._timepro_id()
            if parsed.path=="/api/timepro/timesheets":
                if record_id is None: self._send(400,{"error":"timesheet id is required"}); return
                if not TIMEPRO.delete_timesheet(record_id): self._send(404,{"error":"timesheet not found"}); return
                self._send(200,{"deleted":True,"id":record_id}); return
            if parsed.path=="/api/timepro/attachments":
                aid=self._timepro_id()
                if aid is None: self._send(400,{"error":"attachment id is required"}); return
                if not TIMEPRO.delete_attachment(aid): self._send(404,{"error":"attachment not found"}); return
                self._send(200,{"deleted":True,"id":aid}); return
            self._send(404,{"error":"not found"})
        except TimeProValidationError as exc: self._send(422,{"error":str(exc)})
    def log_message(self,format,*args): return
def serve():
    _start_job_worker(); port=int(os.environ.get("PORT","8080")); server=ThreadingHTTPServer(("0.0.0.0",port),Handler); print(f"App Builder V1 listening on {port}"); server.serve_forever()
if __name__=="__main__": serve()
