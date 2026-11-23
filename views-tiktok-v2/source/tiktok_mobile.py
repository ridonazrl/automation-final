"""
tiktok_view_mobile.py — v2 FIX PAUSE
Perbaikan: tidak ada gesture saat nonton + deteksi & resume pause yang aman.
"""

import uiautomator2 as u2
import time
import random
import sys

# ═══════════════════════════════════════════════════════
# KONFIGURASI
# ═══════════════════════════════════════════════════════

VIDEO_URL = ""
JUMLAH_SIKLUS = 5
PACKAGE = "com.ss.android.ugc.trill"

NONTON_UTAMA_AWAL = (15, 30)
NONTON_VIDEO_BERIKUT = (8, 15)
NONTON_UTAMA_AKHIR = (5, 12)
JEDA_ANTAR_SIKLUS = (3, 8)

SWIPE_STEPS_BAWAH = 12
SWIPE_STEPS_ATAS = 20

# Kandidat resource-id tombol play overlay saat pause.
# TIAP VERSI TIKTOK BEDA — cari punyamu (lihat cara di bawah script).
PAUSE_OVERLAY_IDS = [
    f"{PACKAGE}:id/iv_play",
    f"{PACKAGE}:id/play_icon",
    f"{PACKAGE}:id/pause_icon",
    f"{PACKAGE}:id/lc",
]

d = u2.connect()


# ─────────────────────────────────────────────
# UTIL
# ─────────────────────────────────────────────

def ukuran_layar():
    info = d.info
    return info["displayWidth"], info["displayHeight"]


def wake_screen():
    if not d.info.get("screenOn", True):
        d.screen_on()
        time.sleep(1)


def swipe_ke_atas():
    w, h = ukuran_layar()
    d.swipe(w * 0.5, h * 0.75, w * 0.5, h * 0.25, duration=0.3)


def swipe_ke_bawah():
    w, h = ukuran_layar()
    d.swipe(w * 0.5, h * 0.25, w * 0.5, h * 0.75, duration=0.3)


def buka_video(url):
    d.shell(f'am start -a android.intent.action.VIEW -d "{url}" {PACKAGE}')
    time.sleep(5)


def nonton(durasi):
    wake_screen()
    time.sleep(durasi)


def sedang_pause() -> bool:
    for rid in PAUSE_OVERLAY_IDS:
        if d(resourceId=rid).exists:
            return True
    return False


def resume_kalau_pause():
    if sedang_pause():
        print("  ⏸ Terdeteksi pause, mencoba resume…")
        for rid in PAUSE_OVERLAY_IDS:
            el = d(resourceId=rid)
            if el.exists:
                try:
                    el.click()
                    time.sleep(1)
                    print("  ▶ Resume berhasil")
                    return
                except Exception:
                    pass
        # fallback: tap tengah layar
        w, h = ukuran_layar()
        d.click(w * 0.5, h * 0.5)
        time.sleep(1)


# ─────────────────────────────────────────────
# SIKLUS
# ─────────────────────────────────────────────

def view_satu_siklus(nomor):
    print(f"\n=== Siklus #{nomor} ===")

    durasi1 = random.uniform(*NONTON_UTAMA_AWAL)
    print(f"  [1/3] Nonton utama: {durasi1:.0f} detik")
    nonton(durasi1)
    resume_kalau_pause()

    print(f"  [2/3] Swipe atas 1×…")
    swipe_ke_atas()
    time.sleep(random.uniform(2, 4))
    resume_kalau_pause()
    durasi2 = random.uniform(*NONTON_VIDEO_BERIKUT)
    print(f"        Nonton video berikutnya: {durasi2:.0f} detik")
    nonton(durasi2)
    resume_kalau_pause()

    print(f"  [3/3] Swipe bawah 1× → balik ke utama…")
    swipe_ke_bawah()
    time.sleep(random.uniform(2, 4))
    resume_kalau_pause()
    durasi3 = random.uniform(*NONTON_UTAMA_AKHIR)
    print(f"        Nonton utama lagi: {durasi3:.0f} detik")
    nonton(durasi3)
    resume_kalau_pause()

    print("  ✓ Siklus selesai")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    global VIDEO_URL, JUMLAH_SIKLUS

    # --- CLI Arguments ---
    if len(sys.argv) > 1:
        VIDEO_URL = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            JUMLAH_SIKLUS = int(sys.argv[2])
        except ValueError:
            print("[!] Jumlah siklus harus berupa angka. Menggunakan nilai default.")

    print("=" * 55)
    print("  Android UI Testing Script - TikTok (Asia)")
    print("=" * 55)
    print(f"Target     : {VIDEO_URL}")
    print(f"Siklus     : {JUMLAH_SIKLUS}")
    print(f"Package    : {PACKAGE}")
    print("=" * 55)

    sukses = 0
    gagal = 0

    try:
        print(f"[INIT] Device terhubung: {d.serial}")

        # 1. Buka aplikasi
        print(f"[*] Membuka aplikasi ({PACKAGE})...")
        d.app_start(PACKAGE)
        print("[*] Menunggu 10 detik agar aplikasi fully loaded...")
        time.sleep(10)

        # 2. Buka target video via am start
        print(f"[*] Membuka target: {VIDEO_URL}")
        d.shell(f'am start -a android.intent.action.VIEW -d "{VIDEO_URL}"')
        print("[*] Menunggu 5 detik agar konten load...")
        time.sleep(5)

        # 3. Loop siklus
        for i in range(1, JUMLAH_SIKLUS + 1):
            try:
                print(f"\n>>> Memulai siklus {i}/{JUMLAH_SIKLUS}")
                view_satu_siklus(i)
                sukses += 1

                if i < JUMLAH_SIKLUS:
                    jeda = random.uniform(*JEDA_ANTAR_SIKLUS)
                    print(f"[*] Jeda antar siklus: {jeda:.1f} detik...")
                    time.sleep(jeda)

            except Exception as e:
                gagal += 1
                print(f"[!] Error di siklus {i}: {e}")
                continue

    except KeyboardInterrupt:
        print("\n[!] Dihentikan oleh user (KeyboardInterrupt)")
    except Exception as e:
        print(f"[!] Error fatal: {e}")
    finally:
        try:
            print("[*] Menutup aplikasi...")
            d.app_stop(PACKAGE)
        except Exception:
            pass

        # Ringkasan
        print("\n" + "=" * 55)
        print("  RINGKASAN")
        print("=" * 55)
        print(f"Siklus sukses : {sukses}")
        print(f"Siklus gagal  : {gagal}")
        print(f"Total target  : {JUMLAH_SIKLUS}")
        print("=" * 55)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal: {e}", file=sys.stderr)
        sys.exit(1)
