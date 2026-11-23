"""
Facebook Auto-Like Bot v22 - FINAL (Multi-Strategi + Dump DOM + Frame Check)
"""
from playwright.sync_api import sync_playwright
import time
import random
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

ACCOUNT_PORT_MAP = {
    "akun1": 9222, "akun2": 9223, "akun3": 9224, "akun4": 9225, "akun5": 9226,
}
DEFAULT_CDP_PORT = 9222
WINDOWS_HOST = "10.10.100.254"

CONFIG = {
    "target_url": "",
    "max_likes": 1,
    "delay_between_accounts": (10, 20),
    "accounts_dir": "./accounts",
}


class AccountManager:
    def __init__(self, accounts_dir: str = "./accounts"):
        self.accounts_dir = Path(accounts_dir)
        self.accounts_dir.mkdir(parents=True, exist_ok=True)
        self.accounts_file = self.accounts_dir / "accounts.json"
        self.load_accounts()

    def load_accounts(self):
        if self.accounts_file.exists():
            try:
                with open(self.accounts_file, "r") as f:
                    self.accounts = json.load(f)
            except Exception:
                self.accounts = []
        else:
            self.accounts = []

    def get_all_accounts(self):
        return self.accounts


class FacebookAutoLike:
    def __init__(self, config: Dict):
        self.config = config
        self.account_manager = AccountManager(config.get("accounts_dir", "./accounts"))
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.current_account = None

    def log(self, msg: str, level: str = "INFO"):
        t = datetime.now().strftime("%H:%M:%S")
        icons = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "DEBUG": "🐞"}
        account_name = f"[{self.current_account.get('name', 'unknown')}] " if self.current_account else ""
        print(f"[{t}] {account_name}{icons.get(level, 'ℹ️')} {msg}", flush=True)

    def wait(self, a: float, b: Optional[float] = None):
        time.sleep(a if b is None else random.uniform(a, b))

    def setup_browser(self, account: Dict):
        account_name = account.get("name")
        port = ACCOUNT_PORT_MAP.get(account_name, DEFAULT_CDP_PORT)
        cdp_url = f"http://{WINDOWS_HOST}:{port}"
        self.log(f"🔌 Connect ke Chrome CDP: {cdp_url}", "INFO")
        try:
            self.browser = self.playwright.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            raise Exception(f"Gagal connect ke Chrome CDP {cdp_url}: {e}")
        if self.browser.contexts:
            self.context = self.browser.contexts[0]
        else:
            self.context = self.browser.new_context()
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = self.context.new_page()
        self.log(f"✅ Connected ke Chrome CDP port {port}", "OK")

    def check_login(self) -> bool:
        self.log("Memeriksa login...", "INFO")
        try:
            self.page.goto("https://www.facebook.com/", timeout=30000)
            self.wait(3, 5)
            current_url = self.page.url
            self.log(f"URL: {current_url}", "INFO")
            if "facebook.com/login" in current_url or "/recover" in current_url:
                self.log("❌ Chrome CDP tidak login", "ERR")
                return False
            try:
                if self.page.locator("#email").is_visible(timeout=2000):
                    self.log("❌ Form login muncul", "ERR")
                    return False
            except Exception:
                pass
            self.log("✅ Chrome CDP login OK", "OK")
            return True
        except Exception as e:
            self.log(f"Error check login: {e}", "ERR")
            return False

    def dump_full_dom(self, prefix: str = "dom") -> Optional[str]:
        """Dump seluruh page + semua iframe ke /tmp/"""
        ts = int(time.time())
        out_dir = Path("/tmp")
        out_dir.mkdir(parents=True, exist_ok=True)
        main_path = out_dir / f"{prefix}_{ts}.html"

        try:
            html = self.page.content()
            main_path.write_text(html, encoding="utf-8")
            self.log(f"Dump page → {main_path} ({len(html)} bytes)", "INFO")
            print(f"DUMP OK: {main_path}", flush=True)
        except Exception as e:
            self.log(f"Gagal page.content(): {e}", "ERR")
            print(f"DUMP FAIL: {e}", flush=True)
            return None

        # Dump semua iframe
        for i, frame in enumerate(self.page.frames):
            if frame == self.page.main_frame:
                continue
            try:
                f_html = frame.content()
                p = out_dir / f"{prefix}_{ts}_frame_{i}.html"
                p.write_text(f_html, encoding="utf-8")
                self.log(f"Dump frame[{i}] url={frame.url[:60]}", "INFO")
            except Exception:
                pass

        return str(main_path)

    def search_all_frames(self):
        """Cek semua frame, cari role=button & like"""
        print(f"=== TOTAL FRAMES: {len(self.page.frames)} ===", flush=True)
        for i, frame in enumerate(self.page.frames):
            try:
                count = frame.locator("[role='button']").count()
                likes = frame.get_by_role("button", name=re.compile(r"like|suka", re.I)).count()
                print(f"Frame[{i}] url={frame.url[:60]} → role=button={count}, like={likes}", flush=True)
            except Exception as e:
                print(f"Frame[{i}] error: {e}", flush=True)

    def find_like_via_js(self) -> Optional[dict]:
        """Cari elemen Like pakai JavaScript injection (tembus Shadow DOM)"""
        try:
            result = self.page.evaluate(r"""() => {
                const keywords = /like|suka|sukai|unlike|batalkan\s*suka/i;

                function isVisible(el) {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0')
                        return false;
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                }

                function score(el) {
                    let s = 0;
                    const label = (el.getAttribute('aria-label') || '').toLowerCase();
                    const text  = (el.innerText || el.textContent || '').toLowerCase().trim();
                    const testid = (el.getAttribute('data-testid') || '').toLowerCase();
                    const role = (el.getAttribute('role') || '').toLowerCase();

                    if (keywords.test(label)) s += 10;
                    if (keywords.test(text) && text.length < 30) s += 8;
                    if (keywords.test(testid)) s += 6;
                    if (role === 'button') s += 3;
                    if (el.querySelector('svg')) s += 2;
                    return s;
                }

                const all = Array.from(document.querySelectorAll(
                    '[role="button"], button, [tabindex="0"], div[class*="like" i], span[class*="like" i]'
                ));

                const candidates = [];
                for (const el of all) {
                    if (!isVisible(el)) continue;
                    const sc = score(el);
                    if (sc < 5) continue;

                    const rect = el.getBoundingClientRect();
                    candidates.push({
                        score: sc,
                        tag: el.tagName,
                        role: el.getAttribute('role'),
                        aria: el.getAttribute('aria-label'),
                        testid: el.getAttribute('data-testid'),
                        text: (el.innerText || '').trim().slice(0, 60),
                        x: Math.round(rect.x + rect.width / 2),
                        y: Math.round(rect.y + rect.height / 2),
                        w: Math.round(rect.width),
                        h: Math.round(rect.height),
                        outer: el.outerHTML.slice(0, 300)
                    });
                }

                candidates.sort((a, b) => b.score - a.score);
                return candidates.slice(0, 10);
            }""")
        except Exception as e:
            self.log(f"JS eval error: {e}", "WARN")
            return None

        if not result:
            self.log("JS search: 0 kandidat", "WARN")
            return None

        for i, c in enumerate(result):
            self.log(
                f"JS candidate[{i}] score={c['score']} aria={c['aria']!r} "
                f"text={c['text']!r} pos=({c['x']},{c['y']})",
                "DEBUG"
            )
            print(f"JS candidate[{i}]: score={c['score']}, aria={c['aria']}, text={c['text']}, pos=({c['x']},{c['y']})", flush=True)

        return result[0] if result else None

    def click_by_point(self, x: int, y: int) -> bool:
        try:
            self.page.mouse.click(x, y)
            self.log(f"Clicked at ({x}, {y})", "INFO")
            return True
        except Exception as e:
            self.log(f"mouse.click gagal: {e}", "ERR")
            return False

    def find_like_button_simple(self):
        """Cari tombol Like: multi-strategi + JS fallback"""
        # --- ALARM: mastiin kode baru ke-load ---
        print("=== KODE BARU TER-LOAD ===", flush=True)
        self.log("=== KODE BARU TER-LOAD ===", "INFO")

        try:
            with open("/tmp/qa_alive.txt", "w") as f:
                f.write("alive\n")
            print("File /tmp/qa_alive.txt berhasil ditulis", flush=True)
        except Exception as e:
            print(f"GAGAL tulis /tmp: {e}", flush=True)

        # === STRATEGI 1: Playwright locator di semua dialog ===
        try:
            dialogs = self.page.locator("[role='dialog']").all()
            self.log(f"Total dialog: {len(dialogs)}", "INFO")

            for di, dialog in enumerate(dialogs):
                try:
                    if not dialog.is_visible():
                        continue

                    text = dialog.inner_text(timeout=2000) or ""
                    self.log(f"Dialog {di}: visible, text={text[:100].replace(chr(10), ' ')}", "INFO")

                    candidates = []

                    # get_by_role + regex
                    try:
                        loc = dialog.get_by_role("button", name=re.compile(r"^(Like|Suka|Sukai)$", re.I))
                        candidates.extend(loc.all())
                    except Exception:
                        pass

                    # aria-label contains
                    try:
                        loc = dialog.locator("[aria-label*='Like' i], [aria-label*='Suka' i]")
                        candidates.extend(loc.all())
                    except Exception:
                        pass

                    # data-testid
                    try:
                        loc = dialog.locator("[data-testid*='like' i], [data-testid*='UFI2Reaction' i]")
                        candidates.extend(loc.all())
                    except Exception:
                        pass

                    # Filter & sort by Y
                    visible_candidates = []
                    for el in candidates:
                        try:
                            if not el.is_visible():
                                continue
                            aria = (el.get_attribute("aria-label") or "").lower()
                            if any(x in aria for x in ["unlike", "tidak suka", "batalkan", "hapus suka"]):
                                continue
                            box = el.bounding_box()
                            if not box:
                                continue
                            visible_candidates.append((el, box['y'], box['x'], aria))
                        except Exception:
                            continue

                    visible_candidates.sort(key=lambda x: x[1])
                    self.log(f"Dialog {di}: kandidat={len(visible_candidates)} (sorted by Y)", "INFO")

                    if visible_candidates:
                        el, y, x, aria = visible_candidates[0]
                        self.log(f"✅ TARGET Like: dialog={di}, pos=({int(x)},{int(y)}), aria='{aria}'", "OK")
                        return el

                except Exception as e:
                    self.log(f"Skip dialog {di}: {e}", "WARN")

        except Exception as e:
            self.log(f"Error find_like (Playwright): {e}", "WARN")

        # === STRATEGI 2: JS Injection (tembus Shadow DOM) ===
        self.log("Playwright locator gagal, coba JS injection...", "WARN")
        best = self.find_like_via_js()
        if best and best.get("score", 0) >= 8:
            self.log(f"✅ JS nemu kandidat: score={best['score']}, pos=({best['x']},{best['y']})", "OK")
            return ("JS_POINT", best["x"], best["y"])

        # === STRATEGI 3: Cek semua frame ===
        self.log("JS gagal, cek semua frame...", "WARN")
        for i, frame in enumerate(self.page.frames):
            try:
                btn = frame.get_by_role("button", name=re.compile(r"like|suka", re.I)).first
                if btn.count() > 0 and btn.is_visible():
                    self.log(f"✅ Nem u Like di frame[{i}]", "OK")
                    return btn
            except Exception:
                continue

        return None

    def like_target_post(self) -> bool:
        target_url = self.config["target_url"]

        if not target_url:
            self.log("Target URL belum diisi!", "ERR")
            return False

        self.log(f"Membuka target: {target_url}", "INFO")

        try:
            self.page.goto(target_url, timeout=60000)
            self.wait(5, 8)
        except Exception:
            self.log("Timeout membuka target", "ERR")
            return False

        current_url = self.page.url
        self.log(f"URL target: {current_url}", "INFO")

        if "login" in current_url:
            self.log("Redirect ke login", "WARN")
            return False

        self.wait(3, 5)

        # === DEBUG: Dump DOM & cek frame ===
        self.log("=== DEBUG: Dump DOM & cek frame ===", "DEBUG")
        self.dump_full_dom("before_like")
        self.search_all_frames()

        self.log("Mencari tombol Like TARGET...", "INFO")

        like_button = self.find_like_button_simple()

        # Kalau hasilnya tuple (JS_POINT), klik by koordinat
        if isinstance(like_button, tuple) and like_button[0] == "JS_POINT":
            _, x, y = like_button
            self.log(f"🎯 Klik via koordinat JS: ({x},{y})", "INFO")
            if self.click_by_point(x, y):
                self.wait(2, 3)
                self.log("✅ Like via JS point berhasil (asumsi)", "OK")
                return True
            return False

        if not like_button:
            self.log("Belum ketemu, scroll modal...", "INFO")
            try:
                self.page.mouse.wheel(0, 500)
            except Exception:
                self.page.evaluate("window.scrollBy(0, 500)")
            self.wait(2, 3)
            like_button = self.find_like_button_simple()

        if not like_button:
            self.log("❌ Tombol Like TARGET tidak ketemu", "ERR")
            try:
                self.page.screenshot(path="/tmp/debug_no_target_like.png")
            except Exception:
                pass
            return False

        # Klik pakai Playwright
        try:
            if isinstance(like_button, tuple):
                return False

            like_button.scroll_into_view_if_needed()
            self.wait(1, 2)

            box = like_button.bounding_box()
            if box:
                self.log(f"🎯 Klik TARGET Like di ({int(box['x'])},{int(box['y'])})", "INFO")

            like_button.click(timeout=10000)
            self.wait(2, 3)

            aria_after = (like_button.get_attribute("aria-label") or "").lower()
            if any(x in aria_after for x in ["unlike", "tidak suka", "berhenti", "batalkan", "hapus suka"]):
                self.log("✅ Like TARGET berhasil dan terverifikasi!", "OK")
                return True

            self.log(f"State setelah klik: aria='{aria_after}'", "INFO")
            self.log("⚠️ Klik dilakukan, state belum terverifikasi dari aria-label", "WARN")
            return True

        except Exception as e:
            self.log(f"❌ Gagal klik Like TARGET: {e}", "ERR")
            return False

    def run_account(self, account: Dict) -> bool:
        self.current_account = account
        try:
            self.log("=" * 50, "INFO")
            self.log(f"Memproses: {account.get('name', 'unknown')}", "INFO")
            self.log(f"{'='*50}", "INFO")
            self.setup_browser(account)
            if not self.check_login():
                self.log("Login gagal", "ERR")
                return False
            return self.like_target_post()
        except Exception as e:
            self.log(f"Error: {e}", "ERR")
            return False
        finally:
            self.log("Selesai akun ini", "INFO")

    def run(self):
        if not self.config["target_url"]:
            self.log("Target URL belum diisi!", "ERR")
            return
        accounts = self.account_manager.get_all_accounts()
        if not accounts:
            self.log("Tidak ada akun!", "ERR")
            return
        self.log(f"Ditemukan {len(accounts)} akun", "INFO")
        try:
            self.playwright = sync_playwright().start()
            results = []
            for i, account in enumerate(accounts, 1):
                self.log(f"\n{'='*50}", "INFO")
                self.log(f"Akun {i}/{len(accounts)}", "INFO")
                self.log(f"{'='*50}", "INFO")
                success = self.run_account(account)
                results.append({
                    "account": account.get("name"),
                    "email": account.get("email", "unknown"),
                    "success": success,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                if i < len(accounts):
                    delay = random.uniform(*self.config["delay_between_accounts"])
                    self.log(f"Jeda {delay:.0f} detik...", "INFO")
                    time.sleep(delay)
            self.log(f"\n{'='*50}", "INFO")
            self.log("RINGKASAN HASIL:", "INFO")
            self.log(f"{'='*50}", "INFO")
            success_count = 0
            for result in results:
                status = "OK" if result["success"] else "FAIL"
                if result["success"]:
                    success_count += 1
                self.log(f"{status} {result['account']} ({result['email']})", "INFO")
            self.log(f"\nTotal berhasil: {success_count}/{len(results)}", "INFO")
            with open("results.json", "w") as f:
                json.dump(results, f, indent=2)
            self.log("Hasil disimpan ke results.json", "OK")
        except Exception as e:
            self.log(f"Fatal error: {e}", "ERR")
        finally:
            if self.playwright:
                self.playwright.stop()
            self.log("Bot selesai!", "OK")


if __name__ == "__main__":
    import sys
    config = CONFIG.copy()
    if len(sys.argv) > 1:
        config["target_url"] = sys.argv[1]
    bot = FacebookAutoLike(config)
    bot.run()
