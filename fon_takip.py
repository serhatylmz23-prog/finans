"""
Fon Takip Merkezi
=================

ÖNEMLİ GEÇMİŞ NOT: TEFAS sitesi 2026 Nisan'ında baştan yeniden yazıldı;
yıllarca kullanılan eski `/api/DB/BindHistoryInfo`, `BindHistoryAllocations`
ve `BindFundInfo` uç noktaları KALICI OLARAK KAPATILDI. Önceki sürümdeki kod
tam olarak bu üç ölü uç noktayı deniyordu — bu yüzden neredeyse hiçbir zaman
gerçek veri gelmiyor, sessizce "maliyet = fiyat" yedeğine düşülüyordu (K/Z
her zaman %0 görünüyordu). Bu, kullanıcı tarafından fark edilen "fon
değerleri sahte, hâlâ alım fiyatı üzerinden değerlendiriliyor" hatasının
kök nedeniydi.

Bu sürüm, TEFAS'ın yeni (Next.js tabanlı) sitesinin kullandığı GERÇEKTEN
ÇALIŞAN resmi uç noktalarına erişen `pytefas` paketini kullanıyor
(kimlik/API anahtarı gerektirmiyor, haftalık otomatik "canary" testiyle
TEFAS'ın kendisine karşı doğrulanıyor). Not: `tefasmak` adlı alternatif bir
paket de bulundu ama o, TEFAS'ın bot-koruması (Akamai) koyduğu eski uç
noktayı TARAYICI TAKLİDİ YAPARAK aşmaya çalışıyor — bu, bir kurumun
kasıtlı olarak koyduğu erişim engelini atlatmak anlamına geldiği için
BİLEREK KULLANILMADI. `pytefas` ise sitenin zaten herkese açık, kimlik
gerektirmeyen YENİ ve GEÇERLİ uç noktalarını kullanıyor; bir engeli aşmaya
çalışmıyor.

`pytefas` kurulu değilse (henüz `pip install -r requirements.txt`
çalıştırılmadıysa) bu modül GERÇEK OLMAYAN bir fiyat üretmez; "Alınamadı"
durumunu döner ve çağıran taraf (main.py + analiz_motoru.py) bunu düşük
güven skoru ile işaretler.
"""
import time
from datetime import datetime, timedelta

CACHE_SURESI_SN = 300       # anlık fiyat önbelleği: 5 dakika
GUNLUK_SNAPSHOT_TTL_SN = 6 * 3600  # geçmiş gün verisi değişmez, 6 saat yeterli

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
        ilk veri bulunan iş gününün {fon_kodu: fiyat} sözlüğünü döner.
        TEFAS geçmiş bir gün için veri vermiyorsa (tatil/veri yok) bir önceki
        güne kayar. En fazla `deneme_hakki` gün geriye gidilir.
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
                    df = self._crawler.fetch(anahtar[0], columns="info", kind=kind)
                    sozluk = {}
                    if df is not None and len(df) > 0:
                        for _, satir in df.iterrows():
                            kod = satir.get("fund_code")
                            fiyat = satir.get("price")
                            if kod and fiyat and float(fiyat) > 0:
                                sozluk[str(kod).upper().strip()] = float(fiyat)
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
                "durum": "Alınamadı — 'pytefas' paketi kurulu değil (requirements.txt'e eklendi, "
                         "'pip install -r requirements.txt' çalıştırılmalı)",
                "guncelleme": now_str,
            }
            return res

        bugun = datetime.now()
        # Fon tipleri sırayla denenir: çoğu elde bulunan fon YAT (yatırım fonu)
        for kind in ("YAT", "EMK", "BYF", "GYF", "GSYF"):
            bugun_verisi = self._is_gunu_snapshot(bugun, kind)
            if fon_kodu in bugun_verisi:
                fiyat = bugun_verisi[fon_kodu]

                bir_ay_once = self._is_gunu_snapshot(bugun - timedelta(days=30), kind)
                bir_yil_once = self._is_gunu_snapshot(bugun - timedelta(days=365), kind)

                aylik = None
                yillik = None
                if fon_kodu in bir_ay_once and bir_ay_once[fon_kodu] > 0:
                    aylik = round(((fiyat - bir_ay_once[fon_kodu]) / bir_ay_once[fon_kodu]) * 100, 2)
                if fon_kodu in bir_yil_once and bir_yil_once[fon_kodu] > 0:
                    yillik = round(((fiyat - bir_yil_once[fon_kodu]) / bir_yil_once[fon_kodu]) * 100, 2)

                res = {
                    "sembol": fon_kodu,
                    "fiyat": round(fiyat, 6),
                    "aylik_getiri": aylik,    # None ise: gerçek 1 ay önceki veri bulunamadı, UYDURULMAZ
                    "yillik_getiri": yillik,  # None ise: gerçek 1 yıl önceki veri bulunamadı, UYDURULMAZ
                    "durum": "Canlı (TEFAS resmi API — pytefas)",
                    "fon_tipi": kind,
                    "guncelleme": now_str,
                }
                self.cache[fon_kodu] = res
                self.cache_zamani[fon_kodu] = time.time()
                return res

        # Hiçbir fon tipinde bulunamadı: fon kapanmış/kodu yanlış olabilir.
        res = {
            "sembol": fon_kodu, "fiyat": 0.0,
            "aylik_getiri": None, "yillik_getiri": None,
            "durum": "Alınamadı — TEFAS'ta bu kodla aktif fon bulunamadı",
            "guncelleme": now_str,
        }
        return res


fon_takip = FonTakipMerkezi()
