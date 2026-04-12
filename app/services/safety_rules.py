from typing import Dict, Any, List


DANGEROUS_CLASSES = {
    "stairs",
    "car",
    "vehicle",
    "motorcycle",
    "pole",
    "wall",
    "obstacle",
    "drain",
    "pothole",
}

SAFE_PATH_CLASSES = {
    "road",
    "footpath",
    "sidewalk",
    "walkway",
    "path",
}

BLOCKING_CLASSES = {
    "person",
    "stairs",
    "car",
    "vehicle",
    "motorcycle",
    "pole",
    "wall",
    "obstacle",
    "drain",
    "pothole",
}


def normalize_list(values: List[str]) -> List[str]:
    return [str(v).strip().lower() for v in values if str(v).strip()]


def contains_any(values: List[str], candidates: set) -> bool:
    return any(v in candidates for v in values)


def zone_has_danger(zone_objects: List[str]) -> bool:
    zone_objects = normalize_list(zone_objects)
    return contains_any(zone_objects, DANGEROUS_CLASSES)


def zone_has_safe_path(zone_objects: List[str]) -> bool:
    zone_objects = normalize_list(zone_objects)
    return contains_any(zone_objects, SAFE_PATH_CLASSES)


def zone_is_blocked(zone_objects: List[str]) -> bool:
    zone_objects = normalize_list(zone_objects)
    return contains_any(zone_objects, BLOCKING_CLASSES)


def has_close_danger_in_zone(enriched_detections: List[Dict[str, Any]], zone: str) -> bool:
    for det in enriched_detections:
        det_zone = str(det.get("position", "")).lower()
        det_class = str(det.get("class_name", "")).lower()
        det_band = str(det.get("distance_band", "")).lower()

        if det_zone == zone and det_class in DANGEROUS_CLASSES and det_band in {"within_2m", "within_4m"}:
            return True
    return False

#Pick the first useful class name from a comma-separated summary.
def first_meaningful_object(summary: str) -> str:
    if not summary:
        return ""

    parts = [p.strip().lower() for p in summary.split(",") if p.strip()]
    if not parts:
        return ""

    if parts[0] == "none":
        return ""

    return parts[0]

# Generate a user friendly phrase describing the object and its location based on the zone.
def zone_phrase(summary: str, zone_name: str) -> str:
    obj = first_meaningful_object(summary)
    if not obj:
        return ""

    if zone_name == "center":
        return f"{obj} ahead"
    return f"{obj} on the {zone_name}"


def build_guidance_message(final_decision: str, scene_flags: Dict[str, Any]) -> str:
    left_summary = str(scene_flags.get("left_summary", "none"))
    center_summary = str(scene_flags.get("center_summary", "none"))
    right_summary = str(scene_flags.get("right_summary", "none"))

    left_phrase = zone_phrase(left_summary, "left")
    center_phrase = zone_phrase(center_summary, "center")
    right_phrase = zone_phrase(right_summary, "right")

    if final_decision == "Stop":
        if center_phrase:
            return f"Stop. {center_phrase.capitalize()}."
        if left_phrase:
            return f"Stop. {left_phrase.capitalize()}."
        if right_phrase:
            return f"Stop. {right_phrase.capitalize()}."
        return "Stop. Path is not safe."

    if final_decision == "Move Left":
        reasons = []
        if right_phrase:
            reasons.append(right_phrase)
        if center_phrase:
            reasons.append(center_phrase)

        if reasons:
            return f"Move left carefully. {', '.join(reasons).capitalize()}."
        return "Move left carefully."

    if final_decision == "Move Right":
        reasons = []
        if left_phrase:
            reasons.append(left_phrase)
        if center_phrase:
            reasons.append(center_phrase)

        if reasons:
            return f"Move right carefully. {', '.join(reasons).capitalize()}."
        return "Move right carefully."

    if final_decision == "Move Forward":
        if left_phrase and right_phrase:
            return f"Keep forward carefully. {left_phrase.capitalize()}, {right_phrase}."
        if center_phrase:
            return f"Keep forward carefully. {center_phrase.capitalize()}."
        return "Keep forward carefully. Path appears clear."

    return "Proceed carefully."

