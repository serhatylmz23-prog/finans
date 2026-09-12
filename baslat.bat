@echo off
chcp 65001 >nul
title SyFinansOtagi
cd /d "%~dp0"

echo ============================================
echo   SyFinansOtagi baslatiliyor...
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [HATA] Python bulunamadi. Once https://www.python.org/downloads/ adresinden
    echo Python 3.11+ kurun ve kurulum sirasinda "Add Python to PATH" secenegini isaretleyin.
    pause
    exit /b 1
)

if not exist ".kurulum_tamam" (
    echo Ilk calistirma tespit edildi, gerekli paketler kuruluyor...
    echo Bu islem birkac dakika surebilir, internet baglantisi gereklidir.
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [HATA] Paket kurulumu basarisiz oldu. Yukaridaki hatayi kontrol edin.
        pause
        exit /b 1
    )
    echo. > .kurulum_tamam
)

echo.
echo Tesseract-OCR kurulu degilse, ekran goruntusunden otomatik varlik ekleme
echo calismaz (diger tum ozellikler calismaya devam eder).
echo Kurulum: https://github.com/UB-Mannheim/tesseract/wiki
echo.

echo Sunucu baslatiliyor: http://localhost:8000
start "" http://localhost:8000
python main.py

pause
