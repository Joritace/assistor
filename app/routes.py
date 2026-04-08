import base64
from flask import Blueprint, jsonify, render_template, request, current_app

from .services.ml_client import predict_from_ml_service
from .services.safety_rules import apply_safety_rules

main = Blueprint("main", __name__)


@main.route("/")
def home():
    return render_template("index.html")


@main.route("/health", methods=["GET"])
def health():
    return jsonify({
        "ok": True,
        "status": "running",
        "message": "Nav Assist server is working",
        "use_mock_ml": current_app.config.get("USE_MOCK_ML", True)
    })


@main.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "ok": False,
                "error": "No JSON body received"
            }), 400

        image_data = data.get("image")

        if not image_data:
            return jsonify({
                "ok": False,
                "error": "No image field found"
            }), 400

        if "," not in image_data:
            return jsonify({
                "ok": False,
                "error": "Invalid image format"
            }), 400

        header, encoded = image_data.split(",", 1)

        try:
            decoded_bytes = base64.b64decode(encoded)
        except Exception:
            return jsonify({
                "ok": False,
                "error": "Image is not valid base64"
            }), 400

        if not decoded_bytes:
            return jsonify({
                "ok": False,
                "error": "Decoded image is empty"
            }), 400

        ml_response = predict_from_ml_service()

        if not ml_response.get("ok"):
            return jsonify({
                "ok": False,
                "error": "ML service failed",
                "details": ml_response
            }), 500

        if ml_response.get("mock_mode"):
            # Temporary path:
            # use structured detections directly and pass them through safety rules later
            payload = ml_response["payload"]

            # For now this just simulates what the external ML service will return later
            # Replace this section once Hugging Face returns the full decision JSON
            fake_ml_result = {
                "ok": True,
                "decision": "Move Right",
                "decision_confidence": 0.99,
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
        else:
            fake_ml_result = ml_response["payload"]

        safe_result = apply_safety_rules(fake_ml_result)

        return jsonify({
            "ok": True,
            "decision": safe_result.get("final_decision", "Stop"),
            "message": safe_result.get("final_message", "Stop. Path is not safe."),
            "cooldown": 3,
            "model_decision": safe_result.get("model_decision"),
            "override_reason": safe_result.get("override_reason"),
            "scene_flags": safe_result.get("scene_flags"),
            "safety_flags": safe_result.get("safety_flags")
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500