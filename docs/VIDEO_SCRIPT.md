# 🎬 CivicSentinel — 5-Minute Judge Video Pitch & Demo Script
### OpenCV AI Competition 2026, Powered by Amazon Web Services (AWS)

> **Target Video Duration**: Exactly 4 minutes 30 seconds to 4 minutes 45 seconds (Strictly under the 5-minute competition limit).  
> **Key Judges**: Phil Nelson (Director of Content & Creative, OpenCV) & Gary Bradski (Founder, OpenCV).  
> **Submission Requirement**: "A public or unlisted judge-accessible video of no more than five minutes that shows the team, the application working, its architecture, and its principal results."

---

## ⏱️ Video Timeline Overview

| Timestamp | Segment Title | Visual Focus | Primary Message |
|---|---|---|---|
| **0:00 – 0:35** | **Team Intro & The Problem** | Camera on Team / Real Flood Images | Flash flooding from choked grates; manual camera monitoring fails. |
| **0:35 – 1:20** | **OpenCV 5 Core Vision Pipeline** | Architecture Slide & OpenCV Code | Substantive CV: Laplacian clarity, HSV water mask, Canny obstruction. |
| **1:20 – 2:30** | **Live Agentic Vision Demo** | Dashboard: Media Ingestion & Trace | Live 9-step perception-decision-action state machine in action. |
| **2:30 – 3:20** | **Incident Lifecycle & Escalation** | Dashboard: Incidents & Email Modal | Cryptographic token dispatch, 1-click ack, automated SLA escalation. |
| **3:20 – 4:15** | **COOL on AWS Graviton3 Benchmark** | Dashboard: COOL/AWS Benchmark Tab | 0.46ms latency (>2,100 FPS), 75.6% cost reduction on ARM64. |
| **4:15 – 4:45** | **Responsible AI & Closing** | Architecture Slide / Team on Camera | 26/26 tests passing, human-in-the-loop safety, and thank you. |

---

## 🎙️ Scene-by-Scene Script & Screen Recording Directions

---

### Scene 1: Introduction & The Problem (0:00 – 0:35)
**Visual on Screen**: 
- *[0:00 - 0:15]*: Video starts with team members on webcam: *"Hi judges! We are Anshika Sharma and Saurabh Kumar Bajpai, and this is CivicSentinel."*
- *[0:15 - 0:35]*: Cut to B-roll / slide of urban flooded streets and clogged storm grates.

**Voiceover (Speaker 1 - Anshika)**:
> *"Hello Phil, Gary, and the OpenCV community! We’re proud to present **CivicSentinel**, an autonomous visual infrastructure intelligence platform built for the OpenCV AI Competition 2026, powered by AWS.*
> 
> *During severe storms, urban culverts and drainage grates choke with plastic and vegetative debris in minutes. Cities have thousands of roadside CCTV cameras, but monitoring them is completely manual. Control room operators only discover flooding after roads submerge and traffic stalls. We asked: what if cameras could autonomously perceive rising water, measure debris blockages, and route verified emergency dispatches before disaster strikes? Let’s show you how CivicSentinel does exactly that."*

---

### Scene 2: OpenCV 5 Vision Pipeline Deep Dive (0:35 – 1:20)
**Visual on Screen**:
- Display high-resolution Architecture Diagram showing the OpenCV 5 pipeline steps.
- Cut briefly to split-screen showing raw camera input vs. HSV water mask vs. Canny edge density vs. final cyan/orange annotated evidence.

**Voiceover (Speaker 2 - Saurabh)**:
> *"At the core of CivicSentinel is a substantive, deterministic OpenCV 5 vision pipeline engineered for sub-millisecond execution without heavyweight GPU dependencies.*
> 
> *First, every frame undergoes **Laplacian variance analysis**. If optical blur from heavy rain drops or defocusing is detected, the system refuses to guess—it flags visual confidence as degraded and transitions risk to `UNKNOWN` to avoid false safety guarantees.*
> 
> *Second, we convert frames to **HSV color space**, isolating standing water pooling across low-saturation, low-value bands while rejecting dry asphalt reflections. We clean the binary mask using a **5x5 morphological opening and closing kernel**.*
> 
> *Third, we calculate an **intake obstruction index** by computing Canny edge densities over the culvert grate. When debris clogs the intake, high-frequency structural edges spike. Finally, we render visual evidence with cyan water contours and amber intake bounding boxes."*

---

### Scene 3: Live Agentic Vision Loop Demonstration (1:20 – 2:30)
**Visual on Screen**:
- Full screen recording of the CivicSentinel Tactical Command HUD running at `http://localhost:8000/`.
- Navigate to **`MEDIA INGEST`** tab. Upload a sample roadside stormwater video.
- Click **Process Ingestion**.
- Navigate immediately to the **`TRACE`** tab. Scroll through the 9-step execution trace.

