from typing import Optional
from fastapi import APIRouter, Form
from app.engine.journal import (
    get_all_trades, 
    get_journal_stats, 
    log_trade, 
    close_trade, 
    update_trade,
    delete_trade
)
from app.services.telegram_bot import run_safety_sentinel_check

router = APIRouter(prefix="/api/journal", tags=["Journal"])

@router.get("")
@router.get("/")
async def api_get_journal(market: str = "IDX"):
    clean_m = (market or "IDX").upper().strip()
    return {
        "status": "success", 
        "market": clean_m, 
        "trades": get_all_trades(market=clean_m), 
        "stats": get_journal_stats(market=clean_m)
    }

@router.get("/stats")
async def api_journal_stats(market: str = "IDX"):
    clean_m = (market or "IDX").upper().strip()
    return {"status": "success", "market": clean_m, "data": get_journal_stats(market=clean_m)}

@router.post("/log")
async def api_log_trade(
    ticker: str = Form(...),
    entry_price: float = Form(...),
    stop_loss: float = Form(...),
    target_price: float = Form(...),
    lots: float = Form(...),
    setup_name: str = Form("Alpha Setup"),
    market: str = Form("IDX")
):
    clean_m = (market or "IDX").upper().strip()
    trade_id = log_trade(ticker, entry_price, stop_loss, target_price, lots, setup_name, market=clean_m)
    return {"status": "success", "trade_id": trade_id, "market": clean_m}

@router.post("/update")
@router.post("/update/{trade_id}")
@router.put("/{trade_id}")
async def api_update_trade(
    trade_id: Optional[int] = None,
    trade_id_form: Optional[int] = Form(None, alias="trade_id"),
    lots: float = Form(...),
    entry_price: float = Form(...),
    stop_loss: float = Form(...),
    target_price: float = Form(...),
    setup_name: Optional[str] = Form(""),
    notes: Optional[str] = Form(""),
    exit_price: Optional[float] = Form(None),
    exit_reason: Optional[str] = Form(None),
    buy_fee_pct: Optional[float] = Form(None),
    sell_fee_pct: Optional[float] = Form(None)
):
    tid = trade_id or trade_id_form
    if not tid:
        return {"status": "error", "message": "Missing trade_id"}
    ok = update_trade(
        trade_id=tid,
        lots=lots,
        entry_price=entry_price,
        stop_loss=stop_loss,
        target_price=target_price,
        setup_name=setup_name or "",
        notes=notes or "",
        exit_price=exit_price,
        exit_reason=exit_reason,
        buy_fee_pct=buy_fee_pct,
        sell_fee_pct=sell_fee_pct
    )
    return {"status": "success" if ok else "error"}

@router.post("/close")
async def api_close_trade(
    trade_id: int = Form(...),
    exit_price: float = Form(...),
    notes: Optional[str] = Form(""),
    exit_reason: Optional[str] = Form("MANUAL"),
    buy_fee_pct: Optional[float] = Form(None),
    sell_fee_pct: Optional[float] = Form(None)
):
    ok = close_trade(
        trade_id=trade_id, 
        exit_price=exit_price, 
        notes=notes or "", 
        exit_reason=exit_reason or "MANUAL",
        buy_fee_pct=buy_fee_pct,
        sell_fee_pct=sell_fee_pct
    )
    return {"status": "success" if ok else "error"}

@router.post("/delete")
@router.post("/delete/{trade_id}")
@router.delete("/{trade_id}")
async def api_delete_trade(trade_id: Optional[int] = None, trade_id_form: Optional[int] = Form(None, alias="trade_id")):
    tid = trade_id or trade_id_form
    if not tid:
        return {"status": "error", "message": "Missing trade_id"}
    ok = delete_trade(tid)
    return {"status": "success" if ok else "error", "deleted": ok}

@router.get("/check-safety")
async def api_check_safety():
    res = await run_safety_sentinel_check()
    return {"status": "success", "data": res, "message": "Safety Sentinel check executed"}
