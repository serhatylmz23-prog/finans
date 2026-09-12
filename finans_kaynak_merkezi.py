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
        """
        Önceki sürümde bu fonksiyon hiçbir şeyi gerçekten test etmeden her
        zaman "Çalışıyor" ve sabit güven puanları döndürüyordu — panelde
        "her şey yolunda" görünüp aslında hiçbir kaynağın test edilmediği
        bir durum yaratıyordu. Artık her kaynağa kısa bir gerçek istek
        atılıp yanıt durumuna göre rapor üretiliyor.
        """
        rapor = {}

        # TCMB (döviz)
        try:
            doviz = self.doviz_getir("USDTRY")
            calisiyor = doviz.get("fiyat", 0) > 0 and doviz.get("kaynak") != "Yedek Referans"
            rapor["Döviz Kaynağı"] = {
                "durum": "Çalışıyor" if calisiyor else "Yedek Veriye Düştü",
                "kaynak_adi": doviz.get("kaynak"),
                "guven": doviz.get("guven", 50),
            }
        except Exception as e:
            rapor["Döviz Kaynağı"] = {"durum": f"Hata: {e}", "guven": 0}

        # BIST (yfinance üzerinden XU100 örneklemesi)
        try:
            bist = self.hisse_fiyat_getir("XU100")
            calisiyor = bist.get("fiyat", 0) > 0 and bist.get("kaynak") != "Veri Yok"
            rapor["BIST"] = {
                "durum": "Çalışıyor" if calisiyor else "Veri Alınamadı",
                "kaynak_adi": bist.get("kaynak"),
                "guven": bist.get("guven", 50),
            }
        except Exception as e:
            rapor["BIST"] = {"durum": f"Hata: {e}", "guven": 0}

        # TEFAS (fon_takip üzerinden gerçek bir fon kodu ile test)
        try:
            if fon_takip:
                test_fon = fon_takip.fon_bilgisi_getir("AFA")
                calisiyor = test_fon.get("fiyat", 0) > 0
                rapor["TEFAS"] = {
                    "durum": "Çalışıyor" if calisiyor else "Veri Alınamadı",
                    "guven": 90 if calisiyor else 30,
                }
            else:
                rapor["TEFAS"] = {"durum": "Modül Yüklenemedi", "guven": 0}
        except Exception as e:
            rapor["TEFAS"] = {"durum": f"Hata: {e}", "guven": 0}

        # Altın/Gümüş kaynağı
        try:
            altin = self.altin_fiyatlari_getir()
            calisiyor = altin.get("kaynak") != "Yedek Spot"
            rapor["Kıymetli Maden Kaynağı"] = {
                "durum": "Çalışıyor" if calisiyor else "Yedek Veriye Düştü",
                "kaynak_adi": altin.get("kaynak"),
                "guven": altin.get("guven", 50),
            }
        except Exception as e:
            rapor["Kıymetli Maden Kaynağı"] = {"durum": f"Hata: {e}", "guven": 0}

        return rapor

    def gercek_getiri_hesapla(self, yf_sembol: str):
        """
        Önceki sürümde aylık/yıllık getiri ya sabit koda gömülü yüzdeler
        (örn. altın için hep "+%7.8") ya da kullanıcının kendi maliyetinden
        türetilen anlamsız bir hesaptı (BIST hisseleri). İkisi de piyasanın
        gerçekte ne yaptığını yansıtmıyordu.

        Bu fonksiyon yfinance geçmiş fiyat verisinden GERÇEK 1 aylık ve
        1 yıllık yüzde değişimi hesaplar. Veri çekilemezse None döner —
        çağıran taraf bu durumda "-" (veri yok) göstermeli, uydurma bir
        sayı basmamalıdır.
        """
        try:
            t = yf.Ticker(yf_sembol)
            hist = t.history(period="1y")
            if hist is None or hist.empty or "Close" not in hist:
                return None
            close = hist["Close"].dropna()
            if len(close) < 2:
                return None

            son_fiyat = float(close.iloc[-1])

            def _yuzde_degisim(gun_sayisi):
                if len(close) <= gun_sayisi:
                    eski = float(close.iloc[0])
                else:
                    eski = float(close.iloc[-gun_sayisi])
                if eski <= 0:
                    return None
                return round(((son_fiyat - eski) / eski) * 100, 2)

            aylik = _yuzde_degisim(21)   # ~1 ay işlem günü
            yillik = _yuzde_degisim(252)  # ~1 yıl işlem günü
            if aylik is None or yillik is None:
                return None
            return {"aylik_getiri": aylik, "yillik_getiri": yillik}
        except Exception:
            return None

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