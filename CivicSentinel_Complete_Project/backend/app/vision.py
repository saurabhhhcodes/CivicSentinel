import os
import logging
from typing import Union
from pathlib import Path
from datetime import datetime, timezone
import cv2
import numpy as np

logger = logging.getLogger("civicsentinel.vision")

def evaluate_image_quality(frame: np.ndarray) -> dict:
    """Assess visual quality: blur, texture, brightness, contrast."""
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
    
    # Laplacian variance for blur/sharpness
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    # Brightness / luminance
    mean_val = float(np.mean(gray))
    # Contrast / standard deviation
    std_val = float(np.std(gray))
    
    issues = []
    if lap_var < 35.0:
        issues.append("Low sharpness / motion blur detected")
    if mean_val < 30.0:
        issues.append("Underexposed / low ambient lighting")
    elif mean_val > 225.0:
        issues.append("Overexposed / glare saturation")
    if std_val < 15.0:
        issues.append("Low texture / lack of contrast")
        
    is_acceptable = len(issues) == 0
    quality_label = "acceptable" if is_acceptable else ("degraded" if len(issues) == 1 else "poor")
    
    return {
        "quality_label": quality_label,
        "is_acceptable": is_acceptable,
        "sharpness_score": round(lap_var, 2),
        "mean_luminance": round(mean_val, 2),
        "contrast_std": round(std_val, 2),
        "quality_issues": issues
    }

