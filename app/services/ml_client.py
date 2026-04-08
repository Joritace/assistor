import os
import requests
from dotenv import load_dotenv

load_dotenv()

ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "")
USE_MOCK_ML = os.getenv("USE_MOCK_ML", "true").lower() == "true"


def get_mock_payload() -> dict:
    """
    Temporary sample detections used until the real RT/ML service is deployed.
    """
    return {
        "image_width": 1280,
        "image_height": 720,
        "detections": [
            {
                "class_name": "stairs",
                "confidence": 0.92,
                "bbox": [820, 420, 1180, 710]
            },
            {
                "class_name": "road",
                "confidence": 0.88,
                "bbox": [20, 430, 430, 715]
            },
            {
                "class_name": "person",
                "confidence": 0.79,
                "bbox": [520, 260, 700, 670]
            }
        ]
    }


def predict_from_ml_service() -> dict:
    """
    Calls the external ML service.
    For now, Flask sends a temporary structured payload.
    Later, this can be changed to send the image itself or RT detections.
    """
    if USE_MOCK_ML:
        return {
            "ok": True,
            "mock_mode": True,
            "payload": get_mock_payload()
        }

    if not ML_SERVICE_URL:
        return {
            "ok": False,
            "error": "ML_SERVICE_URL is not configured"
        }

    try:
        response = requests.post(
            ML_SERVICE_URL,
            json=get_mock_payload(),
            timeout=30
        )

        if response.status_code != 200:
            return {
                "ok": False,
                "error": f"ML service returned status {response.status_code}",
                "details": response.text
            }

        data = response.json()
        return {
            "ok": True,
            "mock_mode": False,
            "payload": data
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }