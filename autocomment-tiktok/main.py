from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import os
import sys
import traceback
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class CommentRequest(BaseModel):
    url: str
    accounts: list[str] = ["akun1"]
    mood: str = "positive"
    context: str = ""
    per_account_comment: bool = True
    custom_prompt: str = ""

@app.post("/comment")
async def api_comment(req: CommentRequest):
    try:
        loop = asyncio.get_event_loop()
        
        def process_sync():
            try:
                import tiktok_comment
                print(f"[{datetime.now().strftime('%H.%M.%S')}] 🚀 Memulai Auto-Comment untuk {len(req.accounts)} akun...")
                print(f"[{datetime.now().strftime('%H.%M.%S')}] 📎 Target URL: {req.url}")
                print(f"[{datetime.now().strftime('%H.%M.%S')}] 🎭 Mood: {req.mood} | Konteks: {req.context[:50]}...")
                print(f"[{datetime.now().strftime('%H.%M.%S')}] ========================================")
                
                result = tiktok_comment.run_auto_comment(
                    req.url,
                    req.accounts,
                    req.mood,
                    context=req.context,
                    per_account_comment=req.per_account_comment,
                    preview=False,
                    custom_prompt=req.custom_prompt
                )
                
                print(f"[{datetime.now().strftime('%H.%M.%S')}] ========================================")
                print(f"[{datetime.now().strftime('%H.%M.%S')}] 🏁 SELESAI - Berhasil: {result.get('results', {}).get('success', 0)}, Gagal: {result.get('results', {}).get('failed', 0)}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H.%M.%S')}] ❌ ERROR: {e}")
                traceback.print_exc()

        loop.run_in_executor(None, process_sync)
        return {"success": True, "message": "Diproses di background. Cek log Docker!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
def get_status():
    return {"status": "ok"}
