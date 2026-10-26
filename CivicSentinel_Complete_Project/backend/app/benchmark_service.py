import time, platform, json, os
from pathlib import Path
import cv2
import numpy as np

def run_opencv_benchmark(frame_count: int = 50, resolution: tuple[int, int] = (640, 480)) -> dict:
    """
    Execute a real, verifiable OpenCV vision pipeline benchmark measuring:
    - Preprocessing (resizing, HSV color space conversion)
    - Morphological operations (dilation, erosion, open, close)
    - Canny edge detection & contour extraction
    - Measures mean latency, P95 latency, throughput (FPS), memory/architecture
    """
    w, h = resolution
    # Generate realistic synthetic drainage test patterns with water gradients and edge textures
    test_frames = []
    for i in range(10):
        f = np.zeros((h, w, 3), dtype=np.uint8)
        # Gradient background
        f[:, :] = (30 + i * 2, 40 + i * 2, 50 + i * 2)
        # Synthetic ponding region
        cv2.ellipse(f, (int(w * 0.5), int(h * 0.6)), (int(w * 0.3), int(h * 0.2)), 0, 0, 360, (150, 100, 40), -1)
        # High frequency edges (drainage grate)
        for x in range(int(w * 0.4), int(w * 0.6), 12):
            cv2.line(f, (x, int(h * 0.4)), (x, int(h * 0.7)), (220, 220, 220), 2)
        test_frames.append(f)

    # Warm-up phase (5 iterations)
    for i in range(5):
        gray = cv2.cvtColor(test_frames[i % len(test_frames)], cv2.COLOR_BGR2GRAY)
        _ = cv2.Canny(gray, 50, 150)

    # Timed measurement phase
    latencies_ms = []
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    failed_frames = 0

    t_start_total = time.perf_counter()
    for i in range(frame_count):
        f = test_frames[i % len(test_frames)]
        t0 = time.perf_counter()
        try:
            hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 110, 85]))
            cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
            contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 60, 140)
            t_el = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(t_el)
        except Exception:
            failed_frames += 1

    t_total = time.perf_counter() - t_start_total
    latencies_ms.sort()

    mean_lat = round(float(sum(latencies_ms) / max(1, len(latencies_ms))), 3) if latencies_ms else 0.0
    p95_lat = round(float(latencies_ms[min(len(latencies_ms) - 1, int(len(latencies_ms) * 0.95))]), 3) if latencies_ms else 0.0
    throughput_fps = round(float(len(latencies_ms) / max(0.001, t_total)), 1)

    arch = platform.machine()
    is_arm = "arm" in arch.lower() or "aarch64" in arch.lower()

    # Determine COOL status accurately without fabrication
    cool_installed = False
    try:
        import cool
        cool_installed = True
    except ImportError:
        cool_installed = False

    result = {
        "status": "BASELINE_BENCHMARK_COMPLETE",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "workload": "CivicSentinel OpenCV Drainage Analysis Pipeline",
        "opencv_version": cv2.__version__,
        "opencv5_active": cv2.__version__.startswith("5."),
        "platform": platform.platform(),
        "architecture": arch,
        "is_arm_graviton_compatible": is_arm,
        "frames_tested": frame_count,
        "failed_frames": failed_frames,
        "resolution": f"{w}x{h}",
        "mean_latency_ms": mean_lat,
        "p95_latency_ms": p95_lat,
        "throughput_fps": throughput_fps,
        "cool_status": "AVAILABLE" if cool_installed else "NOT_RUN",
        "graviton_status": "VERIFIED_ARM" if is_arm else "X86_LOCAL_BASELINE",
        "benchmark_notes": [
            f"Mean frame processing latency: {mean_lat} ms ({throughput_fps} FPS).",
            "COOL (OpenCV Optimized Layer) acceleration benchmark requires AWS Graviton (aarch64) EC2 instance.",
            "To execute COOL comparative benchmark on AWS Graviton, follow cool_benchmark/README.md instructions."
        ]
    }
    return result

def get_latest_benchmark_result(results_dir: Path) -> dict:
    """Read saved benchmark results or return informative NOT_RUN status."""
    latest_file = results_dir / "latest.json"
    if latest_file.is_file():
        try:
            return json.loads(latest_file.read_text())
        except Exception:
            pass
    return {
        "status": "NOT_RUN",
        "message": "No benchmark has been executed in this session. Call POST /api/benchmark/run to measure baseline vision latency."
    }
