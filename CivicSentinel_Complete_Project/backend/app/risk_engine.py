def evaluate_temporal_risk(
    water_area_ratio: float,
    temporal_trend: str,
    accumulation_rate: float,
    obstruction_index: float,
    visual_confidence: float,
    image_quality: str,
    previous_risk: str | None = None
) -> dict:
    """
    Transparent, multi-factor risk assessment for evolving stormwater and drainage hazards.
    Combines visual proxy, accumulation rate, obstruction clues, and visual uncertainty.
    
    Categories:
    - CRITICAL: Severe water coverage (>0.60) or rapid water accumulation (>8%/min) with obstruction.
    - HIGH: Substantial water coverage (>0.35) or expanding accumulation (>3%/min).
    - MEDIUM: Moderate water accumulation (>0.15) or isolated ponding with suspect blockage.
    - LOW: Minimal water (<0.15) and stable/decreasing conditions.
    - UNKNOWN: Degraded/poor visibility or confidence < 0.35. (UNKNOWN does not mean safe).
    """
    reasons = []

    # 1. Quality & Uncertainty Gating
    if visual_confidence < 0.35 or image_quality == "poor":
        return {
            "current_risk": "UNKNOWN",
            "predicted_risk": "UNKNOWN",
            "risk_score": 0.0,
            "human_review_required": True,
            "reasons": [
                f"Visual confidence is insufficient ({visual_confidence:.2f}) or image quality is poor ({image_quality}).",
                "Cannot reliably determine safety; UNKNOWN status does not imply absence of risk."
            ],
            "recommended_action": "Schedule physical inspection or verify camera lens condition."
        }

    # 2. Heuristic Composite Risk Score Calculation
    # Base score from water area ratio (0.0 to 1.0)
    score = water_area_ratio * 1.5

    # Trend modifier
    if temporal_trend == "increasing":
        trend_boost = min(0.35, max(0.1, accumulation_rate * 0.03))
        score += trend_boost
        reasons.append(f"Water accumulation is expanding (+{accumulation_rate:.1f}%/min).")
    elif temporal_trend == "decreasing":
        score -= 0.10
        reasons.append("Water level proxy is receding.")
    elif temporal_trend == "stable":
        reasons.append("Water ponding is persistent and static.")
    else:
        reasons.append("Single-observation assessment (temporal trend unavailable).")

    # Obstruction modifier
    if obstruction_index > 0.4:
        score += 0.20
        reasons.append(f"Visual debris clustering / surface obstruction indicator is elevated ({obstruction_index:.2f}).")

    reasons.append(f"Estimated surface runoff coverage proxy: {water_area_ratio * 100:.1f}%.")

    # Clamped composite score
    composite_score = round(float(min(1.0, max(0.0, score))), 3)

    # 3. Categorization with Hysteresis (prevents flapping around boundaries)
    # Hysteresis buffer = 0.04
    h_buf = 0.04 if previous_risk else 0.0

    if composite_score >= (0.80 - (h_buf if previous_risk == "CRITICAL" else 0.0)) or (water_area_ratio >= 0.55 and temporal_trend == "increasing"):
        current_risk = "CRITICAL"
        recommended_action = "IMMEDIATE DISPATCH: Deploy rapid response drainage crew, clear catchbasin intake, and notify district supervisor."
    elif composite_score >= (0.50 - (h_buf if previous_risk in ("HIGH", "CRITICAL") else 0.0)):
        current_risk = "HIGH"
        recommended_action = "PRIORITY INSPECTION: Deploy field crew within 30 minutes to verify intake blockage and clear grates."
    elif composite_score >= (0.22 - (h_buf if previous_risk in ("MEDIUM", "HIGH") else 0.0)):
        current_risk = "MEDIUM"
        recommended_action = "MONITOR & QUEUE: Log asset for routine scheduled inspection during the next maintenance shift."
    else:
        current_risk = "LOW"
        recommended_action = "NORMAL: No active drainage hazard detected; continue automated background surveillance."

    # Predicted risk projection based on accumulation rate
    if current_risk == "CRITICAL":
        predicted_risk = "CRITICAL"
    elif current_risk == "HIGH":
        predicted_risk = "CRITICAL" if temporal_trend == "increasing" else "HIGH"
    elif current_risk == "MEDIUM":
        predicted_risk = "HIGH" if temporal_trend == "increasing" else "MEDIUM"
    else:
        predicted_risk = "MEDIUM" if temporal_trend == "increasing" else "LOW"

    human_review_required = current_risk in ("MEDIUM", "HIGH", "CRITICAL", "UNKNOWN") or visual_confidence < 0.60

    reasons.append("Transparent heuristic evaluation; not a calibrated hydraulic hydrodynamic model.")

    return {
        "current_risk": current_risk,
        "predicted_risk": predicted_risk,
        "risk_score": composite_score,
        "human_review_required": human_review_required,
        "reasons": reasons,
        "recommended_action": recommended_action
    }
