import os
import re
import cv2
import numpy as np
import pytesseract

tesseract_yolu = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(tesseract_yolu):
    pytesseract.pytesseract.tesseract_cmd = tesseract_yolu

try:
    import easyocr
    reader = easyocr.Reader(['tr', 'en'], gpu=False, verbose=False)
except Exception:
    reader = None

class PortfoyGoruntuAjan:
    def __init__(self):
        self.gecersiz = {
            "ADET", "FIYAT", "TUTAR", "TOPLAM", "PORTFOY", "HESAP", "BAKIYE", 
            "KULLANILABILIR", "HISSE", "FON", "TRY", "TL", "USD", "IBAN", 
            "GUNLUK", "DEGISIM", "MALIYET", "KAR", "ZARAR", "SUBE", "NO", "PIYASA", "DEGERI"
        }

    def resimden_metin_cikar(self, img_bytes):
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return ""

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast = clahe.apply(gray)

        metin = ""
        try:
            metin = pytesseract.image_to_string(contrast, lang='tur+eng')
        except Exception:
            try:
                metin = pytesseract.image_to_string(contrast)
            except Exception:
                pass

        if not metin.strip() and reader:
            try:
                sonuclar = reader.readtext(contrast, detail=0)
                metin = "\n".join(sonuclar)
            except Exception:
                pass

        return metin

    def _sayi_temizle(self, s):
        """
        Garanti ve Midas'taki 29.550,00 veya 295,50 sayılarını doğru float yapar.
        """
        s = s.strip().replace("₺", "").replace("$", "").replace("TL", "").strip()
        if not s:
            return 0.0

        # Eğer hem nokta hem virgül varsa (Örn: 29.550,00)
        if "." in s and "," in s:
            if s.find(".") < s.find(","):
                # TR formatı: 29.550,00 -> 29550.00
                s = s.replace(".", "").replace(",", ".")
            else:
                # US formatı: 29,550.00 -> 29550.00
                s = s.replace(",", "")
        elif "," in s:
            # Sadece virgül varsa: 295,50 -> 295.50
            s = s.replace(",", ".")
        elif "." in s:
            # Sadece nokta varsa: 295.50 (Ondalık) veya 1.500 (Binlik)
            parcalar = s.split(".")
            if len(parcalar[-1]) == 3: # 1.500 gibi binlik tam sayı
                s = s.replace(".", "")
        try:
            return float(s)
        except Exception:
            return 0.0

    def portfoy_ayikla(self, ocr_metin):
        varliklar = []
        if not ocr_metin or not ocr_metin.strip():
            return varliklar

        satirlar = [satir.strip() for satir in ocr_metin.split("\n") if satir.strip()]
        
        for i, satir in enumerate(satirlar):
            s_upper = satir.upper()
            
            # Sembol Adayları (3-6 karakter büyük harf, örn: THYAO, AAPL, TTE, ALTINS1)
            kelimeler = re.findall(r"\b[A-Z0-9\.]{3,7}\b", s_upper)
            
            sembol = None
            if "GRAM ALTIN" in s_upper or "ALTIN" in s_upper and "S1" not in s_upper:
                sembol = "GRAM ALTIN"
            else:
                for k in kelimeler:
                    k_sade = k.replace(".", "")
                    if k_sade not in self.gecersiz and not k_sade.isdigit() and len(k_sade) >= 3:
                        sembol = k
                        break

            if sembol:
                # Satırdaki ve hemen sonraki 2 satırdaki tüm sayıları topla
                arama_alani = " " + satir
                if i + 1 < len(satirlar):
                    arama_alani += " " + satirlar[i+1]
                if i + 2 < len(satirlar):
                    arama_alani += " " + satirlar[i+2]

                sayilar_raw = re.findall(r"\b\d+[\.,]?\d*[\.,]?\d*\b", arama_alani)
                sayilar = [self._sayi_temizle(x) for x in sayilar_raw if self._sayi_temizle(x) > 0]

                adet = 0.0
                maliyet = 0.0

                if len(sayilar) >= 3:
                    # Garanti/Midas tipik sıralaması: [Adet, Maliyet, Toplam Tutar]
                    # Adet ve Maliyetin çarpımı yaklaşık Toplam Tutara eşit olmalıdır
                    s0, s1, s2 = sayilar[0], sayilar[1], sayilar[2]
                    if abs((s0 * s1) - s2) < (s2 * 0.15) + 5:
                        adet, maliyet = s0, s1
                    elif abs((s1 * s2) - s0) < (s0 * 0.15) + 5:
                        adet, maliyet = s1, s2
                    else:
                        adet, maliyet = s0, s1
                elif len(sayilar) == 2:
                    adet, maliyet = sayilar[0], sayilar[1]
                elif len(sayilar) == 1:
                    adet = sayilar[0]

                # Aşırı büyük maliyet koruması (Adet ile toplam tutarın karışmasını engeller)
                if adet > 0:
                    if maliyet > 15000 and "ALTIN" not in sembol:
                        # Eğer maliyet 15.000 TL'den büyükse muhtemelen toplam tutar yanlışlıkla maliyete yazılmıştır
                        maliyet = round(maliyet / adet, 2)

                    if not any(v["sembol"] == sembol for v in varliklar):
                        varliklar.append({
                            "sembol": sembol,
                            "adet": adet,
                            "maliyet": maliyet
                        })

        return varliklar

goruntu_ajani = PortfoyGoruntuAjan()