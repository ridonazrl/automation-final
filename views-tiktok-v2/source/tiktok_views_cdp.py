"""
tiktok_views_cdp.py
────────────────────
Tambah views TikTok dengan cara membuka & menonton video menggunakan
Chrome yang sudah login via CDP (sama seperti sistem tiktok_cdp_multi.py).

Cara kerja:
  1. Connect ke Chrome Windows yang sudah berjalan via CDP
  2. Ambil tab aktif (atau buka tab baru)
  3. Navigasi ke URL video TikTok
  4. Tunggu video ter-load & mulai diputar (= 1 view terhitung)
  5. Tonton beberapa detik + simulasi aktivitas manusia
  6. Ulangi untuk semua akun

Cara pakai:
  python tiktok_views_cdp.py
  python tiktok_views_cdp.py --url "https://..." --accounts akun1 akun2
  python tiktok_views_cdp.py --url "https://..." --repeat 3
"""

import os
import json
import time
import random
import argparse
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ─────────────────────────────────────────────────────────────
# Konfigurasi CDP (sama persis dengan tiktok_cdp_multi.py)
# ─────────────────────────────────────────────────────────────

ACCOUNT_PORT_MAP = {
    "akun1": 9222,  # Fatur Ikhsanudin
    "akun2": 9223,  # Ridetes7
    "akun3": 9224,  # Ridonajrul
    "akun4": 9225,  # Usertestpkl
    "akun5": 9226,  # Gptridho
}

DISPLAY_NAMES = {
    "akun1": "Fatur Ikhsanudin",
    "akun2": "Ridetes7",
    "akun3": "Ridonajrul",
    "akun4": "Usertestpkl",
    "akun5": "Gptridho",
}

HOST_IP = "172.18.0.1"

# Berapa detik nonton per sesi
WATCH_MIN = 20
WATCH_MAX = 45

# Delay antar akun (detik)
DELAY_MIN = 5
DELAY_MAX = 15

# File histori
HISTORY_FILE = "views_cdp_history.json"


# ─────────────────────────────────────────────────────────────
# Core: tonton video via CDP
# ─────────────────────────────────────────────────────────────