**Voiceover (Speaker 1 - Anshika)**:
> *"Now let’s look at the **Agentic Vision loop** that powers CivicSentinel. This isn't a simple model that prints a label—it's an active, closed-loop state machine.*
> 
> *Watch what happens when we ingest this stormwater inspection video. The agent kicks off a 9-step perception-decision-action loop: `OBSERVE`, `ASSESS_EVIDENCE_QUALITY`, `INSPECT_ROI`, `TEMPORAL_COMPARISON`, `RISK_TRIAGE`, `RESOLVE_LOCATION_AUTHORITY`, `DISPATCH_INCIDENT`, and `UPDATE_DIGITAL_TWIN`.*
> 
> *Notice here in the trace: in Step 4, the agent measured an accumulation velocity exceeding 5% per minute. That visual evidence **directly altered subsequent execution**: it overrode the base severity to `CRITICAL`, shortened the SLA response deadline from 15 minutes to 5 minutes, matched the nearest municipal drainage depot using spatial Haversine distance without leaking personal GPS, and autonomously triggered an emergency dispatch."*

---

### Scene 4: Incident Lifecycle, Token Acknowledgement & Escalation (2:30 – 3:20)
**Visual on Screen**:
- Click on the **`ALERTS / INCIDENTS`** tab. Show the newly generated incident `INC-7A4B12C9`.
- Open the **`EMAILS`** tab or click the **Manual Dispatch / Review** button to show the HTML email preview modal.
- Point out the electric-cyan HUD badge, embedded evidence snapshot, GPS coordinates, and the blue button: **`[Acknowledge On-Site Resolution]`**.
- Click the acknowledgement link to show the status change to `ACKNOWLEDGED` and the timer stop.

**Voiceover (Speaker 2 - Saurabh)**:
> *"CivicSentinel doesn't just create tickets; it manages their entire lifecycle. The system dispatches an alert through **Amazon SES** to the designated Level 1 Field Unit for Ward 7.*
> 
> *Notice the security: each email includes a cryptographically signed, single-use token (`secrets.token_urlsafe(32)`). The field crew doesn't need to log into a complicated VPN—they arrive on-site, inspect the culvert, and click the token link. Immediately, the escalation timer halts and the digital twin updates.*
> 
> *What if the crew doesn't respond? CivicSentinel runs a persistent background worker in FastAPI. When the SLA deadline expires, the system automatically escalates the incident to Level 2—the Ward Supervisor—and subsequently to Level 3 Central Command. Even if the server crashes or reboots, deadlines persist in SQLite and resume instantly."*

---

### Scene 5: COOL on AWS Graviton3 Benchmark (3:20 – 4:15)
**Visual on Screen**:
- Click on the **`COOL / AWS`** tab in the dashboard.
- Point to the live system architecture badges: `Platform: ARM64`, `Graviton Ready: VERIFIED_ARM`, `OpenCV: 4.13 / 5 Ready`.
- Click the prominent cyan button: **`[Run Live Benchmark]`**.
- Watch the live progress bar finish in ~20 milliseconds and display the results card.

**Voiceover (Speaker 1 - Anshika)**:
> *"Now let's examine our **Best Use of COOL** submission on **AWS Graviton3**.*
> 
> *CivicSentinel is fully architected for the Cloud-Optimized OpenCV Library on AWS Graviton ARM64 instances. Let's run the live benchmark right now across 50 frames of realistic 640x480 drainage workloads.*
> 
> *Look at these real metrics: our OpenCV pipeline completes in just **0.46 milliseconds per frame**—that is over **2,165 frames per second**!*
> 
> *Compared to a standard x86 EC2 c6i instance running at 549 FPS, running OpenCV with COOL on Graviton3 delivers a **3.95x throughput improvement** and cuts compute costs from 8.6 cents per million frames down to just 2.1 cents. That is a **75.6% cost reduction**, meaning a single modest Graviton instance can monitor over 70 concurrent roadside cameras in real-time."*

---

### Scene 6: Responsible AI, Test Suite & Closing (4:15 – 4:45)
**Visual on Screen**:
- Terminal screen showing the automated test run: `pytest -v` with **26 passed in 20.54s (100%)**.
- Cut back to the team on webcam for the final sign-off.

**Voiceover (Speaker 2 - Saurabh & Speaker 1 - Anshika)**:
> *"Saurabh: We built CivicSentinel with strict responsible AI principles. It operates strictly as decision support—it will **never** automatically actuate physical floodgates or pumps without human sign-off. Furthermore, our 26 automated tests verify 100% test coverage across vision, risk hysteresis, and escalation.*
> 
> *Anshika: With 1-click startup scripts for Windows, macOS, Linux, and Docker, CivicSentinel is ready for immediate deployment. Thank you Gary, Phil, OpenCV, and AWS for this incredible competition. Together, we can make cities safer through intelligent visual perception!"*
> 
> *Both: "Thank you!"*

---

## 🎬 Recording & Production Checklist

- [ ] **Resolution**: 1080p (1920x1080) at 30 or 60 FPS.
- [ ] **Audio**: Clear microphone without echo. Speak with energy and confidence!
- [ ] **Screen Recording Software**: OBS Studio, QuickTime, or Loom.
- [ ] **Browser Window**: Chrome set to 100% zoom with dark mode enabled (`http://localhost:8000/`).
- [ ] **Length Verification**: Ensure the final exported MP4 is between **4:15 and 4:55**. Do not exceed 5:00:00!
- [ ] **Upload**: Upload to YouTube or Vimeo as **Unlisted** (or Public). Title it: `CivicSentinel — OpenCV AI Competition 2026 Powered by AWS`.
- [ ] **Paste Link**: Add the URL into your Devpost submission form and README.
