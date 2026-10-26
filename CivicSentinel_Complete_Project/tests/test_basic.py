
from fastapi.testclient import TestClient
from backend.app.main import app,proxy
import numpy as np
client=TestClient(app)
def test_health():
 r=client.get("/health");assert r.status_code==200 and "opencv_version" in r.json()
def test_ready():assert client.get("/ready").status_code==200
def test_upload_rejects_extension():
 r=client.post("/api/uploads",files={"file":("bad.exe",b"no","application/octet-stream")});assert r.status_code==415
def test_proxy_metrics_bounded():
 m,ann=proxy(np.zeros((80,100,3),dtype=np.uint8));assert 0<=m["water_area_ratio_proxy"]<=1 and ann.shape[0]>0
def test_two_jobs_independent():
 # malformed but signature-valid images are accepted as independent jobs, then fail with decoder diagnostics
 b=b"\x89PNG\r\n\x1a\n"+b"not-real-png"
 a=client.post("/api/uploads",files={"file":("one.png",b,"image/png")});c=client.post("/api/uploads",files={"file":("two.png",b,"image/png")})
 assert a.status_code==202 and c.status_code==202 and a.json()["job_id"]!=c.json()["job_id"]
