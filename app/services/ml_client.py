import os
import requests
from dotenv import load_dotenv

load_dotenv()

ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "")
USE_MOCK_ML = os.getenv("USE_MOCK_ML", "true").lower() == "true"


def predict_from_ml_service(image_data: str) -> dict:
    # this sends the image from the backend to the hugging face ml service
    # the hf service now handles:
    # image -> grounding dino -> feature builder -> decision model
    if USE_MOCK_ML:
        return {
            "ok": False,
            "error": "USE_MOCK_ML is still true"
        }

    if not ML_SERVICE_URL:
        return {
            "ok": False,
            "error": "ML_SERVICE_URL is not configured"
        }

    try:
        response = requests.post(
            ML_SERVICE_URL,
            json={"image": image_data},
            timeout=90
        )

        if response.status_code != 200:
            return {
                "ok": False,
                "error": f"ML service returned status {response.status_code}",
                "details": response.text
            }

        return response.json()

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }