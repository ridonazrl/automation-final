"""
tiktok_views_scroll_cdp.py
───────────────────────────
Views TikTok via scroll cycle — semua akun jalan BERSAMAAN (parallel).

Alur tiap akun (di thread masing-masing):
  1. Connect ke Chrome CDP akun tersebut
  2. Buka URL video TARGET
  3. Loop N siklus:
       Tonton video ke-1 (target)
       → scroll bawah ke video ke-2 → tonton sebentar
       → scroll atas balik ke video ke-1
       = +1 view estimasi
  4. Selesai, thread berhenti

Cara pakai:
  python tiktok_views_scroll_cdp.py
  python tiktok_views_scroll_cdp.py --url "https://..." --accounts akun1 akun2 --cycles 5
"""

import os
import json
import time
import random
import argparse
import threading
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ─────────────────────────────────────────────────────────────
# Lock agar print & file tidak tabrakan antar thread
# ─────────────────────────────────────────────────────────────

_print_lock = threading.Lock()
_file_lock  = threading.Lock()

def tprint(account: str, msg: str):
    """Thread-safe print dengan label akun di depan."""
    with _print_lock:
        print(f"[{account:5s}] {msg}")

# ─────────────────────────────────────────────────────────────
# Konfigurasi CDP
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

# ── Timing ───────────────────────────────────────────────────

TARGET_WATCH_MIN = 8    # detik tonton video target per siklus
TARGET_WATCH_MAX = 20
NEXT_WATCH_MIN   = 3    # detik tonton video ke-2
NEXT_WATCH_MAX   = 8

HISTORY_FILE = "views_scroll_history.json"

# ─────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────

def ensure_playing(page):
    try:
        page.evaluate("""
            const videos = document.querySelectorAll('video');
            for (const v of videos) { if (v.paused) v.play(); }
        """)
    except Exception:
        pass

def human_pause(min_s: float, max_s: float):
    time.sleep(random.uniform(min_s, max_s))

def swipe_down(page):
    sx = random.randint(400, 700)
    sy = random.randint(550, 650)
    ey = random.randint(100, 200)
    page.mouse.move(sx, sy)
    human_pause(0.1, 0.3)
    page.mouse.down()
    steps = random.randint(8, 15)
    for i in range(steps):
        p = (i + 1) / steps
        page.mouse.move(sx + random.randint(-5, 5), sy + (ey - sy) * p)
        time.sleep(random.uniform(0.02, 0.06))
    page.mouse.up()
    human_pause(0.3, 0.6)

def swipe_up(page):
    sx = random.randint(400, 700)
    sy = random.randint(100, 200)
    ey = random.randint(550, 650)
    page.mouse.move(sx, sy)
    human_pause(0.1, 0.3)
    page.mouse.down()
    steps = random.randint(8, 15)
    for i in range(steps):
        p = (i + 1) / steps
        page.mouse.move(sx + random.randint(-5, 5), sy + (ey - sy) * p)
        time.sleep(random.uniform(0.02, 0.06))
    page.mouse.up()
    human_pause(0.3, 0.6)

def scroll_to_next(page):
    if random.random() > 0.3:
        swipe_down(page)
    else:
        page.mouse.click(random.randint(400, 700), random.randint(300, 500))
        human_pause(0.2, 0.4)
        page.keyboard.press("ArrowDown")
        human_pause(0.3, 0.6)

def scroll_to_prev(page):
    if random.random() > 0.3:
        swipe_up(page)
    else:
        page.mouse.click(random.randint(400, 700), random.randint(300, 500))
        human_pause(0.2, 0.4)
        page.keyboard.press("ArrowUp")
        human_pause(0.3, 0.6)

def wait_video_load(page, timeout: float = 8.0):
    try:
        page.wait_for_function(
            "() => { const v = document.querySelector('video'); return v && v.readyState >= 2; }",
            timeout=timeout * 1000,
        )
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────
# Core: satu akun di satu thread
# ─────────────────────────────────────────────────────────────

