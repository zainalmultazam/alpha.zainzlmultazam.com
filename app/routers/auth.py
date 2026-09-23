from fastapi import APIRouter, Request, Form
from fastapi.responses import JSONResponse
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/verify-pin")
async def api_verify_pin(pin: str = Form(...)):
    if str(pin).strip() == str(settings.ACCESS_PIN).strip():
        response = JSONResponse(content={"status": "success", "authenticated": True, "token": "pin_ok"})
        response.set_cookie(key="alpha_pin_auth", value="authenticated", max_age=2592000, httponly=False, samesite="lax")
        return response
    return JSONResponse(status_code=401, content={"status": "error", "message": "PIN Salah. Silakan coba lagi."})

@router.get("/status")
async def api_auth_status(request: Request):
    auth_cookie = request.cookies.get("alpha_pin_auth")
    return {"status": "success", "authenticated": auth_cookie == "authenticated"}

@router.post("/logout")
async def api_auth_logout():
    response = JSONResponse(content={"status": "success", "authenticated": False})
    response.delete_cookie("alpha_pin_auth")
    return response
