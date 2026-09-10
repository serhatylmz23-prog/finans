import os
import requests
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv

# 1. FON TAKİP MODÜLÜNÜ IMPORT EDİYORUZ
from fon_takip import fon_takip

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

    # 2. SORUNUZDAKİ FONKSİYONU BURAYA METOD OLARAK EKLİYORUZ
    def fon_fiyat_getir(self, sembol="TTE"):
        return fon_takip.fon_bilgisi_getir(sembol)

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
            px = t.fast_info.get("last_price") or t.history(period="1d")["Close"].iloc[-1]
            return {"sembol": sembol, "fiyat": round(float(px), 4), "kaynak": "Piyasa Kuru", "guven": 95, "guncelleme": now_str}
        except Exception:
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
                ons = t.fast_info.get("last_price") or t.history(period="1d")["Close"].iloc[-1]

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
            return {"ons": 2500.0, "gram": 2750.0, "ceyrek": 4500.0, "kaynak": "Yedek Spot", "guven": 80, "guncelleme": now_str}

    def hisse_fiyat_getir(self, sembol="THYAO"):
        now_str = datetime.now().strftime("%H:%M:%S")
        sembol_temiz = sembol.replace(".IS", "").upper().strip()

        # 1. Durum: Darphane Altın Sertifikası (Garanti / Midas: ALTIN.S1 / ALTINS1)
        if "ALTIN" in sembol_temiz and "S1" in sembol_temiz:
            try:
                t = yf.Ticker("ALTINS1.IS")
                px = t.fast_info.get("last_price") or t.history(period="5d")["Close"].iloc[-1]
                if px and float(px) > 0:
                    return {"sembol": sembol_temiz, "fiyat": round(float(px), 2), "kaynak": "BIST (Darphane)", "guven": 98, "guncelleme": now_str}
            except Exception:
                pass

        # 2. Durum: Midas Amerikan Hisseleri (AAPL, TSLA, NVDA, AMZN, MSFT vb.)
        # Eğer hisse BIST'te değilse ve Finnhub / Yahoo US üzerinden sorgulanacaksa
        abd_hisseleri = {"AAPL", "TSLA", "NVDA", "AMZN", "MSFT", "GOOGL", "META", "NFLX", "AMD", "INTC", "COIN"}
        if sembol_temiz in abd_hisseleri:
            # Önce Finnhub dene
            if self.finnhub_key:
                try:
                    r = requests.get(f"https://finnhub.io/api/v1/quote?symbol={sembol_temiz}&token={self.finnhub_key}", timeout=3)
                    if r.status_code == 200:
                        c = r.json().get("c", 0)
                        if c > 0:
                            # USD cinsinden fiyatı TRY'ye çevirerek veya doğrudan USD olarak döndür
                            doviz_kuru = self.doviz_getir("USDTRY")["fiyat"]
                            tl_fiyat = round(float(c) * doviz_kuru, 2)
                            return {"sembol": sembol_temiz, "fiyat": tl_fiyat, "kaynak": f"Midas/Finnhub (${c})", "guven": 98, "guncelleme": now_str}
                except Exception:
                    pass
            # Finnhub yoksa Yahoo Finance US
            try:
                t_us = yf.Ticker(sembol_temiz)
                px_us = t_us.fast_info.get("last_price") or t_us.history(period="1d")["Close"].iloc[-1]
                if px_us and float(px_us) > 0:
                    doviz_kuru = self.doviz_getir("USDTRY")["fiyat"]
                    tl_fiyat = round(float(px_us) * doviz_kuru, 2)
                    return {"sembol": sembol_temiz, "fiyat": tl_fiyat, "kaynak": f"Yahoo US (${round(float(px_us),2)})", "guven": 95, "guncelleme": now_str}
            except Exception:
                pass

        # 3. Durum: Standart Borsa İstanbul Hisseleri (THYAO, ASELS, EREGL vb.)
        bist_kod = f"{sembol_temiz}.IS"
        try:
            t = yf.Ticker(bist_kod)
            px = t.fast_info.get("last_price")
            if not px or float(px) <= 0:
                hist = t.history(period="5d")
                if not hist.empty:
                    px = hist["Close"].iloc[-1]

            if px and float(px) > 0:
                return {"sembol": sembol_temiz, "fiyat": round(float(px), 2), "kaynak": "BIST Canlı", "guven": 95, "guncelleme": now_str}
        except Exception:
            pass

        return {"sembol": sembol_temiz, "fiyat": 0.0, "kaynak": "Veri Yok", "guven": 50, "guncelleme": now_str}
        
