from pprint import pprint
from safety_rules import apply_safety_rules

sample_ml_response = {
    "ok": True,
    "decision": "Move Right",
    "decision_confidence": 0.9999997843806138,
    "features": {
        "total_object": 3,
        "total_left_object": 1,
        "total_center_object": 1,
        "total_right_object": 1,
        "total_left_object_in_4m": 1,
        "total_center_object_in_4m": 1,
        "total_right_object_in_4m": 1,
        "total_left_object_in_2m": 1,
        "total_center_object_in_2m": 0,
        "total_right_object_in_2m": 0,
        "0_index_objects_class_name": "road",
        "0_index_objects_angle": "far_left",
        "0_index_objects_posistion": "left",
        "1_index_objects_class_name": "stairs",
        "1_index_objects_angle": "far_right",
        "1_index_objects_posistion": "right",
        "2_index_objects_class_name": "person",
        "2_index_objects_angle": "center",
        "2_index_objects_posistion": "center"
    },
    "scene_flags": {
        "left_objects": ["road"],
        "center_objects": ["person"],
        "right_objects": ["stairs"],
        "left_summary": "road",
        "center_summary": "person",
        "right_summary": "stairs"
    },
    "enriched_detections": [
        {
            "class_name": "stairs",
            "confidence": 0.92,
            "bbox": [820, 420, 1180, 710],
            "bbox_area": 104400,
            "bbox_area_ratio": 0.11328125,
            "center_x": 1000.0,
            "center_y": 565.0,
            "position": "right",
            "angle": "far_right",
            "distance_band": "within_4m"
        },
        {
            "class_name": "road",
            "confidence": 0.88,
            "bbox": [20, 430, 430, 715],
            "bbox_area": 116850,
            "bbox_area_ratio": 0.12679036458333334,
            "center_x": 225.0,
            "center_y": 572.5,
            "position": "left",
            "angle": "far_left",
            "distance_band": "within_2m"
        },
        {
            "class_name": "person",
            "confidence": 0.79,
            "bbox": [520, 260, 700, 670],
            "bbox_area": 73800,
            "bbox_area_ratio": 0.080078125,
            "center_x": 610.0,
            "center_y": 465.0,
            "position": "center",
            "angle": "center",
            "distance_band": "within_4m"
        }
    ]
}

safe_result = apply_safety_rules(sample_ml_response)

print("\nSAFE RESULT:\n")
pprint(safe_result)