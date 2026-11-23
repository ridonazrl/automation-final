from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import traceback

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.post("/view")
async def api_view():
    try:
        loop = asyncio.get_event_loop()
        
        def process_sync():
            try:
                import tiktok_mobile
                print("[*] Memulai Auto-View Mobile (USB ADB)...")
                tiktok_mobile.main()
                print("[*] Selesai.")
            except Exception as e:
                print(f"[!] ERROR: {e}")
                traceback.print_exc()

        loop.run_in_executor(None, process_sync)
        return {"success": True, "message": "Diproses di background. Cek log Docker!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
def get_status():
    return {"status": "ok", "service": "views-tiktok-v2-be"}
