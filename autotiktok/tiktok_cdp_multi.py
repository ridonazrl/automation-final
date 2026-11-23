import time
import random
from datetime import datetime
from playwright.sync_api import sync_playwright

ACCOUNT_PORT_MAP = {
    "akun1": 9222, "akun2": 9223, "akun3": 9224, "akun4": 9225, "akun5": 9226,
}
HOST_IP = "172.18.0.1"

def log(msg):
    print(f"[{datetime.now().strftime('%H.%M.%S')}] {msg}", flush=True)

def like_tiktok(account_name: str, url: str):
    if account_name not in ACCOUNT_PORT_MAP:
        log(f"❌ Akun {account_name} gak ada!")
        return False
        
    port = ACCOUNT_PORT_MAP[account_name]
    cdp_url = f"http://{HOST_IP}:{port}"
    
    log(f"========================================")
    log(f"[*] Memproses: {account_name} (Port {port})")
    log(f"[*] Connecting ke Chrome CDP port {port}...")
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            
            log(f"🌐 Membuka URL: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            log(f"⏳ Menunggu video & UI render (5 detik)...")
            time.sleep(5) 
            
            log(f"🖱️  Menggerakkan mouse (human-like)...")
            page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            time.sleep(1)
            
            log(f"🔍 Mencari tombol Like (dengan retry)...")
            
            # --- OPTIMASI: Retry Logic ---
            selectors = [
                '[data-e2e="like-icon"]',
                'button[aria-label*="Like" i]',
                'button[aria-label*="Suka" i]',
                'span[class*="like"]'
            ]
            
            clicked = False
            max_retries = 3
            
            for attempt in range(1, max_retries + 1):
                log(f"  [Attempt {attempt}/{max_retries}] Mencari tombol...")
                
                for sel in selectors:
                    try:
                        btn = page.locator(sel).first
                        # Wait for selector visible, bukan cuma count
                        btn.wait_for(state="visible", timeout=5000)
                        
                        aria_before = btn.get_attribute("aria-label") or ""
                        
                        log(f"  🎯 Tombol ditemukan: {sel}")
                        btn.click(timeout=5000)
                        time.sleep(2)
                        
                        aria_after = btn.get_attribute("aria-label") or ""
                        if aria_before != aria_after:
                            log(f"  ✅ State berubah: '{aria_before}' -> '{aria_after}'")
                        else:
                            log(f"  ⚠️  Klik berhasil, tapi state gak berubah (mungkin sudah di-like)")
                        
                        clicked = True
                        break
                    except Exception:
                        continue
                
                if clicked:
                    break
                
                # Kalau belum ketemu, tunggu dan coba lagi (kecuali attempt terakhir)
                if attempt < max_retries:
                    log(f"  ⏳ Tombol belum muncul, tunggu 3 detik...")
                    time.sleep(3)
            
            if not clicked:
                log(f"❌ Tombol Like tidak ditemukan setelah {max_retries} percobaan.")
                page.screenshot(path=f"/tmp/tiktok_fail_{account_name}.png")
                log(f"📸 Screenshot disimpan di /tmp/tiktok_fail_{account_name}.png")
                return False
            
            log(f"✅ Selesai memproses {account_name}.")
            return True
            
        except Exception as e:
            log(f"❌ Error pada {account_name}: {e}")
            return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 tiktok_cdp_multi.py <URL_VIDEO> [NAMA_AKUN]")
        sys.exit(1)
    
    url = sys.argv[1]
    account = sys.argv[2] if len(sys.argv) > 2 else "akun1"
    like_tiktok(account, url)