def analyze_water_and_obstruction(frame: np.ndarray) -> tuple[dict, np.ndarray]:
    """
    Substantive OpenCV analysis:
    - Rescaling for uniform processing
    - HSV segmentation for reflective ponding and muddy stormwater
    - Morphological filtering (opening + closing)
    - Contour extraction and area measurement
    - Edge density analysis in candidate ROIs for obstruction detection
    - Bounding boxes and HUD annotation
    """
    h, w = frame.shape[:2]
    scale = min(1.0, 720 / max(w, h))
    proc_frame = cv2.resize(frame, (int(w * scale), int(h * scale))) if scale < 1.0 else frame.copy()
    proc_h, proc_w = proc_frame.shape[:2]
    total_pixels = max(1, proc_h * proc_w)

    quality = evaluate_image_quality(proc_frame)

    # Multi-band HSV segmentation:
    # 1. Dark/reflective water ponding (low value, moderate saturation)
    # 2. Turbid / silt-laden stormwater runoff (brown/greenish-grey tint)
    hsv = cv2.cvtColor(proc_frame, cv2.COLOR_BGR2HSV)
    
    # Dark reflective water mask
    mask_dark = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 110, 85]))
    # Turbid stormwater runoff mask
    mask_turbid = cv2.inRange(hsv, np.array([15, 25, 30]), np.array([140, 255, 200]))
    combined_mask = cv2.bitwise_or(mask_dark, mask_turbid)

    # Morphological cleaning
    kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    kernel_large = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    cleaned_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel_small)
    cleaned_mask = cv2.morphologyEx(cleaned_mask, cv2.MORPH_CLOSE, kernel_large)

    # Find contours of candidate water regions
    contours, _ = cv2.findContours(cleaned_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = total_pixels * 0.003
    significant_contours = [c for c in contours if cv2.contourArea(c) > min_area]

    water_area = sum(cv2.contourArea(c) for c in significant_contours)
    water_area_ratio = round(float(water_area / total_pixels), 4)
    visual_water_level_proxy = round(float(min(1.0, water_area_ratio * 2.2)), 4)

    # Obstruction indicator heuristic:
    # Examine edges around candidate drainage margins
    gray_proc = cv2.cvtColor(proc_frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray_proc, 50, 150)
    
    # Measure edge clutter inside water boundary dilation (indicates floating debris, foliage, blockage)
    dilated_water = cv2.dilate(cleaned_mask, kernel_large, iterations=2)
    debris_edge_pixels = cv2.bitwise_and(edges, edges, mask=dilated_water)
    debris_count = cv2.countNonZero(debris_edge_pixels)
    debris_density = round(float(debris_count / max(1, cv2.countNonZero(dilated_water))), 4) if cv2.countNonZero(dilated_water) > 0 else 0.0

    obstruction_suspected = debris_density > 0.08 and water_area_ratio > 0.05
    obstruction_index = round(float(min(1.0, debris_density * 5.0 + (0.2 if water_area_ratio > 0.2 else 0.0))), 3)

    # Visual confidence quantification
    base_confidence = 0.35
    if quality["quality_label"] == "acceptable":
        base_confidence += 0.20
    elif quality["quality_label"] == "degraded":
        base_confidence += 0.05
    else:
        base_confidence -= 0.15

    if len(significant_contours) > 0:
        base_confidence += min(0.25, len(significant_contours) * 0.05)
    else:
        base_confidence += 0.10  # clear absence of water is also informative

    visual_confidence = round(float(np.clip(base_confidence, 0.1, 0.90)), 3)

    # Generate rich annotated evidence overlay
    ann = proc_frame.copy()
    # Draw water contours in cyan/yellow
    cv2.drawContours(ann, significant_contours, -1, (255, 200, 0), 2)
    
    # Draw bounding boxes for significant regions
    for c in significant_contours[:4]:
        bx, by, bw, bh = cv2.boundingRect(c)
        cv2.rectangle(ann, (bx, by), (bx + bw, by + bh), (0, 165, 255), 1)
        cv2.putText(ann, f"ROI: {bw*bh}px", (bx, max(15, by - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)

    # Draw HUD overlay banner
    overlay = ann.copy()
    cv2.rectangle(overlay, (0, 0), (proc_w, 42), (20, 24, 33), -1)
    cv2.addWeighted(overlay, 0.8, ann, 0.2, 0, ann)

    hud_text = f"WATER PROXY: {water_area_ratio*100:.1f}% | DEBRIS INDEX: {obstruction_index:.2f} | CONF: {visual_confidence*100:.0f}%"
    cv2.putText(ann, hud_text, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

    metrics = {
        "width": w,
        "height": h,
        "processed_width": proc_w,
        "processed_height": proc_h,
        "water_area_ratio_proxy": water_area_ratio,
        "visual_water_level_proxy": visual_water_level_proxy,
        "candidate_region_count": len(significant_contours),
        "obstruction_suspected": obstruction_suspected,
        "obstruction_index_proxy": obstruction_index,
        "visual_confidence": visual_confidence,
        "image_quality": quality["quality_label"],
        "quality_metrics": quality,
        "limitations": [
            "Heuristic visual proxy only; not a physically calibrated drainage sensor.",
            "Dark asphalt, shadows, and reflective glass can cause proxy false positives.",
            "Debris index reflects visual edge clutter near runoff margins, not sub-surface pipe blockage.",
            "Confidence is bounded; human inspection must verify consequential flood conditions."
        ]
    }
    return metrics, ann

def decode_image_buffer(input_data: Union[Path, str, bytes, bytearray, np.ndarray]) -> np.ndarray:
    """
    Safely decode image from file path, raw bytes, or numpy ndarray.
    Guards against Windows path encoding issues, empty streams, and RGBA channels.
    """
    if isinstance(input_data, np.ndarray):
        img = input_data
    elif isinstance(input_data, (bytes, bytearray)):
        file_bytes = bytes(input_data)
        if len(file_bytes) == 0:
            logger.error("Image decode failed: input byte buffer is empty (0 bytes).")
            raise ValueError("OpenCV could not decode image: input buffer is empty (0 bytes).")
        buf = np.frombuffer(file_bytes, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_UNCHANGED)
        if img is None:
            img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    elif isinstance(input_data, (str, Path)):
        p = Path(input_data)
        if not p.is_file():
            logger.error(f"Image decode failed: file does not exist at {p}")
            raise FileNotFoundError(f"Image file not found: {p}")
        file_bytes = p.read_bytes()
        if len(file_bytes) == 0:
            logger.error(f"Image decode failed: file at {p} is empty (0 bytes).")
            raise ValueError("OpenCV could not decode image: file is empty (0 bytes).")
        buf = np.frombuffer(file_bytes, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_UNCHANGED)
        if img is None:
            img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is None:
            # Secondary fallback: cv2.imread
            img = cv2.imread(str(p), cv2.IMREAD_COLOR)
    else:
        raise TypeError(f"Unsupported input type for image decoding: {type(input_data)}")

    if img is None:
        logger.error(f"OpenCV could not decode image: format corrupt or unsupported (input type: {type(input_data)}).")
        raise ValueError("OpenCV could not decode image. Format may be corrupt or unsupported.")

    # Channel normalization: safely convert RGBA or Grayscale to 3-channel BGR
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif len(img.shape) == 3 and img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    elif len(img.shape) == 3 and img.shape[2] == 1:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    return img

def process_image_media(file_path: Union[Path, str, bytes, np.ndarray], evidence_dir: Path, job_id: str) -> tuple[dict, list[str]]:
    """Process single uploaded image using OpenCV with robust buffer decoding and RGBA conversion."""
    logger.info(f"Processing image media for job {job_id}")
    frame = decode_image_buffer(file_path)
    if frame is None or frame.size == 0:
        logger.error(f"Decoded frame is None or empty for job {job_id}")
        raise ValueError("OpenCV could not decode image. Format may be corrupt or unsupported.")
    
    metrics, ann = analyze_water_and_obstruction(frame)
    out_name = f"{job_id}_annotated.jpg"
    out_path = evidence_dir / out_name
    
    # Save annotated evidence safely using imencode + write_bytes for cross-platform resilience
    success, enc = cv2.imencode(".jpg", ann, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if success:
        out_path.write_bytes(enc.tobytes())
    else:
        cv2.imwrite(str(out_path), ann, [cv2.IMWRITE_JPEG_QUALITY, 90])
    
    metrics.update({
        "media_type": "image",
        "frames_processed": 1,
        "frames_skipped": 0,
        "temporal_trend": "unavailable",
        "temporal_change": 0.0,
        "accumulation_rate_percent_per_min": 0.0,
        "evidence_images": [out_name]
    })
    return metrics, [out_name]


def process_video_media(file_path: Path, evidence_dir: Path, job_id: str, sample_interval: int, progress_cb=None) -> tuple[dict, list[str]]:
    """Process video media with temporal sampling, change detection and evidence generation."""
    cap = cv2.VideoCapture(str(file_path))
    if not cap.isOpened():
        cap.release()
        raise ValueError("OpenCV could not open video stream. Codec or container may be unsupported.")
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    
    observations = []
    evidence_files = []
    frame_idx = 0
    read_count = 0
    latest_metrics = None
    
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            read_count += 1
            if frame_idx % max(1, sample_interval) == 0:
                m, ann = analyze_water_and_obstruction(frame)
                ts = round(frame_idx / fps, 3) if fps > 0 else round(frame_idx * 0.033, 3)
                m["frame_index"] = frame_idx
                m["timestamp_seconds"] = ts
                observations.append(m)
                latest_metrics = m
                
                out_name = f"{job_id}_frame_{frame_idx:06d}.jpg"
                out_path = evidence_dir / out_name
                cv2.imwrite(str(out_path), ann, [cv2.IMWRITE_JPEG_QUALITY, 88])
                evidence_files.append(out_name)
                
            frame_idx += 1
            if progress_cb and total_frames > 0:
                prog = min(92, int((frame_idx / total_frames) * 92))
                progress_cb(prog)
    finally:
        cap.release()

    if not observations:
        raise ValueError("No decodable video frames were found in video stream.")

    # Calculate temporal accumulation trend
    ratios = [obs["water_area_ratio_proxy"] for obs in observations]
    delta = round(float(ratios[-1] - ratios[0]), 4) if len(ratios) > 1 else 0.0
    
    duration = round(total_frames / fps, 2) if fps > 0 and total_frames > 0 else round(read_count * 0.033, 2)
    acc_rate = 0.0
    if duration > 0 and len(ratios) > 1:
        # Rate of change in % area per minute
        acc_rate = round(float((delta * 100.0) / (duration / 60.0)), 2)

    if delta > 0.025 or acc_rate > 3.0:
        trend = "increasing"
    elif delta < -0.025 or acc_rate < -3.0:
        trend = "decreasing"
    elif len(ratios) > 1:
        trend = "stable"
    else:
        trend = "insufficient_observations"

    result = dict(latest_metrics)
    result.update({
        "media_type": "video",
        "fps": round(fps, 2),
        "duration_seconds": duration,
        "frames_reported": total_frames,
        "frames_processed": len(observations),
        "frames_skipped": max(0, read_count - len(observations)),
        "observations": observations,
        "temporal_trend": trend,
        "temporal_change": delta,
        "accumulation_rate_percent_per_min": acc_rate,
        "evidence_images": evidence_files
    })
    return result, evidence_files
