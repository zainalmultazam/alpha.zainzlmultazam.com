from fastapi import APIRouter
from app.engine.tracker import update_tracked_signals, get_tracker_dashboard_data, get_prediction_accuracy_scorecard
from app.engine.learner import get_active_learned_weights, calibrate_and_learn
from app.engine.post_mortem import get_all_post_mortems

router = APIRouter(prefix="/api/tracker", tags=["Tracker"])

@router.get("")
@router.get("/")
async def api_get_tracker(market: str = "IDX", timeframe: str = "ALL", auto_sync: bool = True):
    clean_m = (market or "IDX").upper().strip()
    clean_tf = (timeframe or "ALL").upper().strip()
    if auto_sync:
        try:
            update_tracked_signals(market=clean_m)
        except Exception:
            pass
    data = get_tracker_dashboard_data(market=clean_m, timeframe=clean_tf)
    data["ai_memory"] = get_active_learned_weights(market=clean_m)
    return {"status": "success", "market": clean_m, "timeframe": clean_tf, "data": data}

@router.post("/sync")
async def api_sync_tracker(market: str = "IDX", timeframe: str = "ALL"):
    clean_m = (market or "IDX").upper().strip()
    clean_tf = (timeframe or "ALL").upper().strip()
    res = update_tracked_signals(market=clean_m)
    data = get_tracker_dashboard_data(market=clean_m, timeframe=clean_tf)
    data["ai_memory"] = get_active_learned_weights(market=clean_m)
    return {"status": "success", "market": clean_m, "timeframe": clean_tf, "sync_result": res, "data": data}

@router.post("/calibrate")
async def api_calibrate_tracker(market: str = "IDX"):
    clean_m = (market or "IDX").upper().strip()
    calib = calibrate_and_learn(market=clean_m)
    data = get_tracker_dashboard_data(market=clean_m)
    data["ai_memory"] = calib
    return {"status": "success", "market": clean_m, "calibration": calib, "data": data}

@router.get("/post-mortems")
async def api_get_post_mortems(market: str = "IDX"):
    clean_m = (market or "IDX").upper().strip()
    data = get_all_post_mortems()
    return {"status": "success", "market": clean_m, "data": data}

@router.get("/prediction-scorecard")
async def api_get_prediction_scorecard(market: str = "IDX"):
    clean_m = (market or "IDX").upper().strip()
    data = get_prediction_accuracy_scorecard(market=clean_m)
    return {"status": "success", "market": clean_m, "data": data}

