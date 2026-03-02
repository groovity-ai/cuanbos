from fastapi import APIRouter, Response
from fastapi.responses import Response
from chart_generator import generate_chart
import traceback

router = APIRouter()

@router.get("/chart/{market_type}/{ticker}")
async def get_chart(market_type: str, ticker: str, days: int = 60):
    try:
        image_bytes = generate_chart(ticker.upper(), market_type, days)
        return Response(content=image_bytes, media_type="image/png")
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()}