def scroll_view_cycles(
    account_name: str,
    target_url: str,
    cycles: int,
    results: dict,          # shared dict untuk kumpulkan hasil
):
    """Dijalankan di thread terpisah per akun."""
    if account_name not in ACCOUNT_PORT_MAP:
        results[account_name] = {
            "success": False,
            "error": f"Akun tidak ada di mapping",
        }
        return

    port    = ACCOUNT_PORT_MAP[account_name]
    name    = DISPLAY_NAMES.get(account_name, account_name)
    cdp_url = f"http://{HOST_IP}:{port}"

    tprint(account_name, f"Start — {name} (Port {port}) — {cycles} siklus")

    with sync_playwright() as p:
        try:
            tprint(account_name, f"Connecting ke CDP {cdp_url}...")
            browser = p.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0]
            page    = context.pages[0] if context.pages else context.new_page()

            tprint(account_name, "Buka video target...")
            page.goto(target_url, timeout=60000, wait_until="domcontentloaded")
            human_pause(3.0, 5.0)

            try:
                page.wait_for_selector("video", timeout=12000, state="attached")
                tprint(account_name, "Video player siap ✓")
            except PWTimeout:
                tprint(account_name, "Video player timeout, lanjut...")

            ensure_playing(page)
            page.mouse.move(random.randint(300, 800), random.randint(200, 500))
            human_pause(1.0, 2.0)

            view_count = 0

            for cycle in range(1, cycles + 1):
                tprint(account_name, f"Siklus {cycle}/{cycles}...")

                # 1. Tonton video TARGET
                wt = random.uniform(TARGET_WATCH_MIN, TARGET_WATCH_MAX)
                tprint(account_name, f"  [1] Tonton TARGET {wt:.0f}s")
                elapsed = 0
                while elapsed < wt:
                    chunk = min(random.uniform(2.0, 4.0), wt - elapsed)
                    time.sleep(chunk)
                    elapsed += chunk
                    if random.random() > 0.5:
                        page.mouse.move(random.randint(200, 900), random.randint(150, 600))
                    ensure_playing(page)

                # 2. Scroll ke video ke-2
                tprint(account_name, "  [2] Scroll ke video ke-2")
                scroll_to_next(page)
                human_pause(1.0, 2.5)
                wait_video_load(page)
                ensure_playing(page)

                # 3. Tonton video ke-2
                wn = random.uniform(NEXT_WATCH_MIN, NEXT_WATCH_MAX)
                tprint(account_name, f"  [3] Tonton video ke-2 {wn:.0f}s")
                elapsed = 0
                while elapsed < wn:
                    chunk = min(random.uniform(1.5, 3.0), wn - elapsed)
                    time.sleep(chunk)
                    elapsed += chunk
                    if random.random() > 0.6:
                        page.mouse.move(random.randint(200, 900), random.randint(150, 600))
                    ensure_playing(page)

                # 4. Scroll balik ke TARGET
                tprint(account_name, "  [4] Scroll balik ke TARGET")
                scroll_to_prev(page)
                human_pause(1.0, 2.5)
                wait_video_load(page)
                ensure_playing(page)

                view_count += 1
                tprint(account_name, f"  ✅ Siklus {cycle} selesai (total: {view_count})")

                if cycle < cycles:
                    time.sleep(random.uniform(1.5, 3.0))

            tprint(account_name, f"🏁 SELESAI — {view_count} siklus")
            results[account_name] = {"success": True, "cycles_completed": view_count}

        except Exception as e:
            tprint(account_name, f"❌ Exception: {e}")
            try:
                path = f"debug_{account_name}_{int(time.time())}.png"
                context.pages[0].screenshot(path=path)
                tprint(account_name, f"Screenshot: {path}")
            except Exception:
                pass
            results[account_name] = {"success": False, "error": str(e)}
        finally:
            pass  # Jangan close — CDP saja

# ─────────────────────────────────────────────────────────────
# Histori (thread-safe)
# ─────────────────────────────────────────────────────────────

def save_history(task: dict):
    with _file_lock:
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
# Orkestrasi PARALLEL
# ─────────────────────────────────────────────────────────────

