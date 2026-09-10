import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(".env.local")

class FonTakipMerkezi:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://www.tefas.gov.tr",
            "Referer": "https://www.tefas.gov.tr/TarihselVeriler.aspx",
            "X-Requested-With": "XMLHttpRequest"
        }
        # TEFAS oturumu ve oturum çerezi başlatma
        try:
            self.session.get("https://www.tefas.gov.tr/TarihselVeriler.aspx", headers=self.headers, timeout=5)
        except Exception:
            pass

    def fon_bilgisi_getir(self, fon_kodu="TTE"):
        fon_kodu = fon_kodu.upper().strip()
        now_str = datetime.now().strftime("%H:%M:%S")
        bugun = datetime.now()
        
        # Son 400 günün kayıtlarını çek (1 aylık ve 1 yıllık getiri hesabı için)
        baslangic = bugun - timedelta(days=400)

        # 1. YÖNTEM: TEFAS Tarihsel Veri Servisi
        payload = {
            "fontip": "YAT",
            "bastarih": baslangic.strftime("%d.%m.%Y"),
            "bittarih": bugun.strftime("%d.%m.%Y"),
            "fonkod": fon_kodu
        }

        try:
            url = "https://www.tefas.gov.tr/api/DB/BindHistoryInfo"
            r = self.session.post(url, data=payload, headers=self.headers, timeout=10)

            # Eğer YAT (Yatırım Fonu) boş dönerse fontip parametresini boş gönderip tüm fon tiplerinde dene
            if r.status_code == 200:
                veri = r.json().get("data", [])
                if not veri:
                    payload["fontip"] = ""
                    r = self.session.post(url, data=payload, headers=self.headers, timeout=10)
                    veri = r.json().get("data", [])

                if veri and len(veri) > 0:
                    # Tarihe göre sıralandığından emin ol ve en son açıklanan kaydı al
                    son_kayit = veri[-1]
                    fiyat_ham = str(son_kayit.get("FIYAT", 0)).replace(",", ".")
                    guncel_fiyat = float(fiyat_ham)

                    # 1 Aylık Getiri: Son 22 işlem günü öncesi
                    aylik_getiri = 0.0
                    idx_ay = max(0, len(veri) - 22)
                    aylik_eski_fiyat = float(str(veri[idx_ay].get("FIYAT", 0)).replace(",", "."))
                    if aylik_eski_fiyat > 0:
                        aylik_getiri = round(((guncel_fiyat - aylik_eski_fiyat) / aylik_eski_fiyat) * 100, 2)

                    # 1 Yıllık Getiri: Listenin başı (~250 işlem günü öncesi)
                    yillik_getiri = 0.0
                    idx_yil = max(0, len(veri) - 252)
                    yillik_eski_fiyat = float(str(veri[idx_yil].get("FIYAT", 0)).replace(",", "."))
                    if yillik_eski_fiyat > 0:
                        yillik_getiri = round(((guncel_fiyat - yillik_eski_fiyat) / yillik_eski_fiyat) * 100, 2)

                    return {
                        "sembol": fon_kodu,
                        "fon_adi": son_kayit.get("FONUNVAN", f"{fon_kodu} Fonu"),
                        "fiyat": round(guncel_fiyat, 6),
                        "tarih": son_kayit.get("TARIH", ""),
                        "aylik_getiri": aylik_getiri,
                        "yillik_getiri": yillik_getiri,
                        "kaynak": "TEFAS Canlı",
                        "durum": "Resmi Değer",
                        "guven": 100,
                        "guncelleme": now_str
                    }

        except Exception as e:
            print(f"TEFAS API İletişim Hatası ({fon_kodu}): {e}")

        # 2. YÖNTEM: TEFAS Fon Kartı Doğrudan Sorgusu (Fallback)
        try:
            r_kart = self.session.post(
                "https://www.tefas.gov.tr/api/DB/BindFundInfo",
                data={"fonkod": fon_kodu},
                headers=self.headers,
                timeout=6
            )
            if r_kart.status_code == 200:
                d_kart = r_kart.json().get("data", [])
                if d_kart:
                    fiyat = float(str(d_kart[0].get("FIYAT", 0)).replace(",", "."))
                    return {
                        "sembol": fon_kodu,
                        "fon_adi": d_kart[0].get("FONUNVAN", f"{fon_kodu} Fonu"),
                        "fiyat": round(fiyat, 6),
                        "aylik_getiri": float(str(d_kart[0].get("GETIRI1A", 0)).replace(",", ".")),
                        "yillik_getiri": float(str(d_kart[0].get("GETIRI1Y", 0)).replace(",", ".")),
                        "kaynak": "TEFAS Kart",
                        "durum": "Resmi Değer",
                        "guven": 98,
                        "guncelleme": now_str
                    }
        except Exception:
            pass

        return {
            "sembol": fon_kodu,
            "fon_adi": f"{fon_kodu} Fonu",
            "fiyat": 0.0,
            "aylik_getiri": 0.0,
            "yillik_getiri": 0.0,
            "kaynak": "Hata",
            "durum": "Veri Alınamadı",
            "guven": 0,
            "guncelleme": now_str
        }

fon_takip = FonTakipMerkezi()