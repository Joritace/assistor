from typing import Dict, Any, List


DANGEROUS_CLASSES = {
    "up_stairs",
    "down_stairs",
    "car",
    "vehicle",
    "motorcycle",
    "train",
    "wall",
    "door",
    "tree",
    "traffic_light",
    "animal",
    "pothole",
    "road",
}

SAFE_PATH_CLASSES = {
    "footpath",
    "sidewalk",
    "zebra_crossing",
}

BLOCKING_CLASSES = {
    "person",
    "stairs",
    "up_stairs",
    "down_stairs",
    "car",
    "vehicle",
    "motorcycle",
    "train",
    "wall",
    "door",
    "tree",
    "traffic_light",
    "animal",
    "obstacle",
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


def has_close_danger_in_zone(
    enriched_detections: List[Dict[str, Any]],
    zone: str
) -> bool:
    for det in enriched_detections:
        det_zone = str(det.get("position", "")).lower()
        raw_class = str(det.get("raw_class_name", "")).lower()
        class_name = str(det.get("class_name", "")).lower()
        det_band = str(det.get("distance_band", "")).lower()

        if det_zone != zone:
            continue

        is_danger = raw_class in DANGEROUS_CLASSES or class_name in DANGEROUS_CLASSES
        is_close = det_band in {"within_2m", "within_4m"}

        if is_danger and is_close:
            return True

    return False


def first_meaningful_object(summary: str) -> str:
    if not summary:
        return ""

    parts = [p.strip().lower() for p in summary.split(",") if p.strip()]

    if not parts:
        return ""

    if parts[0] == "none":
        return ""

    return parts[0]


def make_object_readable(obj: str) -> str:
    obj = str(obj).strip().lower()

    readable = {
        "up_stairs": "up stairs",
        "down_stairs": "down stairs",
        "zebra_crossing": "zebra crossing",
        "traffic_light": "traffic light",
    }

    return readable.get(obj, obj.replace("_", " "))


def zone_phrase(summary: str, zone_name: str) -> str:
    obj = first_meaningful_object(summary)

    if not obj:
        return ""

    obj = make_object_readable(obj)

    if zone_name == "center":
        return f"{obj} ahead"

    return f"{obj} on the {zone_name}"


def get_zone_summary(scene_flags: Dict[str, Any], zone: str) -> str:
    # Prefer raw YOLO class summary for human safety messages
    return str(
        scene_flags.get(
            f"{zone}_raw_summary",
            scene_flags.get(f"{zone}_summary", "none")
        )
    )


def get_zone_raw_objects(scene_flags: Dict[str, Any], zone: str) -> List[str]:
    raw_objects = scene_flags.get(f"{zone}_raw_objects")

    if isinstance(raw_objects, list):
        return normalize_list(raw_objects)

    summary = get_zone_summary(scene_flags, zone)
    return normalize_list(summary.split(","))


def get_zone_all_objects(scene_flags: Dict[str, Any], zone: str) -> List[str]:
    normalized_objects = scene_flags.get(f"{zone}_objects", [])
    raw_objects = scene_flags.get(f"{zone}_raw_objects", [])

    normalized_objects = normalize_list(normalized_objects if isinstance(normalized_objects, list) else [])
    raw_objects = normalize_list(raw_objects if isinstance(raw_objects, list) else [])

    return list(set(normalized_objects + raw_objects))


def zone_has_stairs(objects: List[str]) -> bool:
    objects = normalize_list(objects)
    return any(obj in {"stairs", "up_stairs", "down_stairs"} for obj in objects)


def choose_careful_direction(scene_flags: Dict[str, Any]) -> str:
    left_all = get_zone_all_objects(scene_flags, "left")
    center_all = get_zone_all_objects(scene_flags, "center")
    right_all = get_zone_all_objects(scene_flags, "right")

    # If all directions have obstacles, stairs may still be a careful route.
    if zone_has_stairs(left_all):
        return "Move Left"

    if zone_has_stairs(right_all):
        return "Move Right"

    if zone_has_stairs(center_all):
        return "Move Forward"

    return "Stop"


def build_guidance_message(final_decision: str, scene_flags: Dict[str, Any]) -> str:
    left_summary = get_zone_summary(scene_flags, "left")
    center_summary = get_zone_summary(scene_flags, "center")
    right_summary = get_zone_summary(scene_flags, "right")

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
        left_obj = first_meaningful_object(left_summary)

        if left_obj in {"up_stairs", "down_stairs", "stairs"}:
            return f"Move left carefully. {make_object_readable(left_obj).capitalize()} on the left."

        reasons = []
        if center_phrase:
            reasons.append(center_phrase)
        if right_phrase:
            reasons.append(right_phrase)

        if reasons:
            return f"Move left carefully. {', '.join(reasons).capitalize()}."
        return "Move left carefully."

    if final_decision == "Move Right":
        right_obj = first_meaningful_object(right_summary)

        if right_obj in {"up_stairs", "down_stairs", "stairs"}:
            return f"Move right carefully. {make_object_readable(right_obj).capitalize()} on the right."

        reasons = []
        if center_phrase:
            reasons.append(center_phrase)
        if left_phrase:
            reasons.append(left_phrase)

        if reasons:
            return f"Move right carefully. {', '.join(reasons).capitalize()}."
        return "Move right carefully."

    if final_decision == "Move Forward":
        center_obj = first_meaningful_object(center_summary)

        if center_obj in {"up_stairs", "down_stairs", "stairs"}:
            return f"Move forward carefully. {make_object_readable(center_obj).capitalize()} ahead."

        if left_phrase and right_phrase:
            return f"Keep forward carefully. {left_phrase.capitalize()}, {right_phrase}."
        if center_phrase:
            return f"Keep forward carefully. {center_phrase.capitalize()}."
        return "Keep forward carefully. Path appears clear."

    return "Proceed carefully."


def apply_safety_rules(decision_result: Dict[str, Any]) -> Dict[str, Any]:
    model_decision = str(decision_result.get("decision", "Stop"))

    scene_flags = decision_result.get("scene_flags", {})
    enriched_detections = decision_result.get("enriched_detections", [])

    left_all = get_zone_all_objects(scene_flags, "left")
    center_all = get_zone_all_objects(scene_flags, "center")
    right_all = get_zone_all_objects(scene_flags, "right")

    left_danger = zone_has_danger(left_all) or has_close_danger_in_zone(enriched_detections, "left")
    center_danger = zone_has_danger(center_all) or has_close_danger_in_zone(enriched_detections, "center")
    right_danger = zone_has_danger(right_all) or has_close_danger_in_zone(enriched_detections, "right")

    left_safe_path = zone_has_safe_path(left_all)
    center_safe_path = zone_has_safe_path(center_all)
    right_safe_path = zone_has_safe_path(right_all)

    left_blocked = zone_is_blocked(left_all)
    center_blocked = zone_is_blocked(center_all)
    right_blocked = zone_is_blocked(right_all)

    final_decision = model_decision
    override_reason = None

    # Rule 1: If center is unsafe, do not move forward blindly.
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

    # Rule 2: If model chooses right but right is unsafe, override.
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

    # Rule 3: If model chooses left but left is unsafe, override.
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

    # Rule 4: If all zones are unsafe, allow careful stairs route if present.
    if (
        (left_danger or left_blocked)
        and (center_danger or center_blocked)
        and (right_danger or right_blocked)
    ):
        careful_direction = choose_careful_direction(scene_flags)

        if careful_direction != "Stop":
            final_decision = careful_direction
            override_reason = "All directions have obstacles, but stairs may be usable carefully"
        else:
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
            "left_objects_checked": left_all,
            "center_objects_checked": center_all,
            "right_objects_checked": right_all,
        }
    }