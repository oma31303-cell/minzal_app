#!/data/data/com.termux/files/usr/bin/bash
echo "تثبيت المتطلبات..."
pkg install -y python-flask ffmpeg python-numpy 2>/dev/null
pip install -U flask yt-dlp gallery-dl qrcode pillow pypdf python-barcode openpyxl pyotp fpdf2 pytesseract pyzbar --break-system-packages 2>/dev/null
echo "تشغيل السيرفر..."
cd "$(dirname "$0")"
python server.py
