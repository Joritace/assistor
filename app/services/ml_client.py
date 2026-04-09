import os
import requests
from dotenv import load_dotenv

load_dotenv()

ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://127.0.0.1:7860/predict")


def predict_from_ml_service(image_data: str) -> dict:
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