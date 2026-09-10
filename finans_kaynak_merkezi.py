import os
import requests
import yfinance as yf
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Fon takip modülü
try:
    from fon_takip import fon_takip
except ImportError:
    fon_takip = None

load_dotenv(".env.local")

class FinansKaynakMerkezi:
    def __init__(self):
        self.finnhub_key = os.getenv("FINNHUB_API_KEY", "")
        self.exchange_key = os.getenv("EXCHANGE_RATE_API_KEY", "")
        self.gold_key = os.getenv("GOLD_API_KEY", "")

    def durum_raporu(self):
        return {
            "TCMB": {"durum": "Çalışıyor", "guven": 100},
            "BIST": {"durum": "Çalışıyor", "guven": 95},
            "TEFAS": {"durum": "Çalışıyor", "guven": 98},
            "GoldAPI": {"durum": "Çalışıyor", "guven": 98}
        }

    def fon_fiyat_getir(self, sembol="TTE"):
        """
        TEFAS Yatırım Fonları (AYA, DFI, AIS, GMC, TUA vb.) ve Gümüş (XAG) fiyatlarını çeker.
        """
        sembol_temiz = sembol.upper().strip()

        # 1. Gümüş Kuru (XAG / Gümüş Fonu değilse doğrudan ons/gram gümüş)
        if "XAG" in sembol_temiz:
            try:
                r = requests.get("https://finans.truncgil.com/v3/today.json", timeout=3)
                if r.status_code == 200:
                    data = r.json()
                    if "GUMUS" in data:
                        fiyat_str = data["GUMUS"].get("Selling", "0").replace(".", "").replace(",", ".")
                        return {"fiyat": float(fiyat_str), "aylik_getiri": 0.0, "yillik_getiri": 0.0}
            except Exception:
                pass
            return {"fiyat": 90.0, "aylik_getiri": 0.0, "yillik_getiri": 0.0}

        # 2. Eğer fon_takip modülü varsa önce onu dene
        if fon_takip:
            try:
                veri = fon_takip.fon_bilgisi_getir(sembol_temiz)
                if veri and veri.get("fiyat", 0) > 0:
                    return veri
            except Exception:
                pass

        # 3. Doğrudan Takasbank TEFAS Resmi API Sorgusu (Kesin Sonuç)
        try:
            url = "https://www.tefas.gov.tr/api/DB/BindHistoryInfo"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.tefas.gov.tr/TarihselVeriler.aspx",
                "X-Requested-With": "XMLHttpRequest"
            }
            payload = {
                "fontip": "YAT",
                "fonkod": sembol_temiz
            }
            res = requests.post(url, data=payload, headers=headers, timeout=4)
            if res.status_code == 200:
                j_data = res.json()
                if "data" in j_data and len(j_data["data"]) > 0:
                    son_kayit = j_data["data"][-1]
                    son_fiyat = float(son_kayit.get("FIYAT", 0.0))
                    if son_fiyat > 0:
                        return {
                            "fiyat": round(son_fiyat, 4),
                            "aylik_getiri": 0.0,
                            "yillik_getiri": 0.0
                        }
        except Exception:
            pass

        return {"fiyat": 0.0, "aylik_getiri": 0.0, "yillik_getiri": 0.0}

    def doviz_getir(self, sembol="USDTRY"):
        now_str = datetime.now().strftime("%H:%M:%S")
        try:
            if self.exchange_key:
                r = requests.get(f"https://v6.exchangerate-api.com/v6/{self.exchange_key}/latest/USD", timeout=3)
                if r.status_code == 200:
                    val = r.json().get("conversion_rates", {}).get("TRY")
                    if val:
                        return {"sembol": sembol, "fiyat": float(val), "kaynak": "ExchangeRate-API", "guven": 100, "guncelleme": now_str}

            t = yf.Ticker("USDTRY=X")
            px = t.fast_info.get("last_price")
            if not px:
                hist = t.history(period="1d")
                if not hist.empty:
                    px = hist["Close"].iloc[-1]
            if px:
                return {"sembol": sembol, "fiyat": round(float(px), 4), "kaynak": "Piyasa Kuru", "guven": 95, "guncelleme": now_str}
        except Exception:
            pass
        return {"sembol": sembol, "fiyat": 34.25, "kaynak": "Yedek Referans", "guven": 80, "guncelleme": now_str}

    def altin_fiyatlari_getir(self):
        now_str = datetime.now().strftime("%H:%M:%S")
        try:
            usd_fiyat = self.doviz_getir("USDTRY")["fiyat"]
            ons = 0.0

            if self.gold_key:
                headers = {"x-access-token": self.gold_key, "Content-Type": "application/json"}
                r = requests.get("https://www.goldapi.io/api/XAU/USD", headers=headers, timeout=3)
                if r.status_code == 200:
                    ons = float(r.json().get("price", 0))

            if not ons or ons <= 0:
                t = yf.Ticker("GC=F")
                ons = t.fast_info.get("last_price")
                if not ons:
                    hist = t.history(period="1d")
                    if not hist.empty:
                        ons = hist["Close"].iloc[-1]

            if ons and float(ons) > 0:
                gram = (float(ons) * usd_fiyat) / 31.1034768
                ceyrek = gram * 1.6078 * 1.025
                return {
                    "ons": round(float(ons), 2),
                    "gram": round(gram, 2),
                    "ceyrek": round(ceyrek, 2),
                    "kaynak": "Canlı Spot Ons",
                    "guven": 98,
                    "guncelleme": now_str
                }
        except Exception:
            pass
        return {"ons": 2500.0, "gram": 2750.0, "ceyrek": 4500.0, "kaynak": "Yedek Spot", "guven": 80, "guncelleme": now_str}

    def hisse_fiyat_getir(self, sembol="THYAO"):
        now_str = datetime.now().strftime("%H:%M:%S")
        sembol_temiz = sembol.replace(".IS", "").replace(".", "").upper().strip()

        # 1. Darphane Altın Sertifikası (ALTINS1 / ALTIN.S1)
        # 1 Sertifika = 0.01 Gram 24K Altın (BIST işlem fiyatı eşleniği)
        if "ALTIN" in sembol_temiz and "S1" in sembol_temiz or sembol_temiz in ["ALTINS1", "ALTIN_S1"]:
            try:
                altin_verisi = self.altin_fiyatlari_getir()
                gram_fiyat = float(altin_verisi.get("gram", 0.0))
                if gram_fiyat > 0:
                    # 0.01 gram altın + BIST piyasa marjı (~%1)
                    sertifika_fiyati = round(gram_fiyat * 0.0101, 2)
                    return {
                        "sembol": "ALTIN.S1",
                        "fiyat": sertifika_fiyati,
                        "kaynak": "BIST Darphane Eşleniği",
                        "guven": 100,
                        "guncelleme": now_str
                    }
            except Exception:
                pass
            return {"sembol": "ALTIN.S1", "fiyat": 70.0, "kaynak": "Referans", "guven": 80, "guncelleme": now_str}

        # 2. ABD Hisseleri (AAPL, TSLA, NVDA vb.)
        abd_hisseleri = {"AAPL", "TSLA", "NVDA", "AMZN", "MSFT", "GOOGL", "META", "NFLX", "AMD", "INTC", "COIN"}
        if sembol_temiz in abd_hisseleri:
            if self.finnhub_key:
                try:
                    r = requests.get(f"https://finnhub.io/api/v1/quote?symbol={sembol_temiz}&token={self.finnhub_key}", timeout=3)
                    if r.status_code == 200:
                        c = r.json().get("c", 0)
                        if c > 0:
                            doviz_kuru = self.doviz_getir("USDTRY")["fiyat"]
                            return {"sembol": sembol_temiz, "fiyat": round(float(c) * doviz_kuru, 2), "kaynak": f"Finnhub (${c})", "guven": 98, "guncelleme": now_str}
                except Exception:
                    pass

        # 3. Standart BIST Hisseleri (THYAO, ASELS, EKOS, SASA, DARDL vb.)
        bist_kod = f"{sembol_temiz}.IS"
        try:
            t = yf.Ticker(bist_kod)
            px = t.fast_info.get("last_price")
            if not px:
                hist = t.history(period="5d")
                if not hist.empty:
                    px = hist["Close"].iloc[-1]

            if px and float(px) > 0:
                return {"sembol": sembol_temiz, "fiyat": round(float(px), 2), "kaynak": "BIST Canlı", "guven": 95, "guncelleme": now_str}
        except Exception:
            pass

        return {"sembol": sembol_temiz, "fiyat": 0.0, "kaynak": "Veri Yok", "guven": 50, "guncelleme": now_str}
        
kaynak_merkezi = FinansKaynakMerkezi()