"""
tiktok_view_mobile.py — 1 akun, 10 siklus
Pola per siklus: nonton utama → swipe ATAS 1× → swipe BAWAH 1× (balik ke utama)
Tanpa buka ulang URL di tengah siklus. Swipe pakai steps=20.
"""

import uiautomator2 as u2
import time
import random
import sys

# ═══════════════════════════════════════════════════════
# KONFIGURASI
# ═══════════════════════════════════════════════════════

VIDEO_URL = "https://www.tiktok.com/@wahyu.deann/video/7709874895101971713"
JUMLAH_SIKLUS = 10
PACKAGE = "com.zhiliaoapp.musically"

# Durasi nonton (detik)
NONTON_UTAMA_AWAL = (15, 30)      # nonton video utama
NONTON_VIDEO_BERIKUT = (8, 15)    # nonton video berikutnya (hasil swipe atas)
NONTON_UTAMA_AKHIR = (5, 12)      # setelah swipe bawah, balik nonton utama

# Jeda antar siklus (detik)
JEDA_ANTAR_SIKLUS = (3, 8)

# Swipe pakai steps=20 (≈100ms) — terbukti tidak pause
SWIPE_STEPS = 20

# ═══════════════════════════════════════════════════════

d = u2.connect()


# ─────────────────────────────────────────────
# UTIL
# ─────────────────────────────────────────────

def ukuran_layar():
    return d.window_size()


def wake_screen():
    try:
        if not d.info.get("screenOn", True):
            d.screen_on()
            time.sleep(0.5)
        d.unlock()
    except Exception:
        pass


def swipe_ke_atas():
    """Swipe ke video BERIKUTNYA — coba swipe_ext dulu, fallback ke swipe manual."""
    try:
        d.swipe_ext("up", scale=0.8)
    except Exception:
        w, h = ukuran_layar()
        x = w // 2
        d.swipe(x, int(h * 0.75), x, int(h * 0.30), steps=SWIPE_STEPS)
    time.sleep(0.3)


def swipe_ke_bawah():
    """Swipe ke video SEBELUMNYA — coba swipe_ext dulu, fallback ke swipe manual."""
    try:
        d.swipe_ext("down", scale=0.8)
    except Exception:
        w, h = ukuran_layar()
        x = w // 2
        d.swipe(x, int(h * 0.30), x, int(h * 0.75), steps=SWIPE_STEPS)
    time.sleep(0.3)


def buka_video(url):
    """Buka URL video SEKALI di awal program, tunggu foreground."""
    d.app_stop(PACKAGE)
    time.sleep(2)
    d.shell(f'am start -a android.intent.action.VIEW -d "{url}" {PACKAGE}')
    time.sleep(random.uniform(4, 6))

    for _ in range(15):
        if d.app_current().get("package") == PACKAGE:
            break
        time.sleep(0.5)

    wake_screen()
    time.sleep(random.uniform(1, 2))


def nonton(durasi):
    """Nonton tanpa klik; swipe mikro 1px sebagai sensor aktivitas."""
    time.sleep(durasi)
    t0 = time.time()
    w, h = ukuran_layar()
    while time.time() - t0 < durasi:
        sisa = durasi - (time.time() - t0)
        chunk = min(random.uniform(4, 9), sisa)
        time.sleep(chunk)

        try:
            x = random.randint(int(w * 0.3), int(w * 0.6))
            y = random.randint(int(h * 0.4), int(h * 0.6))
            d.swipe(x, y, x + 1, y, steps=5)
        except Exception:
            pass


# ─────────────────────────────────────────────
# SATU SIKLUS VIEW
# ─────────────────────────────────────────────

def view_satu_siklus(nomor_siklus):
    print(f"\n=== Siklus #{nomor_siklus} ===")

    # 1) Nonton video utama
    durasi1 = random.uniform(*NONTON_UTAMA_AWAL)
    print(f"  [1/3] Nonton video utama: {durasi1:.0f} detik")
    nonton(durasi1)

    # 2) Swipe ATAS 1× → video berikutnya
    print(f"  [2/3] Swipe ke atas 1× (steps={SWIPE_STEPS})…")
    swipe_ke_atas()
    time.sleep(random.uniform(2, 4))
    durasi2 = random.uniform(*NONTON_VIDEO_BERIKUT)
    print(f"        Nonton video berikutnya: {durasi2:.0f} detik")
    nonton(durasi2)

    # 3) Swipe BAWAH 1× → balik ke video utama
    print(f"  [3/3] Swipe ke bawah 1× (steps={SWIPE_STEPS}) → balik ke utama…")
    swipe_ke_bawah()
    time.sleep(random.uniform(2, 4))
    durasi3 = random.uniform(*NONTON_UTAMA_AKHIR)
    print(f"        Nonton video utama lagi: {durasi3:.0f} detik")
    nonton(durasi3)

    print("  ✓ Siklus selesai")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("TikTok Mobile Auto-View — 1 akun, 10 siklus")
    print("Pola: nonton utama → swipe ATAS → swipe BAWAH (balik)")
    print(f"Target   : {VIDEO_URL}")
    print(f"Siklus   : {JUMLAH_SIKLUS}")
    print(f"Swipe    : steps={SWIPE_STEPS} (≈100ms)")
    print(f"Jeda     : {JEDA_ANTAR_SIKLUS[0]}–{JEDA_ANTAR_SIKLUS[1]}s antar siklus")
    print("=" * 55)

    # Buka URL video SEKALI di awal
    wake_screen()
    print("\n[INIT] Membuka video target…")
    buka_video(VIDEO_URL)
    print("[INIT] Siap.\n")

    sukses = 0
    gagal = 0

    for i in range(1, JUMLAH_SIKLUS + 1):
        try:
            view_satu_siklus(i)
            sukses += 1
        except KeyboardInterrupt:
            print("\n⏹ Dihentikan user.")
            break
        except Exception as e:
            gagal += 1
            print(f"  ✗ Siklus #{i} error: {e}")

        if i < JUMLAH_SIKLUS:
            jeda = random.uniform(*JEDA_ANTAR_SIKLUS)
            print(f"  ⏳ Jeda {jeda:.1f} detik…")
            time.sleep(jeda)

    try:
        d.app_stop(PACKAGE)
    except Exception:
        pass

    print("\n" + "=" * 55)
    print(f"✅ Selesai. Sukses: {sukses} | Gagal: {gagal}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal: {e}", file=sys.stderr)
        sys.exit(1)