# function to apply safety rules on top of the ML model's decision.
def apply_safety_rules(decision_result: Dict[str, Any]) -> Dict[str, Any]:

    model_decision = str(decision_result.get("decision", "Stop"))
    scene_flags = decision_result.get("scene_flags", {})
    enriched_detections = decision_result.get("enriched_detections", [])

    left_objects = normalize_list(scene_flags.get("left_objects", []))
    center_objects = normalize_list(scene_flags.get("center_objects", []))
    right_objects = normalize_list(scene_flags.get("right_objects", []))

    left_danger = zone_has_danger(left_objects) or has_close_danger_in_zone(enriched_detections, "left")
    center_danger = zone_has_danger(center_objects) or has_close_danger_in_zone(enriched_detections, "center")
    right_danger = zone_has_danger(right_objects) or has_close_danger_in_zone(enriched_detections, "right")

    left_safe_path = zone_has_safe_path(left_objects)
    center_safe_path = zone_has_safe_path(center_objects)
    right_safe_path = zone_has_safe_path(right_objects)

    left_blocked = zone_is_blocked(left_objects)
    center_blocked = zone_is_blocked(center_objects)
    right_blocked = zone_is_blocked(right_objects)

    final_decision = model_decision
    override_reason = None

    # Rule 1: If center is unsafe, do not keep moving forward
    if model_decision == "Move Forward" and (center_danger or center_blocked):
        if left_safe_path and not left_danger and not left_blocked:
            final_decision = "Move Left"
            override_reason = "Center unsafe, left safer"
        elif right_safe_path and not right_danger and not right_blocked:
            final_decision = "Move Right"
            override_reason = "Center unsafe, right safer"
        else:
            final_decision = "Stop"
            override_reason = "Center unsafe and no clear alternative"

    # Rule 2: If model chooses right but right is dangerous, override
    if model_decision == "Move Right" and (right_danger or right_blocked):
        if left_safe_path and not left_danger and not left_blocked:
            final_decision = "Move Left"
            override_reason = "Right unsafe, left safer"
        elif center_safe_path and not center_danger and not center_blocked:
            final_decision = "Move Forward"
            override_reason = "Right unsafe, center safer"
        else:
            final_decision = "Stop"
            override_reason = "Right unsafe and no safe alternative"

    # Rule 3: If model chooses left but left is dangerous, override
    if model_decision == "Move Left" and (left_danger or left_blocked):
        if right_safe_path and not right_danger and not right_blocked:
            final_decision = "Move Right"
            override_reason = "Left unsafe, right safer"
        elif center_safe_path and not center_danger and not center_blocked:
            final_decision = "Move Forward"
            override_reason = "Left unsafe, center safer"
        else:
            final_decision = "Stop"
            override_reason = "Left unsafe and no safe alternative"

    # Rule 4: If all directions are unsafe, force Stop
    if (left_danger or left_blocked) and (center_danger or center_blocked) and (right_danger or right_blocked):
        final_decision = "Stop"
        override_reason = "All directions unsafe"

    final_message = build_guidance_message(final_decision, scene_flags)

    return {
        **decision_result,
        "model_decision": model_decision,
        "final_decision": final_decision,
        "final_message": final_message,
        "override_reason": override_reason,
        "safety_flags": {
            "left_danger": left_danger,
            "center_danger": center_danger,
            "right_danger": right_danger,
            "left_safe_path": left_safe_path,
            "center_safe_path": center_safe_path,
            "right_safe_path": right_safe_path,
            "left_blocked": left_blocked,
            "center_blocked": center_blocked,
            "right_blocked": right_blocked,
        }
    }