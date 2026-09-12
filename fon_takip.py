import requests
import time
from datetime import datetime

CACHE_SURESI_SN = 300  # 5 dakika - TEFAS fon fiyatları günde bir kez güncellenir ama
                        # sunucu açık kaldığı sürece eski cache'e takılıp kalmasın diye
                        # yine de periyodik tazeleme yapılır.

class FonTakipMerkezi:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.tefas.gov.tr/"
        }
        self.cache = {}
        self.cache_zamani = {}

    def fon_bilgisi_getir(self, fon_kodu="AYA"):
        fon_kodu = str(fon_kodu).upper().strip()
        now_str = datetime.now().strftime("%H:%M:%S")

        if fon_kodu in self.cache:
            if time.time() - self.cache_zamani.get(fon_kodu, 0) < CACHE_SURESI_SN:
                return self.cache[fon_kodu]

        # 1. YÖNTEM: TEFAS Resmi Karşılaştırma / Genel Veri Servisi (Engellenmeyen JSON Endpoint)
        try:
            url = "https://www.tefas.gov.tr/api/DB/BindHistoryAllocations"
            r = requests.post(url, data={"fonkod": fon_kodu}, headers=self.headers, timeout=4)
            if r.status_code == 200:
                d = r.json().get("data", [])
                if d:
                    fiyat = float(str(d[-1].get("FIYAT", 0)).replace(",", "."))
                    if fiyat > 0:
                        res = {
                            "sembol": fon_kodu,
                            "fiyat": round(fiyat, 6),
                            "aylik_getiri": 0.0,
                            "yillik_getiri": 0.0,
                            "durum": "Canlı",
                            "guncelleme": now_str
                        }
                        self.cache[fon_kodu] = res
                        self.cache_zamani[fon_kodu] = time.time()
                        return res
        except Exception:
            pass

        # 2. YÖNTEM: Alternatif Finans Fon Servisi (TEFAS Yedeği)
        try:
            # Doğrudan TEFAS Fon Bilgi Sayfasından Regex/JSON
            url_alt = f"https://ws.spk.gov.tr/PortfolioInvestments/api/Funds/{fon_kodu}"
            r2 = requests.get(url_alt, headers=self.headers, timeout=3)
            if r2.status_code == 200:
                data = r2.json()
                fiyat = float(data.get("Price", data.get("Fiyat", 0)))
                if fiyat > 0:
                    res = {
                        "sembol": fon_kodu,
                        "fiyat": round(fiyat, 6),
                        "aylik_getiri": 0.0,
                        "yillik_getiri": 0.0,
                        "durum": "Canlı",
                        "guncelleme": now_str
                    }
                    self.cache[fon_kodu] = res
                    self.cache_zamani[fon_kodu] = time.time()
                    return res
        except Exception:
            pass

        # 3. YÖNTEM: TefasCrawler / Hızlı Web Arama
        try:
            url_tefas = "https://www.tefas.gov.tr/api/DB/BindFundInfo"
            r3 = requests.post(
                url_tefas, 
                data={"fonkod": fon_kodu}, 
                headers={
                    **self.headers,
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest"
                }, 
                timeout=4
            )
            if r3.status_code == 200:
                data3 = r3.json().get("data", [])
                if data3:
                    fiyat = float(str(data3[0].get("FIYAT", 0)).replace(",", "."))
                    aylik = float(str(data3[0].get("GETIRI1A", 0)).replace(",", "."))
                    yillik = float(str(data3[0].get("GETIRI1Y", 0)).replace(",", "."))
                    if fiyat > 0:
                        res = {
                            "sembol": fon_kodu,
                            "fiyat": round(fiyat, 6),
                            "aylik_getiri": aylik,
                            "yillik_getiri": yillik,
                            "durum": "Canlı",
                            "guncelleme": now_str
                        }
                        self.cache[fon_kodu] = res
                        self.cache_zamani[fon_kodu] = time.time()
                        return res
        except Exception:
            pass

        return {
            "sembol": fon_kodu,
            "fiyat": 0.0,
            "aylik_getiri": 0.0,
            "yillik_getiri": 0.0,
            "durum": "Alınamadı",
            "guncelleme": now_str
        }

fon_takip = FonTakipMerkezi()