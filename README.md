<div align="center">

# 🛡️ CivicSentinel
### Agentic Visual Infrastructure Intelligence & Hazard Escalation Platform
**Built for the OpenCV AI Competition 2026, Powered by Amazon Web Services (AWS)**

[![OpenCV](https://img.shields.io/badge/OpenCV-5.0%20%7C%204.13-5C3EE8?logo=opencv&logoColor=white)](https://opencv.org)
[![AWS Graviton](https://img.shields.io/badge/AWS-Graviton3%20ARM64-FF9900?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/ec2/graviton/)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128.2-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18%20%7C%20TypeScript-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Tests](https://img.shields.io/badge/Pytest-26%2F26%20Passed%20(100%25)-brightgreen?logo=pytest&logoColor=white)](https://pytest.org)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

[**Devpost Submission**](https://opencv26.devpost.com) • [**Architecture**](#-system-architecture) • [**OpenCV 5 Pipeline**](#-substantive-opencv-5-vision-pipeline) • [**Agentic Vision Loop**](#-agentic-vision-orchestration) • [**AWS & COOL Benchmark**](#-cloud-optimized-vision-with-cool--aws-graviton) • [**Quickstart**](#-quick-start-guide)

---

</div>

## 📌 Executive Summary

Urban stormwater drainage networks and arterial culverts fail catastrophically during heavy precipitation when trash, debris, or localized backwaters block grates. Traditional monitoring relies on delayed citizen reports or passive CCTV cameras viewed sporadically by overloaded operators.

**CivicSentinel** transforms municipal cameras and roadside inspection streams into an **autonomous, active perception-decision-action system**. Powered by **OpenCV 5** and **AWS Graviton**, CivicSentinel detects surface water accumulation, measures drainage intake obstruction indices, evaluates visual clarity to reject degraded inputs, resolves responsible ward authorities via spatial GIS mapping, dispatches cryptographically authenticated emergency alerts via **Amazon SES**, and executes an **automated multi-tier escalation state machine** with zero human intervention required until on-site field sign-off.

---

## 🏆 Competition Tracks Addressed

| Award Track | How CivicSentinel Meets & Exceeds Requirements |
|---|---|
| **Grand Prize ($5,000)** | Complete, production-grade vision system solving critical infrastructure flood hazards with 26/26 automated tests passing, sub-millisecond execution, single-port unified deployment, and verified end-to-end incident lifecycle. |
| **Agentic Vision Award ($1,000)** | Implements a **9-step perception-decision-action loop** (`AgenticInvestigationPipeline`). OpenCV 5 outputs directly drive downstream state: water expansion velocity triggers multi-factor risk triage; edge-density obstruction dictates field dispatch urgency; blurred frames dynamically downgrade confidence to `UNKNOWN` and suspend alerts; and unacknowledged dispatches trigger automated level-by-level authority escalation. |
| **Best Use of COOL Award ($1,000)** | Fully instrumented for **Cloud-Optimized OpenCV Library (COOL)** on **AWS Graviton3 ARM64** (`c7g.xlarge`). Reproducible benchmarks demonstrate **0.46ms mean per-frame latency (>2,100 FPS)** on ARM64 NEON SIMD, delivering a **2.3x price-performance improvement** over legacy x86 EC2 instances. |

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph INGESTION ["1. Ingestion Layer"]
        CAM["Roadside CCTV / RTSP / Drone Feeds"] --> BUFFER["Safe Buffer Decode & Magic-Byte Filter"]
        UPL["Mobile Inspection Uploads (Image / Video)"] --> BUFFER
    end

    subgraph OPENCV ["2. OpenCV 5 Core Vision Pipeline"]
        BUFFER --> RGBA["RGBA to BGR Normalization"]
        RGBA --> LAP["Laplacian Blur & Quality Evaluation (σ² > 100)"]
        LAP --> HSV["HSV Color Segmentation (Water Mask)"]
        HSV --> MORPH["Morphological Opening & Closing (5x5 Rect)"]
        MORPH --> CANNY["Canny Edge & Obstruction Indexing (Grates/Debris)"]
        CANNY --> OVERLAY["Annotated Evidence Generation (Cyan / Orange Bounds)"]
    end

    subgraph AGENT ["3. Active Perception Agentic Engine"]
        OVERLAY --> SM["AgenticInvestigationPipeline State Machine"]
        SM --> OBS["OBSERVE (Water Area Proxy & Frame Delta)"]
        OBS --> QUAL["ASSESS_QUALITY (Degraded -> UNKNOWN State)"]
        QUAL --> ROI["INSPECT_ROI (Debris & Grate Occlusion)"]
        ROI --> TEMP["TEMPORAL_COMPARISON (Accumulation Velocity %/min)"]
        TEMP --> RISK["RISK_TRIAGE (LOW / MEDIUM / HIGH / CRITICAL / UNKNOWN)"]
    end

    subgraph RESOLUTION ["4. GIS & Jurisdiction Resolution"]
        RISK --> GIS["Haversine Proximity & Ward Registry Match"]
        GIS --> AUTH["Hierarchical Authority Hierarchy (L1 / L2 / L3)"]
    end

    subgraph AWS ["5. AWS Cloud & Automated Escalation Engine"]
        AUTH --> SES["Amazon SES / SMTP Token-Signed Alert Dispatch"]
        AUTH --> S3["Amazon S3 Encrypted Visual Evidence Storage"]
        AUTH --> CW["Amazon CloudWatch Telemetry & Metrics"]
        SES --> ESCAL["Lifespan Background Worker (Escalation Loop)"]
        ESCAL -->|Unacknowledged Deadline| ESCAL_UP["Promote to Level 2 (Supervisor) / Level 3 (HQ)"]
        ESCAL -->|Single-Use Token Click| HALT["Cryptographic Acknowledgment (Timer Halted)"]
    end

    subgraph FRONTEND ["6. Tactical Command Center (React 18 + TS)"]
        SM --> WS["WebSocket Real-Time Broadcast (ws://.../ws)"]
        WS --> UI["Tactical HUD (Overview, Live Stream, Twin, Incident Tracing, COOL Benchmark)"]
        HALT --> UI
        ESCAL_UP --> UI
    end
```

---

## 🔬 Substantive OpenCV 5 Vision Pipeline

CivicSentinel avoids black-box opaque models in favor of explainable, deterministic, high-throughput computer vision algorithms running on CPU/ARM:

```
INPUT FRAME (BGR)
    │
    ├─── 1. Quality & Illumination Assurance:
    │         Var(∇² f(x,y)) = (1/N) ∑ (ΔI - μ)²
    │         If Var < 100: Flag motion blur/lens smudge -> Fallback to UNKNOWN
    │
    ├─── 2. HSV Space Surface Water Extraction:
    │         H ∈ [0, 180], S ∈ [0, 110], V ∈ [0, 85]
    │         Captures specular ponding, turbid stormwater, and flooded asphalt
    │
    ├─── 3. Morphological Cleaning:
    │         Opened = (Mask ⊖ K) ⊕ K      (Eliminates noise artifacts)
    │         Closed = (Opened ⊕ K) ⊖ K    (Fills internal water voids)
    │         Structuring Element K = 5x5 Rectangular Kernel
    │
    ├─── 4. High-Frequency Intake Obstruction Estimation:
    │         Canny(I_gray, 60, 140) inside intake ROI
    │         Obstruction Index = (Edge Pixels in Intake Area) / (Total Intake Area)
    │         Detects accumulation of leaves, plastic, and stormwater debris
    │
    └─── 5. Annotated Evidence Rendering:
              Cyan contours (#00F0FF) around ponding perimeters
              Orange bounding boxes (#FF9900) highlighting intake obstruction zones
              Embeds frame timestamp, water ratio proxy, and confidence score
```

---

## 🤖 Agentic Vision Orchestration

Unlike passive vision scripts that merely dump labels into a database, CivicSentinel runs a **multi-step perception-decision-action state machine** where visual evidence iteratively alters execution:

```
[STEP 1: OBSERVE] 
   Extract water ratio proxy, candidate contour areas, and edge density.
   │
[STEP 2: ASSESS_EVIDENCE_QUALITY]
   Evaluate Laplacian variance. 
   ──> DECISION BRANCH: If clarity is degraded, downgrade visual confidence, 
       transition risk directly to UNKNOWN, pause auto-dispatch, and request human review.
   │
[STEP 3: INSPECT_ROI]
   Examine drainage intake zones for debris occlusion.
   ──> DECISION BRANCH: Obstruction detected elevated base severity by +1 tier.
   │
[STEP 4: TEMPORAL_COMPARISON]
   Compare previous frame buffer to compute accumulation velocity (% water area / min).
   ──> DECISION BRANCH: Rapid acceleration (>5%/min) elevates risk to CRITICAL.
   │
[STEP 5: RISK_TRIAGE]
   Synthesize multi-factor hysteresis score: [LOW, MEDIUM, HIGH, CRITICAL, UNKNOWN].
   │
[STEP 6: RESOLVE_LOCATION_AUTHORITY]
   Execute 4-tier location priority (Camera GPS -> Admin Coords -> Asset Registry -> Road/Ward).
   ──> DECISION BRANCH: If location unverified, set LOCATION_UNVERIFIED and halt email dispatch.
   │
[STEP 7: INCIDENT_DISPATCH & ESCALATION]
   If existing open incident: DEDUPLICATE and update telemetry without sending spam.
   If new incident: Generate cryptographically signed token (secrets.token_urlsafe(32)),
   persist deadline, and dispatch via Amazon SES to Level 1 Field Crew.
   │
[STEP 8: UPDATE_DIGITAL_TWIN]
   Synchronize spatial twin database, update telemetry, and broadcast over WebSocket.
```

---

## ⚡ Cloud-Optimized Vision with COOL & AWS Graviton

CivicSentinel is engineered for cloud economics and maximum throughput on **AWS Graviton3 ARM64** instances (`c7g.xlarge`):

### Reproducible Benchmark Results

Benchmarked on identical 640x480 resolution drainage test suites (50-frame cycles with warm-up phase):

| Architecture | Platform | Mean Latency | P95 Latency | Throughput | Relative Speedup | Cost / 1M Frames |
|---|---|---|---|---|---|---|
| **x86_64 Baseline (EC2 c6i.xlarge)** | Intel Xeon Ice Lake | 1.82 ms | 2.15 ms | 549 FPS | 1.0x (Baseline) | $0.086 |
| **ARM64 Native (EC2 c7g.xlarge)** | AWS Graviton3 NEON | 0.84 ms | 0.98 ms | 1,190 FPS | 2.17x | $0.038 |
| **ARM64 + COOL Acceleration** | AWS Graviton3 + COOL | **0.46 ms** | **0.52 ms** | **2,165 FPS** | **3.95x** | **$0.021** |

> **Key Impact**: Moving the OpenCV drainage analysis pipeline to AWS Graviton3 with COOL reduces compute costs by **75.6%** while quadrupling frame throughput, enabling a single node to monitor over **70 concurrent 30-FPS roadside cameras in real-time**.

---

## ☁️ AWS Cloud Architecture

CivicSentinel leverages native AWS services for production resilience:

- **AWS Graviton3 (Amazon ECS Fargate / EC2 c7g)**: High-efficiency ARM64 container runtime executing the OpenCV 5 / COOL vision engine.
- **Amazon Simple Email Service (SES)**: Cryptographically verified incident notifications dispatched with 1-click token acknowledgement URLs.
- **Amazon S3**: Server-side encrypted storage for annotated evidence frames and inspection video archives.
- **Amazon CloudWatch**: End-to-end telemetry, frame latency alarms, and worker health monitoring.
- **Dual Processing Mode**: Operates in full AWS Cloud mode or zero-dependency `LOCAL / MOCK` mode for offline evaluation without incurring cloud costs.

---

## 🚀 Quick Start Guide

CivicSentinel features a **single-port unified deployment**: FastAPI serves both the REST API and the compiled React 18 single-page application from `http://127.0.0.1:8000/`.

### Prerequisites
- Python 3.10+ (Python 3.11 or 3.12 recommended)
- Node.js 18+ (only needed if rebuilding the frontend from source; pre-compiled static assets are included)

---

### Option A: 1-Click Startup (macOS / Linux / AWS EC2)

```bash
git clone https://github.com/anshika-verse/CivicSentinel.git
cd CivicSentinel
chmod +x start.sh stop.sh
./start.sh
```

To stop the background server:
```bash
./stop.sh
```

---

### Option B: 1-Click Startup (Windows PowerShell / CMD)

In PowerShell (Run as Administrator or Bypass execution policy):
```powershell
git clone https://github.com/anshika-verse/CivicSentinel.git
cd CivicSentinel
Set-ExecutionPolicy -Scope Process Bypass
.\start.ps1
```
Or double-click `start.bat` in File Explorer.

To stop:
```powershell
.\stop.ps1
```

---

### Option C: Docker Compose

```bash
cd CivicSentinel/CivicSentinel_Complete_Project
docker compose up --build
```

---

## 🌐 Application Endpoints

Once started, access the complete platform at:

| Component | URL | Description |
|---|---|---|
| **Tactical Command Center** | [http://127.0.0.1:8000/](http://127.0.0.1:8000/) | Integrated React 18 HUD (Overview, Live Stream, Media Ingest, Digital Twin, Incidents, Tracing, COOL/AWS Benchmarks). |
| **Interactive OpenAPI (Swagger)** | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | Interactive endpoint explorer and schema documentation. |
| **ReDoc Documentation** | [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) | Alternative formal API documentation view. |
| **Health Diagnostics** | [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) | Real-time OpenCV version, Graviton readiness, and worker health. |
| **Real-Time WebSocket** | `ws://127.0.0.1:8000/ws` | Bi-directional streaming for live alerts, camera metrics, and job states. |

---

## 🧪 Comprehensive Automated Testing

The platform includes a 26-test comprehensive suite covering the entire vision pipeline, agentic state machine, GIS routing, AWS services, and WebSockets.

Run the test suite:
```bash
cd CivicSentinel_Complete_Project
python -m pytest -v
```

### Verified Test Results (26/26 Passed, 100%)
```text
tests/test_basic.py::test_health PASSED                                  [  3%]
tests/test_basic.py::test_ready PASSED                                   [  7%]
tests/test_basic.py::test_upload_rejects_extension PASSED                [ 11%]
tests/test_basic.py::test_proxy_metrics_bounded PASSED                   [ 15%]
tests/test_basic.py::test_two_jobs_independent PASSED                    [ 19%]
tests/test_camera_email_additive.py::test_camera_stream_url_credential_masking PASSED [ 23%]
tests/test_camera_email_additive.py::test_camera_registration_and_listing PASSED [ 26%]
tests/test_camera_email_additive.py::test_location_priority_hierarchy_no_personal_location PASSED [ 30%]
tests/test_camera_email_additive.py::test_camera_connectivity_test PASSED [ 34%]
tests/test_camera_email_additive.py::test_camera_live_sample_and_opencv_analysis PASSED [ 38%]
tests/test_camera_email_additive.py::test_unverified_location_prevents_automatic_dispatch PASSED [ 42%]
tests/test_camera_email_additive.py::test_manual_email_dispatch_and_preview PASSED [ 46%]
tests/test_civicsentinel_core.py::test_real_image_processing_and_evidence PASSED [ 50%]
tests/test_civicsentinel_core.py::test_upload_corrupt_signature PASSED   [ 53%]
tests/test_civicsentinel_core.py::test_temporal_risk_categories PASSED   [ 57%]
tests/test_civicsentinel_core.py::test_location_and_authority_resolution PASSED [ 61%]
tests/test_civicsentinel_core.py::test_haversine_distance PASSED         [ 65%]
tests/test_civicsentinel_core.py::test_incident_creation_notification_and_ack PASSED [ 69%]
tests/test_civicsentinel_core.py::test_automatic_escalation_flow PASSED  [ 73%]
tests/test_civicsentinel_core.py::test_incident_state_transitions PASSED [ 76%]
tests/test_civicsentinel_core.py::test_aws_status_reporting PASSED       [ 80%]
tests/test_civicsentinel_core.py::test_dashboard_api_endpoints PASSED    [ 84%]
tests/test_civicsentinel_core.py::test_opencv_benchmark_execution PASSED [ 88%]
tests/test_civicsentinel_core.py::test_websocket_connection PASSED       [ 92%]
tests/test_civicsentinel_core.py::test_safe_image_decoding_and_rgba PASSED [ 96%]
tests/test_civicsentinel_core.py::test_job_retry_delete_and_clear_failed PASSED [100%]

======================== 26 passed in 20.54s ========================
```

---

## ⚖️ Responsible AI & Safety Guarantees

1. **Human-in-the-Loop Decision Support**: CivicSentinel strictly issues verified alerts, priority escalations, and tactical dispatch recommendations. It **never actuates physical floodgates, sluices, or pumps automatically**.
2. **Degraded Feed Fallback**: When cameras experience optical blur, water droplets, or severe underexposure, the system transitions risk to `UNKNOWN` rather than falsely asserting safety.
3. **Zero Personal Location Tracking**: Location resolution strictly uses fixed infrastructure coordinates and municipal GIS registries. Personal browser/device GPS is never requested or logged.
4. **Credential Masking**: RTSP/ONVIF camera passwords and authentication tokens are masked via regex before ever entering logs, API responses, or JSON exports.
5. **Anti-Fatigue Deduplication**: Continuous frames of an ongoing incident update telemetry rather than generating repetitive duplicate alerts for municipal responders.

---

## 👥 Team & Submission Info

- **Competition**: [OpenCV AI Competition 2026, Powered by AWS](https://opencv26.devpost.com/)
- **Judges**: Phil Nelson (Director of Content & Creative, OpenCV), Gary Bradski (Founder, OpenCV)
- **Primary Authors**: Anshika Sharma & Saurabh Kumar Bajpai
- **Repository**: [https://github.com/anshika-verse/CivicSentinel](https://github.com/anshika-verse/CivicSentinel)

---

<div align="center">
<b>CivicSentinel — Protecting Urban Communities Through Intelligent Visual Perception.</b>
</div>
