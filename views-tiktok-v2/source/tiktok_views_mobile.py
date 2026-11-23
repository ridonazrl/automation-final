"""
tiktok_views_mobile.py
──────────────────────
Auto views TikTok via perangkat Android nyata menggunakan uiautomator2.

Pola nonton per sesi:
  1. Buka video target → tonton beberapa detik
  2. Swipe ke video berikutnya → singgah sebentar
  3. Swipe balik ke video target → tonton lagi sebentar

Cara pakai:
  python tiktok_views_mobile.py                              # mode interaktif
  python tiktok_views_mobile.py --url "https://..." --accounts akun1 akun2
  python tiktok_views_mobile.py --url "https://..." --repeat 3
"""

import os
import json
import time
import random
import argparse
from datetime import datetime

import uiautomator2 as u2

# ─────────────────────────────────────────────────────────────
# Konfigurasi
# ─────────────────────────────────────────────────────────────

PACKAGE = "com.zhiliaoapp.musically"

# Durasi nonton (detik) — setiap tahap
NONTON_UTAMA_AWAL   = (15, 30)   # nonton video utama sebelum pindah
NONTON_VIDEO_KEDUA  = (8, 15)    # singgah di video ke-2
NONTON_UTAMA_AKHIR  = (5, 12)    # balik ke utama, tonton lagi sebentar

# Jeda antar sesi (detik)
DELAY_MIN = 30
DELAY_MAX = 90

# Daftar akun — tambahkan sesuai nama akun di HP
ACCOUNTS = ["akun1", "akun2", "akun3"]

# File histori
HISTORY_FILE = "views_history_mobile.json"

# ─────────────────────────────────────────────────────────────
# Koneksi perangkat
# ─────────────────────────────────────────────────────────────

# Ganti IP di bawah dengan IP HP kamu (cek di Settings → About → IP address)
# Pastikan atx-agent sudah jalan di HP: jalankan sekali lewat `python -m uiautomator2 init`
d = u2.connect()   # koneksi USB


# ─────────────────────────────────────────────────────────────
# Utilitas layar
# ─────────────────────────────────────────────────────────────

def ukuran_layar():
    return d.window_size()   # (lebar, tinggi)


def swipe_ke_atas():
    """Scroll ke video berikutnya."""
    w, h = ukuran_layar()
    d.swipe(w // 2, int(h * 0.75), w // 2, int(h * 0.25),
            duration=random.uniform(0.2, 0.35))


def swipe_ke_bawah():
    """Kembali ke video sebelumnya."""
    w, h = ukuran_layar()
    d.swipe(w // 2, int(h * 0.25), w // 2, int(h * 0.75),
            duration=random.uniform(0.2, 0.35))


# ─────────────────────────────────────────────────────────────
# Aksi utama
# ─────────────────────────────────────────────────────────────

def buka_video(url: str):
    """Tutup TikTok, lalu buka URL video via intent."""
    d.app_stop(PACKAGE)
    time.sleep(2)
    d.shell(f'am start -a android.intent.action.VIEW -d "{url}" {PACKAGE}')
    time.sleep(random.uniform(5, 8))
    d.screen_on()
    d.wake_up()


def nonton(durasi: float):
    """
    Simulasi menonton: sesekali tap di area video (bukan tombol kanan).
    Tap area: 30–60% lebar, 40–60% tinggi — hindari tombol like/komentar.
    """
    t0 = time.time()
    while time.time() - t0 < durasi:
        w, h = ukuran_layar()
        d.click(
            random.randint(int(w * 0.3), int(w * 0.6)),
            random.randint(int(h * 0.4), int(h * 0.6)),
        )
        time.sleep(random.uniform(4, 8))


