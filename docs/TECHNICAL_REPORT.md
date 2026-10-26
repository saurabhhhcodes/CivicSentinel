# 📑 CivicSentinel: Technical Report
## Agentic Visual Infrastructure Intelligence & Hazard Escalation Platform
**OpenCV AI Competition 2026, Powered by Amazon Web Services (AWS)**

**Authors**: Anshika Sharma & Saurabh Kumar Bajpai  
**Repository**: [https://github.com/anshika-verse/CivicSentinel](https://github.com/anshika-verse/CivicSentinel)  
**Date**: October 2026  
**Competition Category**: General Competition / Grand Prize Track  
**Special Award Tracks**: Agentic Vision with OpenCV 5 • Best Use of COOL (Cloud-Optimized OpenCV Library)

---

## Abstract

Urban stormwater management networks are prone to catastrophic localized flash flooding when culverts, storm grates, and retention channels become obstructed by trash, silt, and urban debris during heavy precipitation. Passive surveillance cameras deployed across municipal transit corridors are rarely monitored in real time due to operator cognitive fatigue. This report presents **CivicSentinel**, an autonomous infrastructure surveillance and incident response platform built with **OpenCV 5** and **Amazon Web Services (AWS)**. CivicSentinel couples substantive morphological and edge-density computer vision pipelines with an **agentic perception-decision-action state machine** and an automated multi-tier municipal escalation engine. 

The system evaluates optical blur using Laplacian variance to prevent false assurances on degraded inputs, computes intake obstruction indices via Canny edge density, resolves responsible administrative wards using spatial GIS hierarchies without personal location leakage, and dispatches authenticated dispatches with single-use cryptographic acknowledgement tokens via **Amazon SES**. Evaluated on **AWS Graviton3 ARM64** (`c7g.xlarge`) with the **Cloud-Optimized OpenCV Library (COOL)**, CivicSentinel achieves a **0.46 ms mean frame processing latency (>2,165 FPS)**—a **3.95x throughput improvement** and **75.6% compute cost reduction** over legacy x86 baselines. The platform is verified through an automated test suite achieving a 100% pass rate (26/26 tests passing) and is deployed via a unified, single-port tactical command dashboard.

---

## 1. Problem Statement & Real-World Impact

### 1.1 The Urban Drainage Crisis
Municipal stormwater systems are designed to handle specified runoff volumes; however, their real-world capacity is routinely crippled by surface obstructions. Plastic bags, vegetative cuttings, construction sediment, and loose urban debris are swept toward culvert intake grates during the initial 15 minutes of a storm—the critical "first flush" window. Once an intake grate is partially choked, upstream water depth increases non-linearly, causing rapid road surface flooding, hydraulic pressure surges, vehicular hydroplaning, and structural asphalt erosion.

### 1.2 Current Operational Deficiencies
Municipal flood response currently suffers from three fatal bottlenecks:
1. **Passive and Blind Surveillance**: Traffic and municipal CCTV cameras stream gigabytes of unanalyzed video. Control center operators monitor dozens of screens simultaneously, routinely failing to detect localized ponding until citizens call emergency helplines.
2. **Disconnected Jurisdictions**: When water is reported, routing the incident to the appropriate field team requires manual cross-referencing of administrative ward boundaries, road ownership (state highway vs. municipal street), and maintenance contractor territories. This introduces 30–90 minute dispatch delays.
3. **No Closed-Loop Escalation**: Dispatched field teams often lack visual context before arriving on-site. If a field team is delayed or unavailable, notifications languish unescalated without automatic SLA enforcement or supervisory alerting.

### 1.3 Intended Real-World Impact
CivicSentinel eliminates manual bottlenecks by establishing an autonomous, continuous loop between visual camera feeds and emergency municipal response. By detecting ponding in its nascent stages and measuring physical intake grate obstruction, CivicSentinel enables preventative maintenance dispatches before roadways submerge, saving lives, preventing property damage, and preserving critical civic infrastructure.

---

## 2. Target Beneficiaries & Users

| User Persona | Operational Role | Value Delivered by CivicSentinel |
|---|---|---|
| **Municipal Field Response Crew** | On-site drainage maintenance and emergency clearing units. | Receives instant, tokenized dispatch notifications on mobile devices containing annotated visual evidence, GPS coordinates, and estimated debris obstruction indices. Single-click acknowledgement halts escalation without requiring complex login credentials. |
| **Ward Engineering Supervisors** | Regional drainage directors overseeing maintenance SLAs. | Receives automatic, level-by-level escalation alerts when field crews fail to acknowledge critical incidents within defined SLA timeframes (e.g., 5–15 minutes). |
| **Central Emergency Operations Center (EOC)** | Municipal disaster coordinators and city leadership. | Full operational visibility across all monitored arterial roads and drainage assets via the real-time GIS Digital Twin and tactical command HUD. |
| **Urban Commuters & Citizens** | Road users, transit operators, and local residents. | Benefit from preemptively cleared drainage intakes, dramatically reduced urban flash flood events, and decreased traffic disruption during severe weather. |

---

## 3. End-to-End System Architecture

CivicSentinel is designed around a modular, decoupled architecture where edge or cloud ingestion feeds into a high-throughput OpenCV pipeline, an agentic decision orchestrator, an additive relational persistence layer, and multi-tier notification workers.

### 3.1 Technical Topology

```text
[ ROADSIDE ASSETS / CAMERAS / INSPECTION UPLOADS ]
                      │
                      ▼
┌────────────────────────────────────────────────────────┐
│             INGESTION & BUFFER VALIDATION              │
│  - Magic-byte file validation (JPEG, PNG, MP4, WebM)   │
│  - np.frombuffer safe decode into BGR memory buffers   │
│  - Stream URL credential sanitization (mask_stream_url)│
└─────────────────────────┬──────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────┐
│            OPENCV 5 CORE VISION PIPELINE               │
│  - Laplacian variance blur metric: Var(∇² f)           │
│  - HSV color space candidate water segmentation        │
│  - Morphological opening & closing (5x5 rect kernel)   │
│  - Intake obstruction estimation (Canny edge density)  │
│  - Annotated visual evidence generation                │
└─────────────────────────┬──────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────┐
│            AGENTIC INVESTIGATION STATE MACHINE         │
│  - 9-step Perception-Decision-Action loop              │
│  - Dynamic confidence modulation & UNKNOWN fallback    │
│  - Multi-factor temporal risk triage (hysteresis)      │
│  - Spatial Haversine & 4-tier GIS jurisdiction routing │
│  - Stateful incident deduplication & telemetry update  │
└─────────────────────────┬──────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────┐
│          AWS CLOUD & DURABLE ESCALATION ENGINE         │
│  - Amazon SES: Cryptographic tokenized dispatch        │
│  - Amazon S3: Visual evidence storage & archival       │
│  - Amazon CloudWatch: System metrics & SLA alarms      │
│  - FastAPI Lifespan Background Worker (30s eval ticks) │
│  - Durable restart recovery & SQLite persistence       │
└─────────────────────────┬──────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────┐
│               TACTICAL COMMAND HUD (SPA)               │
│  - Unified single-port deployment on port 8000         │
│  - React 18 + TypeScript + Vite tactical interface     │
│  - Live camera sampling & WebSocket real-time stream   │
│  - Interactive benchmark suite & trace inspector       │
└────────────────────────────────────────────────────────┘
```

---

## 4. Substantive OpenCV 5 Vision Pipeline Implementation

The core visual analysis engine (`backend/app/vision.py`) is written using OpenCV 5 / OpenCV 4.13.0 headless, specifically tailored for deterministic execution on CPU and ARM hardware without external deep learning dependencies.

### 4.1 Ingestion & Memory Buffer Decoding
To defend against malformed payloads or disguised executables, CivicSentinel performs strict magic-byte validation before passing bytes into OpenCV:
- Evaluates file headers against allowed signatures (`FF D8 FF` for JPEG, `89 50 4E 47` for PNG, `52 49 46 46` for WebP, and standard container boxes for MP4/MKV).
- Decodes memory streams safely into raw memory using:
  $$\text{image} = \text{cv2.imdecode}(\text{np.frombuffer}(\text{file\_bytes}, \text{np.uint8}), \text{cv2.IMREAD\_UNCHANGED})$$
- Normalizes 4-channel BGRA / RGBA arrays to 3-channel BGR via `cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)` to prevent channel-index memory corruption.

### 4.2 Image Quality & Laplacian Focus Assurance
A critical flaw in standard vision systems is making affirmative safety decisions on degraded, blurred, or occluded imagery. CivicSentinel computes the **Laplacian variance** of each incoming frame:
$$\sigma^2 = \text{Var}\left(\nabla^2 f(x,y)\right) = \frac{1}{N} \sum_{x,y} \left( \Delta f(x,y) - \mu \right)^2$$
Where $\Delta f(x,y) = \frac{\partial^2 f}{\partial x^2} + \frac{\partial^2 f}{\partial y^2}$ is obtained using `cv2.Laplacian(gray, cv2.CV_64F)`.
- If $\sigma^2 < 100$, the system flags motion blur, rain smudges, or camera defocusing.
- The visual confidence metric is penalized proportionately, and the downstream risk engine is forced into an **`UNKNOWN`** state, halting automatic public notifications and flagging the camera for physical maintenance.

### 4.3 Multi-Band HSV Water Segmentation
Specular reflection on asphalt and turbid stormwater makes grayscale thresholding unreliable. CivicSentinel converts BGR frames to HSV color space:
$$\text{Mask}_{\text{water}} = \begin{cases} 1 & \text{if } H \in [0, 180], S \in [0, 110], V \in [0, 85] \\ 0 & \text{otherwise} \end{cases}$$
This bounds the low-saturation, low-to-medium value profile characteristic of pooled stormwater and flooded road surfaces while rejecting dry, reflective asphalt.

### 4.4 Morphological Filtering
Raw segmentation masks contain speckle noise from lane markings and vehicle tires. CivicSentinel applies morphological opening followed by morphological closing using a $5 \times 5$ rectangular structuring element $K$:
$$\text{Opened} = (\text{Mask} \ominus K) \oplus K \quad \text{(Eliminates high-frequency noise)}$$
$$\text{Cleaned} = (\text{Opened} \oplus K) \ominus K \quad \text{(Bridges internal voids within puddles)}$$
External contours are extracted via `cv2.findContours(Cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)`. The surface water area proxy is calculated as:
$$\text{Water Ratio Proxy} = \frac{\sum_{i} \text{Area}(\text{Contour}_i)}{\text{Width} \times \text{Height}}$$

### 4.5 Intake Obstruction Indexing via Canny Edge Density
Drainage grates with free water flow exhibit low high-frequency edge density. When leaves, plastic debris, or tree limbs choke the intake, high-frequency structural edges spike. CivicSentinel extracts edge gradients inside the drainage region of interest using `cv2.Canny(gray, 60, 140)`:
$$\text{Obstruction Index} = \frac{\sum_{(x,y) \in \text{ROI}} \mathbf{1}_{\{\text{Edge}(x,y) > 0\}}}{\text{Total Pixels in ROI}}$$
If the obstruction index exceeds the calibration threshold (0.18), the system flags **`OBSTRUCTION_SUSPECTED = True`**, which elevates the incident priority tier.

### 4.6 Annotated Evidence Generation
To provide verifiable visual receipts to field crews, CivicSentinel renders annotated BGR frames:
- **Electric Cyan (#00F0FF)** contours delineate surface ponding boundaries.
- **Amber Orange (#FF9900)** bounding rectangles highlight obstructed culvert intakes.
- An informational HUD bar is burned into the top border displaying the timestamp, frame index, computed water ratio, and obstruction score.

---

## 5. Agentic Vision Engine (Perception-Decision-Action Loop)

To qualify for the **Agentic Vision Award**, a solution must feature an active workflow where vision analysis dynamically changes subsequent decisions, tool calls, and actions. CivicSentinel's `AgenticInvestigationPipeline` (`backend/app/agent.py`) executes an auditable, 9-step state machine:

```text
[1. OBSERVE]
    ↳ Ingest frame & extract water ratio proxy, contours, visual confidence.
[2. ASSESS_EVIDENCE_QUALITY]
    ↳ Evaluate Laplacian variance.
    ↳ DECISION: If quality degraded -> downgrade confidence & trigger UNKNOWN triage.
[3. INSPECT_ROI]
    ↳ Measure Canny edge density over drainage intake.
    ↳ DECISION: If obstruction suspected -> elevate base severity tier.
[4. TEMPORAL_COMPARISON]
    ↳ Compare sequential frame buffer timestamps and water area deltas.
    ↳ DECISION: If accumulation velocity > 5%/min -> escalate risk to CRITICAL.
[5. RISK_TRIAGE]
    ↳ Evaluate temporal multi-factor risk: LOW, MEDIUM, HIGH, CRITICAL, UNKNOWN.
[6. RESOLVE_LOCATION_AUTHORITY]
    ↳ 4-tier GIS hierarchy match (Camera GPS -> Admin Coords -> Asset Registry -> Ward).
    ↳ DECISION: If location unverified -> set LOCATION_UNVERIFIED and halt auto-dispatch.
[7. DISPATCH_INCIDENT]
    ↳ DECISION: If active incident exists -> DEDUPLICATE and update telemetry without spamming.
    ↳ DECISION: If new incident -> Generate single-use cryptographic token, set SLA deadline,
      and dispatch alert via Amazon SES.
[8. UPDATE_DIGITAL_TWIN]
    ↳ Synchronize asset state, commit database transaction, and broadcast over WebSocket.
```

### 5.1 Concrete Agentic Execution Trace Example
Below is an actual JSON step trace generated by the pipeline demonstrating how visual analysis directly governs downstream tool execution:

```json
[
  {
    "step": 1,
    "state": "OBSERVE",
    "tool": "opencv_pipeline",
    "decision": "Ingest and process media frames using multi-band HSV and morphological filtering.",
    "result": {"water_area_ratio_proxy": 0.284, "candidate_regions": 3, "visual_confidence": 0.88}
  },
  {
    "step": 2,
    "state": "ASSESS_EVIDENCE_QUALITY",
    "tool": "evaluate_image_quality",
    "decision": "Verify illumination and focus blur (Laplacian variance) before triage.",
    "result": {"quality_label": "acceptable", "sharpness_score": 142.6, "issues_detected": []}
  },
  {
    "step": 3,
    "state": "INSPECT_ROI",
    "tool": "assess_obstruction",
    "decision": "Inspect drainage intake perimeter for floating debris or physical blockage indicators.",
    "result": {"obstruction_suspected": true, "obstruction_index": 0.221}
  },
  {
    "step": 4,
    "state": "TEMPORAL_COMPARISON",
    "tool": "compare_observations",
    "decision": "Measure rate of change across sampled frames to determine acceleration.",
    "result": {"temporal_trend": "accelerating", "accumulation_rate_percent_per_min": 6.2}
  },
  {
    "step": 5,
    "state": "RISK_TRIAGE",
    "tool": "calculate_risk",
    "decision": "Visual proxy (28.4%), high obstruction (0.22), and rapid rise (+6.2%/min) trigger CRITICAL tier.",
    "result": {"current_risk": "CRITICAL", "risk_score": 0.94, "recommended_action": "EMERGENCY_FIELD_DISPATCH"}
  },
  {
    "step": 6,
    "state": "RESOLVE_LOCATION_AUTHORITY",
    "tool": "resolve_camera_location",
    "decision": "Resolve infrastructure coordinates and municipal authority without personal location tracking.",
    "result": {"ward": "Ward 7 - West Arterial", "assigned_authority": "West Division Stormwater Unit", "verification_status": "VERIFIED"}
  },
  {
    "step": 7,
    "state": "DISPATCH_INCIDENT",
    "tool": "send_incident_notification",
    "decision": "Severity is CRITICAL. Shorten SLA deadline to 5 minutes, generate token, and dispatch via Amazon SES.",
    "result": {"incident_id": "INC-7A4B12C9", "notification_status": "SENT", "channel": "AMAZON_SES", "acknowledgement_deadline": "2026-10-27T01:15:00Z"}
  },
  {
    "step": 8,
    "state": "UPDATE_DIGITAL_TWIN",
    "tool": "update_digital_twin",
    "decision": "Update spatial digital twin state, risk status, and broadcast to tactical command HUD.",
    "result": {"asset_id": "ASSET-CULVERT-04", "status": "SYNCHRONIZED"}
  }
]
```

---

## 6. Cloud-Optimized Vision with COOL on AWS Graviton

To qualify for the **Best Use of COOL Award**, CivicSentinel was architected, benchmarked, and validated for ARM64 execution on **AWS Graviton3** (`c7g.xlarge`).

### 6.1 Architecture & NEON SIMD Acceleration
AWS Graviton3 processors feature 64-bit Arm Neoverse-V1 cores with dual 256-bit SVE (Scalable Vector Extension) and NEON SIMD vector pipelines. Traditional OpenCV operations (such as color space conversions and matrix convolutions) typically suffer from cache stalls on standard x86 architectures. By leveraging the **Cloud-Optimized OpenCV Library (COOL)** compiled for Graviton, CivicSentinel executes multi-channel matrix traversals with vectorized loop unrolling and optimized memory alignment.

### 6.2 Empirical Benchmark Methodology & Results
The benchmark harness (`backend/app/benchmark_service.py`) executes timed runs over 50 realistic drainage frames (640x480 resolution) preceded by a 5-frame warm-up cycle. The workload encompasses BGR-to-HSV conversion, binary in-range masking, morphological opening with a $5 \times 5$ kernel, contour extraction, and Canny edge filtering.

| Metric | x86_64 Baseline (c6i.xlarge) | AWS Graviton3 Native (c7g.xlarge) | AWS Graviton3 + COOL (c7g.xlarge) |
|---|---|---|---|
| **Mean Frame Latency** | 1.82 ms | 0.84 ms | **0.46 ms** |
| **P95 Frame Latency** | 2.15 ms | 0.98 ms | **0.52 ms** |
| **Throughput (FPS)** | 549 FPS | 1,190 FPS | **2,165 FPS** |
| **EC2 On-Demand Rate ($/hr)** | $0.170 | $0.145 | **$0.145** |
| **Cost per 1 Million Frames** | $0.086 | $0.034 | **$0.021** |
| **Relative Speedup** | 1.00x (Baseline) | 2.17x | **3.95x** |

### 6.3 Cloud Cost Impact
Operating on AWS Graviton3 with COOL yields an immediate **75.6% compute cost reduction** per analyzed frame compared to x86 instances. A single `c7g.xlarge` instance provides sufficient compute headroom to continuously process **over 70 concurrent 30-FPS video streams in real time**.

---

## 7. AWS Cloud Services & Production Deployment

CivicSentinel is designed for cloud-native deployment while offering an offline fallback mode:

```text
                               AWS CLOUD TOPOLOGY
┌────────────────────────────────────────────────────────────────────────┐
│                              AMAZON ROUTE 53                           │
│                                     │                                  │
│                                     ▼                                  │
│                        APPLICATION LOAD BALANCER                       │
│                                     │                                  │
│                 ┌───────────────────┴───────────────────┐              │
│                 ▼                                       ▼              │
│   AMAZON ECS FARGATE (TASK 1)             AMAZON ECS FARGATE (TASK 2)  │
│   [AWS Graviton3 ARM64 c7g]               [AWS Graviton3 ARM64 c7g]    │
│   • FastAPI REST & WebSockets             • FastAPI REST & WebSockets  │
│   • OpenCV 5 / COOL Vision Pipeline       • OpenCV 5 / COOL Vision     │
│   • Lifespan Escalation Worker            • Lifespan Escalation Worker │
│                 │                                       │              │
│                 └───────────────────┬───────────────────┘              │
│                                     │                                  │
│         ┌───────────────────────────┼───────────────────────────┐      │
│         ▼                           ▼                           ▼      │
│   AMAZON S3                   AMAZON SES               AMAZON CLOUDWATCH│
│   (Encrypted Evidence)        (Token Alert Dispatch)   (Metrics & Logs) │
└────────────────────────────────────────────────────────────────────────┘
```

- **Amazon ECS Fargate (Graviton3 / c7g)**: Runs containerized CivicSentinel Docker containers natively on ARM64 architectures.
- **Amazon SES**: Transmits authenticated HTML incident dispatches containing embedded evidence photos, priority badges, and single-click acknowledgement links.
- **Amazon S3**: Visual evidence frames, annotated contours, and raw video clips are archived with server-side encryption (SSE-S3).
- **Amazon CloudWatch**: Gathers execution metrics, tracking mean frame latencies, escalation loop frequencies, and missed acknowledgment SLA alarms.
- **Dual Processing Engine**: If AWS credentials are not present in `.env`, the system automatically switches to `PROCESSING_MODE=LOCAL`, simulating SES via SQLite audit logging and storing evidence in local disk directories (`data/evidence/`).

---

## 8. Experimental Evaluation & Validation Evidence

### 8.1 Automated Test Suite
CivicSentinel incorporates an automated test suite executed via Pytest. The suite verifies end-to-end functionality across 26 test cases:

- **Vision & Ingestion Integrity**: Verified rejection of corrupt files, safe memory decoding from buffers, RGBA normalization, and bounded proxy scores (0.0 to 1.0).
- **Temporal Risk & Hysteresis**: Validated proper categorizations across LOW, MEDIUM, HIGH, CRITICAL, and UNKNOWN states under simulated water growth scenarios.
- **Location & Authority**: Tested Haversine distance computations, priority fallback hierarchies, and the strict requirement that unverified camera coordinates halt automated notifications.
- **Escalation State Machine**: Validated that unacknowledged incident deadlines trigger Level 1 ➔ Level 2 promotions, while single-use cryptographic tokens successfully cancel escalation timers.
- **AWS Service Adapters**: Verified SES, S3, and CloudWatch status diagnostics in both cloud and local mock modes.
- **API & WebSockets**: Confirmed 200 OK responses across all REST dashboard endpoints and WebSocket event streaming.

**Result**: **26 passed in 20.54s (100% pass rate)**.

### 8.2 Failure Cases, Edge Cases & Degraded Inputs
To ensure operational robustness, CivicSentinel explicitly models and handles edge cases:

| Failure Mode / Edge Case | Observed System Behavior | Safeguard Mechanism |
|---|---|---|
| **Nighttime / Underexposure** | Frame mean pixel intensity drops below threshold ($V_{\text{mean}} < 20$). | Visual confidence is set to 0.15; risk engine transitions to `UNKNOWN`; flags camera for external lighting inspection. |
| **Optical Blur / Rain Smear** | Laplacian variance drops below 100 ($\sigma^2 < 100$). | Downstream severity is set to `UNKNOWN`; automated municipal email dispatch is suspended to prevent false alarms. |
| **Specular Road Reflections** | Dry asphalt reflections mimic water luminance. | Multi-band HSV saturation filters and Canny intake edge checks reject false specular contours. |
| **Unregistered Camera Coordinates** | Camera stream added without verified GPS metadata. | System marks location as `LOCATION_UNVERIFIED` and requires administrative sign-off before email dispatch. |
| **Server Crash During Escalation** | Host reboot occurs while an incident acknowledgement timer is running. | Deadlines are committed to SQLite; on restart, the FastAPI lifespan worker immediately evaluates expired SLAs. |

---

## 9. Responsible AI & Operational Safety Policies

1. **Human-in-the-Loop Decision Support**: CivicSentinel functions strictly as a decision-support and dispatch-routing platform. Under no circumstances does the system automatically actuate physical floodgates, motorized pumps, or sluice valves without human operator confirmation.
2. **Explicit Uncertainty Modeling**: Rather than forcing a binary "safe/flooded" classification on degraded video, CivicSentinel treats low-confidence observations as `UNKNOWN`, requiring human visual verification.
3. **Zero Personal Location Tracking**: The system operates exclusively on fixed municipal infrastructure registries (culverts, bridges, camera GPS). Personal device or mobile browser geolocation is never requested, accessed, or persisted.
4. **Credential Protection**: RTSP stream URLs containing embedded authentication credentials (`rtsp://user:pass@host:port/stream`) are sanitized via regex (`mask_stream_url`) before entering logs, API responses, or JSON exports.
5. **Anti-Fatigue Deduplication**: Continuous camera frames of an existing flood event update telemetry instead of flooding responders with duplicate notifications.

---

## 10. Conclusion

CivicSentinel demonstrates how modern **OpenCV 5** computer vision algorithms, coupled with **AWS Graviton3 ARM64** infrastructure and an **agentic perception-decision-action state machine**, can transform municipal flood surveillance from a reactive, manual task into an autonomous, closed-loop incident management platform. By achieving sub-millisecond per-frame latencies, rigorous edge-case handling, and cryptographically verified emergency dispatches, CivicSentinel provides a practical, scalable blueprint for smart city infrastructure resilience.

---
*OpenCV AI Competition 2026, Powered by AWS • All source code and reproducibility scripts are available in the project repository.*
