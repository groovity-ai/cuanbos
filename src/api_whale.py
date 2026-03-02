from fastapi import APIRouter
from whale_tracker import analyze_whale_sentiment
import traceback

router = APIRouter()

@router.get("/whales")
def get_whales():
    try:
        return analyze_whale_sentiment()
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()}