def ganti_akun(indeks_tujuan: int):
    """
    Pindah akun via Profile → Switch account.
    Koordinat y pada daftar akun perlu disesuaikan ke HP masing-masing.
    """
    d.app_start(PACKAGE)
    time.sleep(random.uniform(4, 6))

    if not d(text="Profile").click_exists(timeout=5000):
        print("    [!] Tombol Profile tidak ditemukan")
        return

    time.sleep(random.uniform(2, 4))

    # Coba beberapa label "Switch account"
    if not (
        d(description="Switch account").click_exists(timeout=3000)
        or d(text="Switch account").click_exists(timeout=3000)
    ):
        d.click(300, 200)   # fallback: tap header nama user

    time.sleep(random.uniform(2, 4))

    # Sesuaikan y_base dan jarak_per_akun dengan tampilan HP-mu
    y_base = 800
    jarak_per_akun = 160
    d.click(500, y_base + indeks_tujuan * jarak_per_akun)
    time.sleep(random.uniform(4, 7))


# ─────────────────────────────────────────────────────────────
# Satu sesi view (buka → singgah → balik)
# ─────────────────────────────────────────────────────────────

def view_satu_sesi(url: str, label: str = ""):
    """
    Jalankan satu siklus view: buka video, pindah ke video ke-2, balik.

    Returns:
        dict: success, watched_seconds (total), error (opsional)
    """
    prefix = f"  {label}" if label else "  "

    try:
        buka_video(url)

        # 1) Nonton video utama
        dur1 = random.uniform(*NONTON_UTAMA_AWAL)
        print(f"{prefix}[1/3] Nonton video utama   : {dur1:.0f} dtk")
        nonton(dur1)

        # 2) Pindah ke video ke-2
        swipe_ke_atas()
        time.sleep(random.uniform(2, 4))
        dur2 = random.uniform(*NONTON_VIDEO_KEDUA)
        print(f"{prefix}[2/3] Singgah video ke-2   : {dur2:.0f} dtk")
        nonton(dur2)

        # 3) Balik ke video utama
        swipe_ke_bawah()
        time.sleep(random.uniform(2, 4))
        dur3 = random.uniform(*NONTON_UTAMA_AKHIR)
        print(f"{prefix}[3/3] Kembali video utama  : {dur3:.0f} dtk")
        nonton(dur3)

        total_dtk = int(dur1 + dur2 + dur3)
        print(f"{prefix}✓ Sesi selesai ({total_dtk} dtk total)")

        return {"success": True, "watched_seconds": total_dtk}

    except Exception as e:
        print(f"{prefix}✗ Error: {e}")
        return {"success": False, "watched_seconds": 0, "error": str(e)}


# ─────────────────────────────────────────────────────────────
# Orkestrasi multi-akun
# ─────────────────────────────────────────────────────────────

def run_views(url: str, accounts: list, repeat: int = 1):
    """
    Jalankan views untuk banyak akun, opsional beberapa kali.

    Args:
        url      : URL video TikTok
        accounts : List indeks/nama akun (berdasar posisi di ACCOUNTS)
        repeat   : Berapa kali tiap akun menonton
    """
    print(f"\n{'='*55}")
    print(f"  📱  TikTok Auto Views — Mobile (uiautomator2)")
    print(f"{'='*55}")
    print(f"  URL    : {url}")
    print(f"  Akun   : {', '.join(str(a) for a in accounts)}")
    print(f"  Repeat : {repeat}x per akun")
    total = len(accounts) * repeat
    print(f"  Total  : {total} sesi")
    print(f"{'='*55}\n")

    task = {
        "id": f"mobile_views_{int(time.time())}",
        "url": url,
        "accounts": accounts,
        "repeat": repeat,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": {"success": 0, "failed": 0},
        "details": [],
    }

    counter = 0

    for acc_idx, acc_name in enumerate(accounts):
        for r in range(repeat):
            counter += 1
            label = f"[{counter}/{total}]"

            if acc_idx > 0 or r > 0:
                # Ganti akun hanya saat berpindah ke akun berbeda
                if r == 0:
                    print(f"\n{label} Ganti ke akun: {acc_name}")
                    ganti_akun(acc_idx)
                else:
                    print(f"\n{label} Akun: {acc_name} — sesi ke-{r+1}")
            else:
                print(f"\n{label} Akun: {acc_name}")

            result = view_satu_sesi(url, label)
            result["account"] = acc_name
            result["url"] = url
            task["details"].append(result)

            if result["success"]:
                task["results"]["success"] += 1
            else:
                task["results"]["failed"] += 1
                print(f"   ⚠️  Gagal: {result.get('error', 'Unknown')}")

            # Jeda sebelum sesi berikutnya
            if counter < total:
                delay = random.randint(DELAY_MIN, DELAY_MAX)
                print(f"\n⏳ Jeda {delay} dtk sebelum sesi berikutnya...")
                time.sleep(delay)

    # Tutup aplikasi
    d.app_stop(PACKAGE)

    # Ringkasan
    s = task["results"]["success"]
    f = task["results"]["failed"]
    task["status"] = (
        "success" if f == 0 else ("failed" if s == 0 else "partial")
    )

    print(f"\n{'='*55}")
    print(f"🏁 SELESAI")
    print(f"   ✅ Berhasil : {s} sesi")
    print(f"   ❌ Gagal    : {f} sesi")
    print(f"{'='*55}")

    _save_history(task)
    print(f"💾 Histori disimpan ke {HISTORY_FILE}")

    return task


