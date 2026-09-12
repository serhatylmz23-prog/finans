#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "============================================"
echo "  SyFinansOtagi baslatiliyor..."
echo "============================================"
echo

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "[HATA] Python bulunamadi. https://www.python.org/downloads/ adresinden kurun"
    echo "(Mac icin: brew install python3 de kullanilabilir)."
    read -p "Kapatmak icin Enter'a basin..."
    exit 1
fi

if [ ! -f ".kurulum_tamam" ]; then
    echo "Ilk calistirma tespit edildi, gerekli paketler kuruluyor..."
    echo "Bu islem birkac dakika surebilir, internet baglantisi gereklidir."
    "$PYTHON_BIN" -m pip install --upgrade pip
    "$PYTHON_BIN" -m pip install -r requirements.txt
    touch .kurulum_tamam
fi

echo
echo "Tesseract-OCR kurulu degilse, ekran goruntusunden otomatik varlik ekleme"
echo "calismaz (diger tum ozellikler calismaya devam eder)."
echo "Kurulum (Mac): brew install tesseract tesseract-lang"
echo "Kurulum (Linux): sudo apt install tesseract-ocr tesseract-ocr-tur"
echo

echo "Sunucu baslatiliyor: http://localhost:8000"
( sleep 2 && (open http://localhost:8000 2>/dev/null || xdg-open http://localhost:8000 2>/dev/null || true) ) &

"$PYTHON_BIN" main.py