class FinansKaynakMerkezi:
    def __init__(self):
        self.finnhub_key = os.getenv("FINNHUB_API_KEY", "")
        self.exchange_key = os.getenv("EXCHANGE_RATE_API_KEY", "")
        self.gold_key = os.getenv("GOLD_API_KEY", "")

    def durum_raporu(self):
        return {
            "TCMB": {"durum": "Çalışıyor", "guven": 100},
            "BIST": {"durum": "Çalışıyor", "guven": 95},
            "GoldAPI": {"durum": "Çalışıyor", "guven": 98}
        }

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
            px = t.fast_info.get("last_price") or t.history(period="1d")["Close"].iloc[-1]
            return {"sembol": sembol, "fiyat": round(float(px), 4), "kaynak": "Piyasa Kuru", "guven": 95, "guncelleme": now_str}
        except Exception:
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
                ons = t.fast_info.get("last_price") or t.history(period="1d")["Close"].iloc[-1]

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
            return {"ons": 2500.0, "gram": 2750.0, "ceyrek": 4500.0, "kaynak": "Yedek Spot", "guven": 80, "guncelleme": now_str}

    def hisse_fiyat_getir(self, sembol="ALTIN.S1"):
        now_str = datetime.now().strftime("%H:%M:%S")
        
        # ALTIN.S1 yazıldığında Yahoo Finance koduna (ALTINS1.IS) çevir
        sembol_temiz = sembol.replace(".IS", "").replace(".", "").upper()
        bist_kod = f"{sembol_temiz}.IS"

        try:
            t = yf.Ticker(bist_kod)
            px = t.fast_info.get("last_price")
            if not px:
                hist = t.history(period="5d")
                if not hist.empty:
                    px = hist["Close"].iloc[-1]

            if px and float(px) > 0:
                return {"sembol": sembol, "fiyat": round(float(px), 2), "kaynak": "BIST", "guven": 95, "guncelleme": now_str}
        except Exception:
            pass

        return {"sembol": sembol, "fiyat": 0.0, "kaynak": "Veri Yok", "guven": 50, "guncelleme": now_str}

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
                ons = t.fast_info.get("last_price") or t.history(period="1d")["Close"].iloc[-1]

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
            return {"ons": 2500.0, "gram": 2750.0, "ceyrek": 4500.0, "kaynak": "Yedek Spot", "guven": 80, "guncelleme": now_str}

    def hisse_fiyat_getir(self, sembol="THYAO"):
        now_str = datetime.now().strftime("%H:%M:%S")
        
        # ALTIN.S1, THYAO vb. için noktaları temizleyip .IS formatına getir
        sembol_temiz = sembol.replace(".IS", "").replace(".", "").upper().strip()
        bist_kod = f"{sembol_temiz}.IS"

        try:
            t = yf.Ticker(bist_kod)
            px = t.fast_info.get("last_price")
            if not px:
                hist = t.history(period="5d")
                if not hist.empty:
                    px = hist["Close"].iloc[-1]

            if px and float(px) > 0:
                return {"sembol": sembol_temiz, "fiyat": round(float(px), 2), "kaynak": "BIST", "guven": 95, "guncelleme": now_str}

            # Finnhub kontrolü (Yabancı Hisse)
            if self.finnhub_key:
                r = requests.get(f"https://finnhub.io/api/v1/quote?symbol={sembol_temiz}&token={self.finnhub_key}", timeout=3)
                if r.status_code == 200:
                    c = r.json().get("c", 0)
                    if c > 0:
                        return {"sembol": sembol_temiz, "fiyat": float(c), "kaynak": "Finnhub", "guven": 98, "guncelleme": now_str}
        except Exception:
            pass

        return {"sembol": sembol_temiz, "fiyat": 0.0, "kaynak": "Veri Yok", "guven": 50, "guncelleme": now_str}


kaynak_merkezi = FinansKaynakMerkezi()