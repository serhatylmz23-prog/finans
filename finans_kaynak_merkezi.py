import os
import requests
import json
import websocket
import yfinance as yf
from datetime import datetime, timedelta
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, TimeoutError as _FutureTimeoutError

_zaman_asimi_havuzu = ThreadPoolExecutor(max_workers=16)

def zaman_siniriyla(fn, saniye=4, *args, **kwargs):
    try:
        gelecek = _zaman_asimi_havuzu.submit(fn, *args, **kwargs)
        return gelecek.result(timeout=saniye)
    except _FutureTimeoutError:
        return None
    except Exception:
        return None

def _yf_son_fiyat(yf_kodu: str, period: str = "5d"):
    def _getir():
        t = yf.Ticker(yf_kodu)
        px = t.fast_info.get("last_price")
        if not px:
            hist = t.history(period=period)
            if not hist.empty:
                px = hist["Close"].iloc[-1]
        return float(px) if px else None
    return zaman_siniriyla(_getir, saniye=4)

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
        self.cdp_port = 9222

    def cdp_tradingview_canli_fiyat_cek(self, sembol: str):
        """
        Edge/Chrome üzerinde açık olan TradingView CDP portu (9222) üzerinden
        aktif sekmeye bağlanarak DOM üzerindeki canlı fiyatı doğrudan çeker.
        """
        try:
            r = requests.get(f"http://localhost:{self.cdp_port}/json", timeout=2)
            if r.status_code == 200:
                sekmeler = r.json()
                tv_sekme = next((s for s in sekmeler if "tradingview.com" in s.get("url", "").lower()), None)
                if tv_sekme and "webSocketDebuggerUrl" in tv_sekme:
                    ws_url = tv_sekme["webSocketDebuggerUrl"]
                    
                    payload = {
                        "id": 1,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": "document.querySelector('.last-is-price-line, .tv-symbol-price-quote__value')?.innerText || document.querySelector('[data-name=\"price-value\"]')?.innerText || ''"
                        }
                    }
                    
                    ws = websocket.create_connection(ws_url, timeout=2)
                    ws.send(json.dumps(payload))
                    resp = ws.recv()
                    ws.close()
                    
                    data = json.loads(resp)
                    fiyat_metni = data.get("result", {}).get("result", {}).get("value", "")
                    
                    if fiyat_metni:
                        temiz_fiyat = float(fiyat_metni.replace(".", "").replace(",", ".").strip())
                        if temiz_fiyat > 0:
                            return {
                                "sembol": sembol,
                                "fiyat": temiz_fiyat,
                                "kaynak": "TradingView CDP Canlı DOM (Port 9222)",
                                "guven": 99
                            }
        except Exception:
            pass
        return None

    def durum_raporu(self):
        rapor = {}

        # Döviz
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

        # BIST
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

        # TEFAS
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

        # TradingView CDP Köprü Durumu
        try:
            r_cdp = requests.get(f"http://localhost:{self.cdp_port}/json/version", timeout=2)
            cdp_aktif = r_cdp.status_code == 200
            rapor["TradingView CDP (9222)"] = {
                "durum": "Aktif ve Bağlı (DOM Okuma Hazır)" if cdp_aktif else "Port Yanıt Vermiyor",
                "guven": 100 if cdp_aktif else 0
            }
        except Exception:
            rapor["TradingView CDP (9222)"] = {"durum": "Bağlantı Kurulamadı", "guven": 0}

        return rapor

    def gercek_getiri_hesapla(self, yf_sembol: str):
        def _getir():
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

            aylik = _yuzde_degisim(21)
            yillik = _yuzde_degisim(252)
            if aylik is None or yillik is None:
                return None
            return {"aylik_getiri": aylik, "yillik_getiri": yillik}

        return zaman_siniriyla(_getir, saniye=6)

    def grafik_ve_analiz_yorumlari_getir(self, sembol="THYAO"):
        sembol_temiz = sembol.replace(".IS", "").replace(".", "").upper().strip()
        yf_kod = f"{sembol_temiz}.IS" if not sembol_temiz in ["USDTRY", "GC=F", "SI=F"] else sembol_temiz
        
        getiriler = self.gercek_getiri_hesapla(yf_kod) or {"aylik_getiri": 0.0, "yillik_getiri": 0.0}
        
        aylik = getiriler.get("aylik_getiri", 0.0) or 0.0
        teknik_egilim = "Yükseliş Trendi (Boğa)" if aylik > 0 else "Düşüş / Yatay Konsolidasyon"
        
        yorumlar = {
            "sembol": sembol_temiz,
            "teknik_egilim": teknik_egilim,
            "aylik_getiri_yuzde": aylik,
            "yillik_getiri_yuzde": getiriler.get("yillik_getiri", 0.0),
            "cdp_durum": self.cdp_tradingview_canli_fiyat_cek(sembol_temiz),
            "analiz_notu": f"{sembol_temiz} varlığı için son 1 aylık performans %{aylik} seviyesindedir. TradingView CDP köprüsü üzerinden canlı grafik taranmaktadır."
        }
        return yorumlar

    def gumus_fiyatlari_getir(self):
        now_str = datetime.now().strftime("%H:%M:%S")
        try:
            r = requests.get("https://finans.truncgil.com/v3/today.json", timeout=3)
            if r.status_code == 200:
                data = r.json()
                if "GUMUS" in data:
                    fiyat_str = str(data["GUMUS"].get("Selling", "0")).replace(".", "").replace(",", ".")
                    gram = float(fiyat_str)
                    if gram > 0:
                        return {"gram": round(gram, 2), "kaynak": "Truncgil (Canlı)", "guven": 92, "guncelleme": now_str}
        except Exception:
            pass

        try:
            usd_fiyat = self.doviz_getir("USDTRY")["fiyat"]
            ons = _yf_son_fiyat("SI=F", period="1d")
            if ons and float(ons) > 0:
                gram = (float(ons) * usd_fiyat) / 31.1034768
                return {"gram": round(gram, 2), "kaynak": "Spot Ons (Gümüş, yfinance)", "guven": 88, "guncelleme": now_str}
        except Exception:
            pass

        return {"gram": 89.50, "kaynak": "Yedek Referans", "guven": 50, "guncelleme": now_str}

    def fon_fiyat_getir(self, sembol="TTE"):
        sembol_temiz = sembol.upper().strip()
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

        if fon_takip:
            try:
                veri = fon_takip.fon_bilgisi_getir(sembol_temiz)
                if veri and veri.get("fiyat", 0) > 0:
                    return veri
                return veri
            except Exception:
                pass

        return {"fiyat": 0.0, "aylik_getiri": 0.0, "yillik_getiri": 0.0, "durum": "fon_takip modülü yüklenemedi"}

    def doviz_getir(self, sembol="USDTRY"):
        now_str = datetime.now().strftime("%H:%M:%S")
        try:
            if self.exchange_key:
                r = requests.get(f"https://v6.exchangerate-api.com/v6/{self.exchange_key}/latest/USD", timeout=3)
                if r.status_code == 200:
                    val = r.json().get("conversion_rates", {}).get("TRY")
                    if val:
                        return {"sembol": sembol, "fiyat": float(val), "kaynak": "ExchangeRate-API", "guven": 100, "guncelleme": now_str}

            px = _yf_son_fiyat("USDTRY=X", period="1d")
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
                ons = _yf_son_fiyat("GC=F", period="1d")

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

        # 1. Önce açık olan TradingView CDP sekmesinden canlı DOM verisini dene (ALTINS1 dahil primli fiyatlar için)
        cdp_canli = self.cdp_tradingview_canli_fiyat_cek(sembol_temiz)
        if cdp_canli and cdp_canli.get("fiyat", 0) > 0:
            return {
                "sembol": sembol_temiz,
                "fiyat": cdp_canli["fiyat"],
                "kaynak": cdp_canli["kaynak"],
                "guven": cdp_canli["guven"],
                "guncelleme": now_str
            }

        # 2. ALTINS1 ve primli varlıklar için yfinance veya saf altın yedeği
        if "ALTIN" in sembol_temiz and "S1" in sembol_temiz or sembol_temiz in ["ALTINS1", "ALTIN_S1"]:
            px = _yf_son_fiyat("ALTIN.IS")
            if px and float(px) > 0:
                return {"sembol": "ALTINS1", "fiyat": round(float(px), 2), "kaynak": "BIST Canlı (yfinance: ALTIN.IS)", "guven": 95, "guncelleme": now_str}

            try:
                altin_verisi = self.altin_fiyatlari_getir()
                gram_fiyat = float(altin_verisi.get("gram", 0.0))
                if gram_fiyat > 0:
                    sertifika_fiyati = round(gram_fiyat * 0.0101, 2)
                    return {
                        "sembol": "ALTINS1",
                        "fiyat": sertifika_fiyati,
                        "kaynak": "TAHMİNİ (spot altın bazlı, borsada primli işlem görebilir)",
                        "guven": 45,
                        "guncelleme": now_str
                    }
            except Exception:
                pass
            return {"sembol": "ALTINS1", "fiyat": 70.0, "kaynak": "Referans (veri alınamadı)", "guven": 30, "guncelleme": now_str}

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

        bist_kod = f"{sembol_temiz}.IS"
        px = _yf_son_fiyat(bist_kod, period="5d")
        if px and float(px) > 0:
            return {"sembol": sembol_temiz, "fiyat": round(float(px), 2), "kaynak": "BIST Canlı", "guven": 95, "guncelleme": now_str}

        return {"sembol": sembol_temiz, "fiyat": 0.0, "kaynak": "Veri Yok", "guven": 50, "guncelleme": now_str}

    def hisse_ek_bilgi_getir(self, sembol="THYAO"):
        sembol_temiz = sembol.replace(".IS", "").replace(".", "").upper().strip()
        bist_kod = f"{sembol_temiz}.IS"

        def _getir_info():
            t = yf.Ticker(bist_kod)
            return t.get_info() if hasattr(t, "get_info") else t.info

        info = zaman_siniriyla(_getir_info, saniye=6) or {}

        def _al(*anahtarlar):
            for a in anahtarlar:
                if info.get(a) not in (None, 0):
                    return info.get(a)
            return None

        piyasa_degeri = _al("marketCap")
        pay_sayisi = _al("sharesOutstanding", "impliedSharesOutstanding")
        temettu_tarihi_ts = _al("exDividendDate")
        temettu_tarihi = None
        if temettu_tarihi_ts:
            try:
                temettu_tarihi = datetime.utcfromtimestamp(int(temettu_tarihi_ts)).strftime("%d.%m.%Y")
            except Exception:
                temettu_tarihi = None
        temettu_verimi = _al("dividendYield")

        return {
            "sembol": sembol_temiz,
            "piyasa_degeri_try": piyasa_degeri,
            "pay_sayisi": pay_sayisi,
            "temettu_tarihi": temettu_tarihi,
            "temettu_verimi": temettu_verimi,
            "yatirimci_sayisi": None,
        }

kaynak_merkezi = FinansKaynakMerkezi()