def run_all_parallel(url: str, accounts: list[str], cycles: int = 3):
    print(f"\n{'='*58}")
    print(f"  👁️  TikTok Auto Views — Scroll Cycle (PARALLEL)")
    print(f"{'='*58}")
    print(f"  URL          : {url}")
    print(f"  Akun         : {', '.join(accounts)}")
    print(f"  Siklus/akun  : {cycles}x")
    print(f"  Mode         : 🔀 Semua akun jalan BERSAMAAN")
    print(f"{'='*58}\n")

    results  = {}   # dikisi oleh tiap thread
    threads  = []
    start_at = datetime.now()

    # Buat dan start semua thread sekaligus
    for account_id in accounts:
        t = threading.Thread(
            target=scroll_view_cycles,
            args=(account_id, url, cycles, results),
            name=account_id,
            daemon=True,
        )
        threads.append(t)

    with _print_lock:
        print(f"🚀 Start {len(threads)} thread sekaligus...\n")

    for t in threads:
        t.start()
        # Sedikit stagger (0.5-1.5 detik) agar tidak semua hit CDP di detik yang sama
        time.sleep(random.uniform(0.5, 1.5))

    # Tunggu semua thread selesai
    for t in threads:
        t.join()

    # Ringkasan
    duration = (datetime.now() - start_at).seconds
    success  = sum(1 for r in results.values() if r.get("success"))
    failed   = len(results) - success
    total_cycles = sum(r.get("cycles_completed", 0) for r in results.values())

    print(f"\n{'='*58}")
    print(f"🏁 SEMUA THREAD SELESAI  ({duration}s)")
    print(f"{'='*58}")
    for acc_id, r in results.items():
        name = DISPLAY_NAMES.get(acc_id, acc_id)
        if r.get("success"):
            print(f"  ✅ {acc_id:6s} ({name}) — {r['cycles_completed']} siklus")
        else:
            print(f"  ❌ {acc_id:6s} ({name}) — {r.get('error', 'Unknown')}")
    print(f"{'─'*58}")
    print(f"  Total siklus : {total_cycles}")
    print(f"  Berhasil     : {success} akun")
    print(f"  Gagal        : {failed} akun")
    print(f"{'='*58}")

    # Simpan histori
    task = {
        "id": f"scroll_parallel_{int(time.time())}",
        "url": url,
        "accounts": accounts,
        "cycles_per_account": cycles,
        "timestamp": start_at.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_seconds": duration,
        "results": {
            "success": success,
            "failed": failed,
            "total_cycles": total_cycles,
        },
        "details": [
            {"account": k, **v} for k, v in results.items()
        ],
        "status": "success" if failed == 0 else ("failed" if success == 0 else "partial"),
    }
    save_history(task)
    print(f"💾 Hasil disimpan ke {HISTORY_FILE}\n")

    return task

# ─────────────────────────────────────────────────────────────
# CLI interaktif
# ─────────────────────────────────────────────────────────────

def interactive_mode():
    print("=" * 58)
    print("  👁️  TikTok Auto Views — Scroll Cycle PARALLEL")
    print("=" * 58)
    print("\n  Semua akun jalan bersamaan di thread terpisah.")
    print("  Alur/siklus: TARGET → scroll bawah → ke-2 → scroll atas → TARGET")

    url = input("\n📎 URL video target: ").strip()
    if not url or "tiktok.com" not in url:
        print("❌ URL tidak valid.")
        return

    acc_keys = list(ACCOUNT_PORT_MAP.keys())
    print(f"\n👥 Pilih akun:")
    print(f"  [0] Semua akun ({len(acc_keys)} akun — semua jalan bersamaan)")
    for i, acc_id in enumerate(acc_keys, 1):
        name = DISPLAY_NAMES.get(acc_id, acc_id)
        print(f"  [{i}] {acc_id} — {name}  (Port {ACCOUNT_PORT_MAP[acc_id]})")

    while True:
        raw = input("\nPilih akun (pisah koma, 0=semua): ").strip()
        if raw == "0":
            selected = acc_keys
            break
        try:
            choices  = [int(x.strip()) for x in raw.split(",")]
            selected = []
            valid    = True
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
            print("   ⚠️  Format tidak valid. Contoh: 1,3,5")

    print(f"✅ Akun: {', '.join(selected)}")

    while True:
        try:
            raw    = input("\n🔁 Siklus per akun? [default: 3]: ").strip()
            cycles = int(raw) if raw else 3
            if cycles >= 1:
                break
            print("   ⚠️  Minimal 1.")
        except ValueError:
            cycles = 3
            break

    print(f"\n{'─'*58}")
    print(f"  URL          : {url}")
    print(f"  Akun         : {', '.join(selected)}")
    print(f"  Siklus/akun  : {cycles}x")
    print(f"  Mode         : 🔀 Parallel (semua jalan bersamaan)")
    print(f"{'─'*58}")

    if input("\n▶️  Lanjutkan? [y/N]: ").strip().lower() != "y":
        print("❌ Dibatalkan.")
        return

    run_all_parallel(url, selected, cycles)


def cli_mode():
    parser = argparse.ArgumentParser(
        description="TikTok Auto Views — Scroll Cycle Parallel via CDP"
    )
    parser.add_argument("--url", required=True)
    parser.add_argument("--accounts", nargs="+", default=list(ACCOUNT_PORT_MAP.keys()))
    parser.add_argument("--cycles", type=int, default=3)
    args = parser.parse_args()
    run_all_parallel(args.url, args.accounts, args.cycles)


# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cli_mode()
    else:
        interactive_mode()
