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
        "use_mock_ml": current_app.config.get("USE_MOCK_ML", True),
        "ml_service_url": current_app.config.get("ML_SERVICE_URL", "")
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

        # send the actual image to hugging face
        ml_result = predict_from_ml_service(image_data)

        if not ml_result.get("ok"):
            return jsonify({
                "ok": False,
                "error": "ML service failed",
                "details": ml_result
            }), 500

        # apply backend safety rules here
        safe_result = apply_safety_rules(ml_result)

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