# ─────────────────────────────────────────────────────────────
# Histori
# ─────────────────────────────────────────────────────────────

def _save_history(task: dict):
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
# Mode interaktif
# ─────────────────────────────────────────────────────────────

def interactive_mode():
    print("=" * 55)
    print("  📱  TikTok Auto Views — Mobile")
    print("=" * 55)

    # URL
    url = input("\n📎 URL video TikTok: ").strip()
    if not url or "tiktok.com" not in url:
        print("❌ URL tidak valid.")
        return

    # Pilih akun
    print(f"\n👥 Akun terdaftar ({len(ACCOUNTS)}):")
    print(f"  [0] Semua akun")
    for i, name in enumerate(ACCOUNTS, 1):
        print(f"  [{i}] {name}")

    while True:
        raw = input("\nPilih akun (pisah koma, 0=semua): ").strip()
        if raw == "0":
            selected_names = ACCOUNTS[:]
            break
        try:
            choices = [int(x.strip()) for x in raw.split(",")]
            selected_names = []
            ok = True
            for c in choices:
                if 1 <= c <= len(ACCOUNTS):
                    selected_names.append(ACCOUNTS[c - 1])
                else:
                    print(f"   ⚠️  Nomor {c} tidak valid.")
                    ok = False
                    break
            if ok and selected_names:
                break
        except ValueError:
            print("   ⚠️  Format tidak valid. Contoh: 1,2")

    print(f"✅ Akun dipilih: {', '.join(selected_names)}")

    # Repeat
    while True:
        try:
            raw = input("\n🔁 Berapa kali tiap akun menonton? [default: 1]: ").strip()
            repeat = int(raw) if raw else 1
            if repeat >= 1:
                break
            print("   ⚠️  Minimal 1.")
        except ValueError:
            repeat = 1
            break

    # Konfirmasi
    total = len(selected_names) * repeat
    print(f"\n📋 Ringkasan:")
    print(f"   URL   : {url}")
    print(f"   Akun  : {', '.join(selected_names)}")
    print(f"   Total : {total} sesi")
    confirm = input("\n▶️  Lanjutkan? [y/N]: ").strip().lower()
    if confirm != "y":
        print("❌ Dibatalkan.")
        return

    run_views(url, selected_names, repeat)


# ─────────────────────────────────────────────────────────────
# Mode CLI
# ─────────────────────────────────────────────────────────────

def cli_mode():
    parser = argparse.ArgumentParser(
        description="TikTok Auto Views — Mobile (uiautomator2)"
    )
    parser.add_argument("--url", required=True, help="URL video TikTok")
    parser.add_argument(
        "--accounts",
        nargs="+",
        default=ACCOUNTS,
        help="Nama akun (sesuai list ACCOUNTS), misal: akun1 akun2",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Berapa kali tiap akun menonton (default: 1)",
    )
    args = parser.parse_args()
    run_views(args.url, args.accounts, args.repeat)


# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cli_mode()
    else:
        interactive_mode()
