#!/bin/bash

echo "=========================================="
echo "    TIKTOK AUTO-VIEW (MOBILE USB)"
echo "=========================================="
echo ""

# 1. Cek HP kedetek gak
echo "[*] Cek koneksi HP via ADB..."
adb devices | grep -q "device" 
if [ $? -ne 0 ]; then
    echo "❌ HP tidak terdeteksi! Pastiin HP udah dicolok & USB Debugging ON."
    exit 1
fi
echo "✅ HP terdeteksi."
echo ""

# 2. Tanya URL
while true; do
    read -p "Paste URL Video TikTok: " TARGET_URL
    [ -n "$TARGET_URL" ] && break
done

# 3. Tanya Siklus
read -p "Berapa siklus? (default 5): " SIKLUS
[ -z "$SIKLUS" ] && SIKLUS=5

echo ""
echo "=== START AUTO-VIEW ==="
echo "Target : $TARGET_URL"
echo "Siklus : $SIKLUS"
echo ""

# 4. Jalanin script Python
cd /opt/project/spammer/views-tiktok-v2/source
python3 tiktok_mobile.py "$TARGET_URL" "$SIKLUS"
