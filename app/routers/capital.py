from typing import Optional
from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse
from app.config import settings
from app.engine.capital import log_capital_flow, get_capital_statement, delete_capital_entry
from app.engine.journal import get_performance_metrics
from app.engine.strategy import calculate_lot_size

router = APIRouter(tags=["Capital"])

@router.get("/api/capital/statement")
async def api_get_capital_statement(market: str = "IDX"):
    """Mengembalikan laporan neraca modal, HPP, kas, dan riwayat mutasi per pasar."""
    clean_m = (market or "IDX").upper().strip()
    return get_capital_statement(market=clean_m)

@router.post("/api/capital/log")
async def api_log_capital_flow(
    type: str = Form("DEPOSIT"),
    amount: float = Form(...),
    entry_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(""),
    market: str = Form("IDX")
):
    """Mencatat setoran modal (Top Up) atau penarikan dana (Withdrawal) per pasar."""
    clean_m = (market or "IDX").upper().strip()
    res = log_capital_flow(type, amount, entry_date, notes or "", market=clean_m)
    return res

@router.post("/api/capital/delete")
@router.post("/api/capital/delete/{entry_id}")
@router.delete("/api/capital/{entry_id}")
async def api_delete_capital_entry(entry_id: Optional[int] = None, entry_id_form: Optional[int] = Form(None, alias="entry_id")):
    """Menghapus riwayat mutasi modal jika ada kesalahan input."""
    eid = entry_id or entry_id_form
    if not eid:
        return {"status": "error", "message": "Missing entry_id"}
    ok = delete_capital_entry(eid)
    return {"status": "success" if ok else "error", "deleted": ok}

@router.post("/api/calculate-size")
async def api_calculate_size(
    capital: float = Form(...),
    risk_pct: float = Form(1.0),
    entry_price: float = Form(...),
    stop_loss: float = Form(...),
    target_price: Optional[float] = Form(None),
    market: str = Form("IDX")
):
    try:
        result = calculate_lot_size(capital, risk_pct, entry_price, stop_loss, target_price, market=market)
        return {"status": "success", "data": result}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

@router.get("/api/performance")
async def api_performance(capital: Optional[float] = None, market: str = "IDX", timeframe: str = "ALL"):
    clean_m = (market or "IDX").upper().strip()
    clean_tf = (timeframe or "ALL").upper().strip()
    base_cap = capital or (settings.DEFAULT_CAPITAL if clean_m == "IDX" else 5000.0) or 50000000.0
    metrics = get_performance_metrics(base_cap, market=clean_m, timeframe=clean_tf)
    return {"status": "success", "market": clean_m, "timeframe": clean_tf, "data": metrics}
