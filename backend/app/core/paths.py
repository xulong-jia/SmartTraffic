from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = Path(__file__).resolve().parents[3]
RESULTS_DIR = PROJECT_DIR / "results" / "traffic_analysis"
LOCAL_VIDEOS_DIR = PROJECT_DIR / "local_videos"
LOCAL_MODELS_DIR = PROJECT_DIR / "local_models"
