#!/bin/bash

echo "=========================================="
echo "    TIKTOK AUTO-LIKE - MULTI CDP"
echo "=========================================="
echo ""

# 1. Tanya URL
while true; do
    read -p "Tempel URL video TikTok: " TARGET_URL
    if [ -z "$TARGET_URL" ]; then
        echo "❌ URL gak boleh kosong."
        continue
    fi
    if [[ ! "$TARGET_URL" =~ tiktok\.com ]]; then
        echo "❌ URL harus dari tiktok.com."
        continue
    fi
    break
done

# 2. Tanya Akun
echo ""
echo "Pilih Akun (1-5):"
echo "1. akun1 (Fatur Ikhsanudin)"
echo "2. akun2 (Ridetes7)"
echo "3. akun3 (Ridonajrul)"
echo "4. akun4 (Usertestpkl)"
echo "5. akun5 (Gptridho)"
echo "6. SEMUA AKUN (Loop 1-5)"
echo ""

while true; do
    read -p "Pilih (1-6): " CHOICE
    case "$CHOICE" in
        1) AKUN="akun1"; break ;;
        2) AKUN="akun2"; break ;;
        3) AKUN="akun3"; break ;;
        4) AKUN="akun4"; break ;;
        5) AKUN="akun5"; break ;;
        6) AKUN="ALL"; break ;;
        *) echo "❌ Pilihan gak valid." ;;
    esac
done

echo ""
echo "=== START TIKTOK AUTO-LIKE ==="
echo "Target: $TARGET_URL"
echo ""

# 3. Eksekusi
if [ "$AKUN" == "ALL" ]; then
    for akun in akun1 akun2 akun3 akun4 akun5; do
        python3 /tmp/tiktok-qa/tiktok_cdp_multi.py "$TARGET_URL" "$akun"
        echo ""
        echo "⏳ Jeda 5 detik sebelum akun berikutnya..."
        sleep 5
    done
else
    python3 /tmp/tiktok-qa/tiktok_cdp_multi.py "$TARGET_URL" "$AKUN"
fi

echo ""
echo "=== SELESAI ==="