def watch_video_cdp(account_name: str, url: str, watch_seconds: int = None) -> dict:
    """
    Buka video TikTok di Chrome yang sudah login via CDP, tonton beberapa detik.

    Returns:
        dict: success, account, url, watched_seconds, error (opsional)
    """
    if account_name not in ACCOUNT_PORT_MAP:
        return {
            "success": False,
            "account": account_name,
            "url": url,
            "error": f"Akun '{account_name}' tidak ada di ACCOUNT_PORT_MAP",
        }

    port = ACCOUNT_PORT_MAP[account_name]
    name = DISPLAY_NAMES.get(account_name, account_name)
    cdp_url = f"http://{HOST_IP}:{port}"

    if watch_seconds is None:
        watch_seconds = random.randint(WATCH_MIN, WATCH_MAX)

    print(f"\n{'='*55}")
    print(f"[*] Akun   : {name} ({account_name}) — Port {port}")
    print(f"[*] URL    : {url}")
    print(f"[*] Tonton : {watch_seconds} detik")
    print(f"{'='*55}")

    with sync_playwright() as p:
        try:
            # 1. Connect ke Chrome Windows via CDP
            print(f"[*] Connecting ke CDP: {cdp_url} ...")
            browser = p.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0]

            # Ambil tab yang sudah ada (atau buat baru)
            if context.pages:
                page = context.pages[0]
            else:
                page = context.new_page()

            # 2. Navigasi ke video
            print(f"[*] Navigasi ke video...")
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            print(f"[+] Halaman ter-load")

            # 3. Tunggu video player muncul
            print(f"[*] Menunggu video player...")
            video_selectors = [
                "video",
                '[data-e2e="video-player"] video',
                ".tiktok-web-player video",
            ]
            video_found = False
            for sel in video_selectors:
                try:
                    page.wait_for_selector(sel, timeout=10000, state="attached")
                    video_found = True
                    print(f"[+] Video player ditemukan: {sel}")
                    break
                except PWTimeout:
                    continue

            if not video_found:
                print("[!] Video player tidak ditemukan, lanjut quand même...")

            # 4. Jeda awal agar video mulai load
            time.sleep(random.uniform(2.0, 4.0))

            # 5. Pastikan video diputar
            try:
                is_playing = page.evaluate("""
                    (() => {
                        const v = document.querySelector('video');
                        if (!v) return false;
                        if (v.paused) { v.play(); return false; }
                        return true;
                    })()
                """)
                print(f"[+] Video {'sudah' if is_playing else 'mulai'} diputar")
            except Exception:
                pass

            # Gerak mouse pertama (natural)
            page.mouse.move(
                random.randint(300, 800),
                random.randint(200, 500),
            )
            time.sleep(random.uniform(0.5, 1.2))

            # 6. Tonton dengan simulasi aktivitas manusia
            print(f"[*] Menonton selama {watch_seconds} detik...")
            elapsed = 0
            while elapsed < watch_seconds:
                chunk = min(random.randint(4, 8), watch_seconds - elapsed)
                time.sleep(chunk)
                elapsed += chunk

                # Gerak mouse acak
                if random.random() > 0.3:
                    page.mouse.move(
                        random.randint(200, 1000),
                        random.randint(150, 650),
                    )

                # Sesekali scroll kecil lalu balik
                if random.random() > 0.65:
                    scroll_down = random.randint(40, 120)
                    page.evaluate(f"window.scrollBy(0, {scroll_down})")
                    time.sleep(random.uniform(0.3, 0.8))
                    page.evaluate(f"window.scrollBy(0, -{scroll_down})")

                # Cek video masih jalan
                try:
                    page.evaluate("""
                        const v = document.querySelector('video');
                        if (v && v.paused) v.play();
                    """)
                except Exception:
                    pass

                remaining = watch_seconds - elapsed
                if remaining > 0:
                    print(f"    ⏱  {elapsed}s / {watch_seconds}s  ({remaining}s lagi...)")

            print(f"[✅] Selesai menonton {watch_seconds} detik untuk {name}")
            return {
                "success": True,
                "account": account_name,
                "url": url,
                "watched_seconds": watch_seconds,
            }

        except Exception as e:
            print(f"[!] Exception: {e}")
            # Screenshot debug
            try:
                debug_path = f"debug_views_cdp_{account_name}_{int(time.time())}.png"
                context.pages[0].screenshot(path=debug_path)
                print(f"[!] Screenshot disimpan: {debug_path}")
            except Exception:
                pass
            return {
                "success": False,
                "account": account_name,
                "url": url,
                "error": str(e),
            }
        finally:
            # JANGAN close browser — CDP hanya lepas koneksi
            pass


# ─────────────────────────────────────────────────────────────
# Histori
# ─────────────────────────────────────────────────────────────

def save_history(task: dict):
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            pass
    history.insert(0, task)
    history = history[:200]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────
# Orkestrasi multi-akun
# ─────────────────────────────────────────────────────────────

def run_views(url: str, accounts: list[str], repeat: int = 1):
    """
    Jalankan views untuk banyak akun, bisa repeat beberapa kali per akun.
    """
    print(f"\n{'='*55}")
    print(f"  👁️  TikTok Auto Views — CDP Mode")
    print(f"{'='*55}")
    print(f"  URL    : {url}")
    print(f"  Akun   : {', '.join(accounts)}")
    print(f"  Repeat : {repeat}x per akun")
    print(f"  Total  : {len(accounts) * repeat} sesi")
    print(f"  Host   : {HOST_IP}")
    print(f"{'='*55}\n")

    task = {
        "id": f"views_cdp_{int(time.time())}",
        "url": url,
        "accounts": accounts,
        "repeat": repeat,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": {"success": 0, "failed": 0},
        "details": [],
    }

    total = len(accounts) * repeat
    counter = 0

    for account_id in accounts:
        for r in range(repeat):
            counter += 1
            label = f"[{counter}/{total}]"

            if repeat > 1:
                print(f"\n{label} Akun: {account_id} — Sesi ke-{r+1}")
            else:
                print(f"\n{label} Akun: {account_id}")

            result = watch_video_cdp(account_id, url)
            task["details"].append(result)

            if result["success"]:
                task["results"]["success"] += 1
            else:
                task["results"]["failed"] += 1
                print(f"   ⚠️  Gagal: {result.get('error', 'Unknown')}")

            # Jeda antar sesi (kecuali yang terakhir)
            if counter < total:
                delay = random.randint(DELAY_MIN, DELAY_MAX)
                print(f"\n⏳ Jeda {delay} detik sebelum sesi berikutnya...")
                time.sleep(delay)

    # Ringkasan
    s = task["results"]["success"]
    f = task["results"]["failed"]
    task["status"] = "success" if f == 0 else ("failed" if s == 0 else "partial")

    print(f"\n{'='*55}")
    print(f"🏁 SELESAI")
    print(f"   ✅ Berhasil : {s} sesi")
    print(f"   ❌ Gagal    : {f} sesi")
    print(f"{'='*55}")

    save_history(task)
    print(f"💾 Hasil disimpan ke {HISTORY_FILE}")

    return task


