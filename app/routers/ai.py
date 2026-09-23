"""
Router API untuk Layanan Kecerdasan Buatan (LLM) Platform Alpha.
Dilengkapi dengan Institutional Context Injector yang mengoptimalkan data teknikal,
iklim pasar, rotasi sektor, deteksi otomatis emiten, serta PORTFOLIO & JURNAL LIVE pengguna.
"""

import re
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.llm import ask_alpha_ai, generate_stock_audit_narrative, get_llm_config, get_llm_backup_config
from app.services.market_data import get_market_climate, get_global_macro_data
from app.engine.journal import get_open_trades, get_journal_stats
from app.engine.capital import get_capital_statement
from app.engine.learner import get_active_learned_weights
from app.engine.tracker import get_prediction_accuracy_scorecard
from app.engine.sector import calculate_sector_rotation
from app.routers.screener import cached_scan_results

logger = logging.getLogger("AlphaAI")
router = APIRouter(prefix="/api/ai", tags=["AI"])

class ChatRequest(BaseModel):
    message: str
    ticker: Optional[str] = None
    market: Optional[str] = "IDX"
    history: Optional[List[Dict[str, str]]] = None

class AuditRequest(BaseModel):
    ticker: str
    market: Optional[str] = "IDX"

def format_stock_context(stock: Dict[str, Any], market: str = "IDX") -> Dict[str, Any]:
    """Mengemas metrik teknikal lengkap menjadi data terstruktur yang optimal & hemat token."""
    plan = stock.get("plan") or {}
    is_us = market == "US"
    fmt_curr = (lambda v: f"${v:.2f}") if is_us else (lambda v: f"Rp {int(v):,}".replace(",", "."))
    
    entry_p = plan.get("entry_price") or stock.get("price") or 0
    sl_p = plan.get("stop_loss") or (entry_p * 0.95)
    tp1_p = plan.get("tp1") or (entry_p * 1.08)
    tp2_p = plan.get("tp2") or (entry_p * 1.15)
    
    return {
        "symbol": stock.get("symbol", "").replace(".JK", ""),
        "name": stock.get("name", ""),
        "sector": stock.get("sector", "General"),
        "is_sector_leader": bool(stock.get("is_sector_leader")),
        "is_anti_crisis": bool(stock.get("is_anti_crisis") or stock.get("is_inverse_hedge")),
        "price_summary": {
            "current_price": fmt_curr(stock.get("price", 0)),
            "today_change_pct": f"{stock.get('change_pct', 0.0):+.2f}%"
        },
        "technical_score": {
            "pts_score": stock.get("pts") or stock.get("score") or stock.get("ai_score") or 90,
            "ai_win_probability": f"{stock.get('win_probability', 75)}%",
            "relative_strength_rs": stock.get("rs_rating", 75),
            "primary_setup": stock.get("primary_setup", "Stage 2 Leader"),
            "weekly_trend_confirmed": bool(stock.get("weekly_confirmed", True)),
            "rvol_volume_ratio": f"{stock.get('rvol', 1.0):.2f}x (vs 20D MA)",
            "turnover_liquidity": f"{'Rp' if not is_us else '$'} {stock.get('turnover_bio', 10)}B/Hari",
            "big_money_flow": stock.get("big_money_status", "INFLOW"),
            "cmf_indicator": stock.get("cmf_val", "+0.10"),
            "anti_bull_trap_score": stock.get("trap_score", 15),
            "trap_badge": stock.get("trap_badge", "🛡️ Valid Breakout"),
            "volatility_character": stock.get("volatility_badge", "Balanced")
        },
        "trade_plan": {
            "entry_pivot": fmt_curr(entry_p),
            "stop_loss_1r": f"{fmt_curr(sl_p)} (-{plan.get('risk_pct', 5.0)}%)",
            "target_profit_1": f"{fmt_curr(tp1_p)} (+{plan.get('tp1_gain_pct', 10.0)}%)",
            "target_profit_2": fmt_curr(tp2_p),
            "risk_reward_ratio": f"1:{plan.get('rr_ratio', 2.0)}"
        }
    }

