import cv2,time,json,platform,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("video");p.add_argument("--output",default="cool_benchmark/results/latest.json");a=p.parse_args()
cap=cv2.VideoCapture(a.video)
if not cap.isOpened():raise SystemExit("Cannot open video")
times=[];count=0
try:
 while True:
  t=time.perf_counter();ok,f=cap.read()
  if not ok:break
  cv2.Canny(cv2.cvtColor(f,cv2.COLOR_BGR2GRAY),60,140);times.append((time.perf_counter()-t)*1000);count+=1
finally:cap.release()
times.sort();result={"status":"BASELINE_MEASURED","opencv_version":cv2.__version__,"platform":platform.platform(),"architecture":platform.machine(),"frames":count,"mean_latency_ms":sum(times)/len(times) if times else None,"p95_latency_ms":times[min(len(times)-1,int(len(times)*.95))] if times else None,"cool_status":"NOT_RUN","graviton_status":"NOT_RUN"}
Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