# ─────────────────────────────────────────────────────────────
# CLI interaktif
# ─────────────────────────────────────────────────────────────

def interactive_mode():
    print("=" * 55)
    print("  👁️  TikTok Auto Views — CDP Mode")
    print("=" * 55)
    print(f"\n  Akun tersedia:")
    for acc_id, port in ACCOUNT_PORT_MAP.items():
        name = DISPLAY_NAMES.get(acc_id, acc_id)
        print(f"    {acc_id} — {name}  (CDP Port {port})")

    # URL
    url = input("\n📎 Masukkan URL video TikTok: ").strip()
    if not url or "tiktok.com" not in url:
        print("❌ URL tidak valid.")
        return

    # Pilih akun
    acc_keys = list(ACCOUNT_PORT_MAP.keys())
    print(f"\n👥 Pilih akun:")
    print(f"  [0] Semua akun ({len(acc_keys)} akun)")
    for i, acc_id in enumerate(acc_keys, 1):
        name = DISPLAY_NAMES.get(acc_id, acc_id)
        print(f"  [{i}] {acc_id} — {name}  (Port {ACCOUNT_PORT_MAP[acc_id]})")

    while True:
        raw = input("\nPilih akun (pisah koma, 0=semua): ").strip()
        if raw == "0":
            selected = acc_keys
            break
        try:
            choices = [int(x.strip()) for x in raw.split(",")]
            selected = []
            valid = True
            for c in choices:
                if 1 <= c <= len(acc_keys):
                    selected.append(acc_keys[c - 1])
                else:
                    print(f"   ⚠️  Nomor {c} tidak valid.")
                    valid = False
                    break
            if valid and selected:
                break
        except ValueError:
            print("   ⚠️  Format tidak valid. Contoh: 1,3")

    print(f"✅ Akun dipilih: {', '.join(selected)}")

    # Repeat
    while True:
        try:
            repeat_input = input("\n🔁 Berapa kali tiap akun menonton? [default: 1]: ").strip()
            repeat = int(repeat_input) if repeat_input else 1
            if repeat >= 1:
                break
            print("   ⚠️  Minimal 1.")
        except ValueError:
            repeat = 1
            break

    # Konfirmasi
    total = len(selected) * repeat
    print(f"\n📋 Ringkasan:")
    print(f"   URL    : {url}")
    print(f"   Akun   : {', '.join(selected)}")
    print(f"   Total  : {total} sesi menonton ({WATCH_MIN}–{WATCH_MAX} detik/sesi)")
    confirm = input("\n▶️  Lanjutkan? [y/N]: ").strip().lower()
    if confirm != "y":
        print("❌ Dibatalkan.")
        return

    run_views(url, selected, repeat)


def cli_mode():
    parser = argparse.ArgumentParser(description="TikTok Auto Views via CDP")
    parser.add_argument("--url", required=True, help="URL video TikTok")
    parser.add_argument(
        "--accounts",
        nargs="+",
        default=list(ACCOUNT_PORT_MAP.keys()),
        help="Nama akun (misal: akun1 akun2)",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Berapa kali tiap akun menonton (default: 1)",
    )
    parser.add_argument(
        "--watch",
        type=int,
        default=None,
        help="Durasi tonton tetap dalam detik (default: acak 20-45)",
    )
    args = parser.parse_args()

    # Override watch time jika diberikan
    global WATCH_MIN, WATCH_MAX
    if args.watch:
        WATCH_MIN = args.watch
        WATCH_MAX = args.watch

    run_views(args.url, args.accounts, args.repeat)


# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cli_mode()
    else:
        interactive_mode()