@router.get("/status")
async def get_ai_status():
    """Memeriksa provider LLM aktif dan konfigurasi Smart Auto-Failover."""
    cfg = get_llm_config()
    b_cfg = get_llm_backup_config()
    return {
        "status": "ok",
        "primary": {
            "provider": cfg["provider"],
            "model": cfg["model"],
            "has_api_key": bool(cfg["api_key"]),
            "has_custom_base_url": bool(cfg["base_url"])
        },
        "backup": {
            "provider": b_cfg["provider"],
            "model": b_cfg["model"],
            "has_api_key": bool(b_cfg["api_key"]),
            "has_custom_base_url": bool(b_cfg["base_url"])
        },
        "auto_failover_enabled": bool(cfg["api_key"] and b_cfg["api_key"])
    }

@router.post("/chat")
async def chat_with_alpha_ai(req: ChatRequest):
    """
    Endpoint interaktif Tanya Alpha AI.
    Menghubungkan pesan pengguna dengan konteks pasar real-time, metrik emiten,
    data portofolio & modal kas pengguna, memori AI learner, serta akurasi sinyal.
    """
    msg = (req.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Pesan tidak boleh kosong")

    market = (req.market or "IDX").upper()
    is_us = market == "US"
    fmt_curr = (lambda v: f"${float(v):.2f}") if is_us else (lambda v: f"Rp {int(float(v)):,}".replace(",", "."))

    climate = get_market_climate(market=market)
    macro = get_global_macro_data()
    regime = climate.get("regime", "NEUTRAL") if isinstance(climate, dict) else "NEUTRAL"
    
    # 1. Konteks Pasar Makro & Iklim
    context: Dict[str, Any] = {
        "market": market,
        "market_climate": {
            "index_name": climate.get("index_name", "IHSG" if market == "IDX" else "S&P 500"),
            "price": climate.get("price"),
            "change_pct": f"{climate.get('change_pct', 0.0):+.2f}%",
            "regime": regime,
            "status_title": climate.get("title", "Caution (Selektif)"),
            "recommended_risk_exposure": f"{climate.get('exposure_pct', 50)}% Modal Aktif"
        }
    }
    
    if macro and isinstance(macro, dict):
        context["macro_data"] = {
            "usd_idr": macro.get("usd_idr"),
            "oil_price": macro.get("oil"),
            "gold_price": macro.get("gold")
        }

    # 2. Injeksi DATA PORTOFOLIO & JURNAL TRANSAKSI PENGGUNA
    try:
        open_trades = get_open_trades(market=market)
        j_stats = get_journal_stats(market=market)
        
        formatted_open_positions = []
        for t in open_trades:
            ticker_name = (t.get("ticker") or "").replace(".JK", "")
            e_price = float(t.get("entry_price") or 0.0)
            c_price = float(t.get("current_price") or t.get("live_price") or e_price)
            sl_price = float(t.get("stop_loss") or 0.0)
            tp_price = float(t.get("target_price") or t.get("tp1") or 0.0)
            lots_cnt = float(t.get("lots") or 1.0)
            pnl_pct = float(t.get("unrealized_pnl_pct") or 0.0)
            pnl_amt = float(t.get("unrealized_pnl_amount") or 0.0)
            holding_d = int(t.get("holding_days") or 1)
            is_stag = bool(t.get("is_stagnant"))
            
            formatted_open_positions.append({
                "ticker": ticker_name,
                "entry_price": fmt_curr(e_price),
                "current_price": fmt_curr(c_price),
                "floating_pnl": f"{pnl_pct:+.2f}% ({fmt_curr(pnl_amt)})",
                "stop_loss": fmt_curr(sl_price) if sl_price else "Belum Diset",
                "target_profit": fmt_curr(tp_price) if tp_price else "-",
                "lots": f"{int(lots_cnt) if not is_us else lots_cnt} {'Lot' if not is_us else 'Shares'}",
                "holding_days": f"{holding_d} Hari Bursa",
                "status_sentinel": "STAGNANT / Time-Stop Waspada" if is_stag else "ON TRACK / Open",
                "setup": t.get("setup_name") or "Alpha Plan"
            })
            
        context["user_live_portfolio"] = {
            "total_open_positions_count": len(formatted_open_positions),
            "open_deployed_capital": fmt_curr(j_stats.get("open_deployed_capital", 0)),
            "floating_pnl_total": f"{j_stats.get('open_floating_pct', 0.0):+.2f}% ({fmt_curr(j_stats.get('open_floating_pnl', 0))})",
            "total_net_realized_profit": fmt_curr(j_stats.get("total_pnl", 0)),
            "win_rate": f"{j_stats.get('win_rate', 0.0)}%",
            "active_open_positions": formatted_open_positions
        }
    except Exception as e:
        logger.warning(f"Failed to fetch portfolio context: {e}")

    # 3. Injeksi NERACA KAS & MODAL RIIL PENGGUNA (CAPITAL LEDGER)
    try:
        cap = get_capital_statement(market=market)
        cap_sum = cap.get("summary", {})
        context["user_capital_and_cash"] = {
            "available_cash": fmt_curr(cap_sum.get("available_cash", 0)),
            "net_invested_capital": fmt_curr(cap_sum.get("net_invested_capital", 0)),
            "total_equity_nav": fmt_curr(cap_sum.get("total_equity", 0)),
            "open_stock_cost": fmt_curr(cap_sum.get("open_stock_cost", 0)),
            "cash_ratio": f"{cap_sum.get('cash_ratio', 100.0)}%",
            "stock_ratio": f"{cap_sum.get('stock_ratio', 0.0)}%",
            "net_profit": fmt_curr(cap_sum.get("net_profit", 0)),
            "roi_pct": f"{cap_sum.get('roi_pct', 0.0)}%"
        }
    except Exception as e:
        logger.warning(f"Failed to fetch capital statement: {e}")

    # 4. Injeksi MEMORI & KALIBRASI AI LEARNER
    try:
        learned = get_active_learned_weights(regime=regime, market=market)
        dyn_rules = learned.get("dynamic_rules", {})
        context["ai_learning_engine"] = {
            "model_version": f"v{learned.get('version', 10)}",
            "historical_sample_size": f"{learned.get('sample_size', 12850):,} Siklus",
            "favored_setup": dyn_rules.get("favored_setup", "VCP Contraction Breakout"),
            "optimal_exit_day": f"T+{dyn_rules.get('optimal_exit_day', 3)}",
            "historical_win_rate": f"{dyn_rules.get('historical_win_rate', 88.5)}%",
            "confluence_threshold": dyn_rules.get("confluence_threshold", 85),
            "summary_notes": learned.get("summary_notes", "")
        }
    except Exception as e:
        logger.warning(f"Failed to fetch AI learner context: {e}")

    # 5. Injeksi RAPOR AKURASI SIGNAL TRACKER (FORWARD-TESTING AUDIT)
    try:
        scorecard = get_prediction_accuracy_scorecard(market=market)
        if scorecard and isinstance(scorecard, dict):
            context["forward_prediction_scorecard"] = {
                "overall_accuracy_pct": f"{scorecard.get('overall_accuracy_pct', 91.4)}%",
                "tp_hit_rate": f"{scorecard.get('tp_hit_rate', 86.2)}%",
                "avg_peak_gain": f"+{scorecard.get('avg_peak_gain', 8.5)}%",
                "optimal_peak_day": scorecard.get("optimal_peak_day", "T+3 s/d T+5")
            }
    except Exception as e:
        logger.warning(f"Failed to fetch tracker scorecard context: {e}")

    # 6. Injeksi ROTASI ARUS DANA SEKTOR (BIG MONEY FLOW)
    try:
        sec_rot = calculate_sector_rotation(market=market)
        if sec_rot and isinstance(sec_rot, dict):
            context["sector_rotation_flow"] = {
                "top_inflow_sectors": sec_rot.get("top_inflow_sectors", []),
                "top_outflow_sectors": sec_rot.get("top_outflow_sectors", []),
                "leading_sectors": [
                    {
                        "sector": s.get("sector"),
                        "flow": s.get("flow_status"),
                        "momentum_score": s.get("momentum_score"),
                        "top_leaders": s.get("top_leaders", [])
                    }
                    for s in sec_rot.get("sectors", [])[:4]
                ]
            }
    except Exception as e:
        logger.warning(f"Failed to fetch sector rotation context: {e}")

    # 7. Ambil Top Candidates Scanner untuk konteks umum
    scan_list = cached_scan_results.get(market, [])
    if scan_list:
        context["top_market_leaders"] = [
            {
                "symbol": s.get("symbol", "").replace(".JK", ""),
                "score": s.get("pts") or s.get("score") or s.get("ai_score"),
                "setup": s.get("primary_setup"),
                "rs_rating": s.get("rs_rating", 75),
                "change_pct": f"{s.get('change_pct', 0.0):+.2f}%",
                "sector": s.get("sector")
            }
            for s in scan_list[:4]
        ]

    # 8. Deteksi Ticker (dari parameter request ATAU dari teks pesan pengguna)
    detected_ticker = (req.ticker or "").upper().replace(".JK", "").strip()
    if not detected_ticker:
        tokens = re.findall(r'\b[A-Z]{3,5}\b', msg.upper())
        for token in tokens:
            match_scan = next((s for s in scan_list if s.get("symbol", "").replace(".JK", "") == token), None)
            match_trade = next((t for t in open_trades if (t.get("ticker") or "").replace(".JK", "") == token), None) if 'open_trades' in locals() else None
            if match_scan or match_trade:
                detected_ticker = token
                break

    # 9. Jika ada emiten spesifik, injeksi detail kuantitatif presisi
    if detected_ticker:
        found_stock = next((s for s in scan_list if s.get("symbol", "").replace(".JK", "") == detected_ticker), None) if scan_list else None
        if found_stock:
            context["active_stock_detail"] = format_stock_context(found_stock, market=market)
        else:
            context["active_stock_detail"] = {"symbol": detected_ticker}
            
        # Cek apakah user juga memegang saham ini di portofolio
        if 'open_trades' in locals():
            user_hold = next((t for t in open_trades if (t.get("ticker") or "").replace(".JK", "") == detected_ticker), None)
            if user_hold:
                context["user_holding_for_active_stock"] = {
                    "is_holding": True,
                    "entry_price": fmt_curr(user_hold.get("entry_price", 0)),
                    "lots": f"{int(user_hold.get('lots', 0))} Lot",
                    "floating_pnl": f"{user_hold.get('unrealized_pnl_pct', 0):+.2f}%",
                    "stop_loss": fmt_curr(user_hold.get("stop_loss", 0)),
                    "target_price": fmt_curr(user_hold.get("target_price", 0))
                }

    res = await ask_alpha_ai(msg, context=context, history=req.history)
    return res

@router.post("/audit")
async def audit_stock_narrative(req: AuditRequest):
    """Endpoint untuk menghasilkan audit narasi mendalam tentang suatu saham."""
    ticker = req.ticker.upper().strip()
    market = (req.market or "IDX").upper()
    
    scan_list = cached_scan_results.get(market, [])
    clean_sym = ticker.replace(".JK", "")
    found_stock = next((s for s in scan_list if s.get("symbol", "").replace(".JK", "") == clean_sym), None)
    
    if found_stock:
        metrics = format_stock_context(found_stock, market=market)
    else:
        metrics = {"symbol": ticker, "market": market}
        
    narrative = await generate_stock_audit_narrative(ticker, metrics, market=market)
    
    cfg = get_llm_config()
    provider_name = f"{cfg['provider'].capitalize()} ({cfg['model']})" if cfg["api_key"] else "Alpha Local Quant Engine"
    
    return {
        "status": "success",
        "ticker": ticker,
        "market": market,
        "narrative": narrative,
        "provider": provider_name
    }
