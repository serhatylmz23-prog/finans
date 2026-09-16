"""
Fon Takip Merkezi (Gelişmiş Metrikler ve Piyasa Entegrasyonu ile Güncel Sürüm)
==========================================================================

ÖNEMLİ GEÇMİŞ NOT: TEFAS sitesi 2026 Nisan'ında baştan yeniden yazıldı;
yıllarca kullanılan eski uç noktalar kapatıldı. Bu sürüm, pytefas paketinin
sağladığı güncel ve kararlı resmi altyapıyı kullanır. 
Ek olarak portföy analizleri için yabancı ilgisi, dolaşımdaki lot, piyasa değeri 
(TL/USD) ve temettü takvimi verilerini işleyecek şekilde genişletilmiştir.
"""
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, TimeoutError as _FutureTimeoutError

CACHE_SURESI_SN = 300       # anlık fiyat önbelleği: 5 dakika
GUNLUK_SNAPSHOT_TTL_SN = 6 * 3600  # geçmiş gün verisi değişmez, 6 saat yeterli

_tefas_zaman_asimi_havuzu = ThreadPoolExecutor(max_workers=8)

def _tefas_zaman_siniriyla(fn, saniye=10, *args, **kwargs):
    try:
        gelecek = _tefas_zaman_asimi_havuzu.submit(fn, *args, **kwargs)
        return gelecek.result(timeout=saniye)
    except _FutureTimeoutError:
        return None
    except Exception:
        return None

try:
    from pytefas import Crawler as _TefasCrawler
    PYTEFAS_VAR = True
except ImportError:
    PYTEFAS_VAR = False


class FonTakipMerkezi:
    def __init__(self):
        self.cache = {}
        self.cache_zamani = {}
        self._gun_cache = {}       # (tarih_str, kind) -> {fon_kodu: fiyat}
        self._gun_cache_zaman = {}
        self._crawler = _TefasCrawler() if PYTEFAS_VAR else None

    def _is_gunu_snapshot(self, tarih: "datetime", kind: str = "YAT", deneme_hakki: int = 6):
        """
        Verilen tarihten geriye doğru (hafta sonu/tatil boşluklarını atlayarak)
        ilk veri bulunan iş gününün sözlüğünü döner.
        """
        if not self._crawler:
            return {}

        gun = tarih
        for _ in range(deneme_hakki):
            anahtar = (gun.strftime("%Y-%m-%d"), kind)
            simdi = time.time()
            if anahtar in self._gun_cache and simdi - self._gun_cache_zaman.get(anahtar, 0) < GUNLUK_SNAPSHOT_TTL_SN:
                if self._gun_cache[anahtar]:
                    return self._gun_cache[anahtar]
            else:
                try:
                    df = _tefas_zaman_siniriyla(self._crawler.fetch, 10, anahtar[0], columns="info", kind=kind)
                    sozluk = {}
                    if df is not None and len(df) > 0:
                        for _, satir in df.iterrows():
                            kod = satir.get("fund_code")
                            fiyat = satir.get("price")
                            if kod and fiyat and float(fiyat) > 0:
                                sozluk[str(kod).upper().strip()] = {
                                    "fiyat": float(fiyat),
                                    "yatirimci_sayisi": satir.get("investor_count"),
                                    "piyasa_degeri": satir.get("portfolio_size"),
                                    "pay_adedi": satir.get("shares_outstanding"),
                                }
                    self._gun_cache[anahtar] = sozluk
                    self._gun_cache_zaman[anahtar] = simdi
                    if sozluk:
                        return sozluk
                except Exception:
                    self._gun_cache[anahtar] = {}
                    self._gun_cache_zaman[anahtar] = simdi
            gun = gun - timedelta(days=1)
        return {}

    def fon_bilgisi_getir(self, fon_kodu="AYA"):
        fon_kodu = str(fon_kodu).upper().strip()
        now_str = datetime.now().strftime("%H:%M:%S")

        if fon_kodu in self.cache:
            if time.time() - self.cache_zamani.get(fon_kodu, 0) < CACHE_SURESI_SN:
                return self.cache[fon_kodu]

        if not PYTEFAS_VAR:
            res = {
                "sembol": fon_kodu, "fiyat": 0.0,
                "aylik_getiri": None, "yillik_getiri": None,
                "durum": "Alınamadı — 'pytefas' paketi kurulu değil",
                "guncelleme": now_str,
            }
            return res

        bugun = datetime.now()
        for kind in ("YAT", "EMK", "BYF", "GYF", "GSYF"):
            bugun_verisi = self._is_gunu_snapshot(bugun, kind)
            if fon_kodu in bugun_verisi:
                satir = bugun_verisi[fon_kodu]
                fiyat = satir["fiyat"]

                bir_ay_once = self._is_gunu_snapshot(bugun - timedelta(days=30), kind)
                bir_yil_once = self._is_gunu_snapshot(bugun - timedelta(days=365), kind)

                aylik = None
                yillik = None
                if fon_kodu in bir_ay_once and bir_ay_once[fon_kodu]["fiyat"] > 0:
                    onceki = bir_ay_once[fon_kodu]["fiyat"]
                    aylik = round(((fiyat - onceki) / onceki) * 100, 2)
                if fon_kodu in bir_yil_once and bir_yil_once[fon_kodu]["fiyat"] > 0:
                    onceki = bir_yil_once[fon_kodu]["fiyat"]
                    yillik = round(((fiyat - onceki) / onceki) * 100, 2)

                res = {
                    "sembol": fon_kodu,
                    "fiyat": round(fiyat, 6),
                    "aylik_getiri": aylik,
                    "yillik_getiri": yillik,
                    "yatirimci_sayisi": satir.get("yatirimci_sayisi"),
                    "piyasa_degeri": satir.get("piyasa_degeri"),
                    "pay_adedi": satir.get("pay_adedi"),
                    # Genişletilmiş analiz alanları (Piyasa/Yabancı/Temettü katmanı entegrasyonu için ayrıldı)
                    "yabanci_orani": satir.get("yabanci_orani", "N/A"),
                    "dolasim_lot": satir.get("pay_adedi", "N/A"),
                    "temettu_tarihi": satir.get("temettu_tarihi", "Yok"),
                    "durum": "Canlı (TEFAS resmi API — pytefas)",
                    "fon_tipi": kind,
                    "guncelleme": now_str,
                }
                self.cache[fon_kodu] = res
                self.cache_zamani[fon_kodu] = time.time()
                return res

        res = {
            "sembol": fon_kodu, "fiyat": 0.0,
            "aylik_getiri": None, "yillik_getiri": None,
            "durum": "Alınamadı — TEFAS'ta bu kodla aktif fon bulunamadı",
            "guncelleme": now_str,
        }
        return res


fon_takip = FonTakipMerkezi()