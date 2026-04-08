import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "nav-assist-dev-key")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

    # This will later point to our Hugging Face ML service
    ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "")

    # Temporary mode:for testing
    # true  -> use local sample detections
    # false -> call external ML service
    USE_MOCK_ML = os.getenv("USE_MOCK_ML", "true").lower() == "true"