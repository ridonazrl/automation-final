from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tiktok_cdp_multi import like_tiktok
import requests
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ACCOUNT_PORT_MAP = {
    "akun1": 9222, "akun2": 9223, "akun3": 9224, "akun4": 9225, "akun5": 9226,
}

class TikTokRequest(BaseModel):
    url: str
    accounts: list[str]

class TikTokSingleRequest(BaseModel):
    url: str
    account: str

@app.post("/like")
def api_like_batch(req: TikTokRequest):
    for akun in req.accounts:
        like_tiktok(akun, req.url)
    return {"success": True, "message": f"Memproses {len(req.accounts)} akun."}

@app.post("/like/single")
def api_like_single(req: TikTokSingleRequest):
    berhasil = like_tiktok(req.account, req.url)
    return {"success": berhasil, "message": f"Selesai memproses {req.account}."}

@app.get("/status")
def get_status():
    return {"success": True, "status": "ok"}

# Endpoint buat FE ngecek status tiap akun
@app.get("/browsers/check/{account_id}")
def check_browser(account_id: str):
    port = ACCOUNT_PORT_MAP.get(account_id)
    if not port:
        return {"online": False, "latency": 0}

    start = time.time()
    try:
        # Nembak ke Host Docker (172.18.0.1) dari dalam container
        r = requests.get(f"http://172.18.0.1:{port}/json/version", timeout=2)
        if r.status_code == 200:
            latency = int((time.time() - start) * 1000)
            return {"online": True, "latency": latency}
        else:
            return {"online": False, "latency": 0}
    except Exception:
        return {"online": False, "latency": 0}
