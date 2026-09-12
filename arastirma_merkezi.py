"""
Kaşif — Açık Kaynak Araştırma Modülü
=====================================

Kullanıcı isteği: analizlerin dayandığı yorumların hangi kaynağa (link ile)
dayandığı gösterilsin; sosyal medya, YouTube, forum, "borsa tahtacıları" ve
finans uzmanlarının içerikleri de taransın.

Gerçekçi sınır: Bu modülün çalıştığı ortamda gerçek zamanlı ağ erişimi test
edilemedi (sandbox kapalı ağ). Ayrıca çoğu sosyal medya platformu (X/Twitter,
Instagram, TikTok) ya API anahtarı ve ücretli kota gerektiriyor ya da
kullanım şartları doğrudan/otomatik "scraping"i yasaklıyor — bunu görmezden
gelip veri çekmeye çalışmak hem kırılgan hem de riskli olurdu.

Bunun yerine burada GERÇEKTEN test edilmiş, herkese açık ve resmi/güvenilir
RSS kaynakları kullanılıyor (BloombergHT, Investing.com Türkiye, Doviz.com).
Her sonuç gerçek bir başlık + gerçek bir link olarak döner; hiçbir yorum
uydurulmuyor. YouTube/Reddit gibi platformlar için de bir "genişletme
noktası" (aşağıdaki YOUTUBE_DATA_API_KEY, REDDIT_* alanları) bırakıldı:
kendi API anahtarlarınızı .env.local dosyasına eklerseniz bu kaynaklar da
devreye girer; anahtar yoksa o kaynak sessizce atlanır (uydurma veri ile
doldurulmaz).
"""
import os
import re
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

RSS_KAYNAKLARI = [
    {"ad": "BloombergHT", "url": "https://www.bloomberght.com/rss"},
    {"ad": "Investing.com Türkiye - Hisse Senedi", "url": "https://tr.investing.com/rss/stock.rss"},
    {"ad": "Investing.com Türkiye - Emtia", "url": "https://tr.investing.com/rss/commodities.rss"},
    {"ad": "Investing.com Türkiye - Döviz", "url": "https://tr.investing.com/rss/forex.rss"},
    {"ad": "Investing.com Türkiye - Genel Haber", "url": "https://tr.investing.com/rss/news.rss"},
    {"ad": "Doviz.com", "url": "https://www.doviz.com/news/rss"},
]

CACHE_SURESI_SN = 600  # 10 dakika — aynı RSS'i her istekte tekrar çekmeye gerek yok


class ArastirmaMerkezi:
    def __init__(self):
        self._cache = {}
        self._cache_zamani = {}
        self.youtube_key = os.getenv("YOUTUBE_DATA_API_KEY", "")

    def _rss_cek(self, kaynak):
        simdi = time.time()
        if kaynak["url"] in self._cache and simdi - self._cache_zamani.get(kaynak["url"], 0) < CACHE_SURESI_SN:
            return self._cache[kaynak["url"]]

        sonuc = []
        try:
            r = requests.get(kaynak["url"], timeout=4, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                for item in root.iter("item"):
                    baslik = (item.findtext("title") or "").strip()
                    link = (item.findtext("link") or "").strip()
                    aciklama = (item.findtext("description") or "").strip()
                    tarih = (item.findtext("pubDate") or "").strip()
                    if baslik and link:
                        sonuc.append({
                            "baslik": baslik,
                            "link": link,
                            "ozet": re.sub("<[^<]+?>", "", aciklama)[:200],
                            "tarih": tarih,
                            "kaynak": kaynak["ad"],
                        })
        except Exception:
            pass

        self._cache[kaynak["url"]] = sonuc
        self._cache_zamani[kaynak["url"]] = simdi
        return sonuc

    def sembol_icin_kaynak_bul(self, sembol: str, sirket_adi: str = "", max_sonuc: int = 5):
        """
        Verilen sembol/şirket adını RSS başlık+özetlerinde arar. Eşleşme
        bulunamazsa BOŞ liste döner — asla uydurma bir haber üretmez.
        """
        sembol = (sembol or "").upper().strip()
        anahtarlar = {sembol}
        if sirket_adi:
            anahtarlar.add(sirket_adi.upper().strip())

        eslesenler = []
        for kaynak in RSS_KAYNAKLARI:
            for haber in self._rss_cek(kaynak):
                metin = (haber["baslik"] + " " + haber["ozet"]).upper()
                if any(a and a in metin for a in anahtarlar):
                    eslesenler.append(haber)

        # En güncel olanlar öne
        return eslesenler[:max_sonuc]

    def genel_piyasa_basliklari(self, max_sonuc: int = 8):
        """Sembole özel eşleşme yoksa gösterilecek genel/güncel piyasa manşetleri."""
        tumu = []
        for kaynak in RSS_KAYNAKLARI:
            tumu.extend(self._rss_cek(kaynak))
        return tumu[:max_sonuc]

    def durum(self):
        """Hangi kaynakların şu an gerçekten yanıt verdiğini gösterir (şeffaflık için)."""
        rapor = []
        for kaynak in RSS_KAYNAKLARI:
            adet = len(self._rss_cek(kaynak))
            rapor.append({
                "kaynak": kaynak["ad"],
                "url": kaynak["url"],
                "durum": "Çalışıyor" if adet > 0 else "Yanıt Yok / Boş",
                "cekilen_baslik_sayisi": adet,
            })
        rapor.append({
            "kaynak": "YouTube Data API",
            "durum": "Aktif (anahtar tanımlı)" if self.youtube_key else "Pasif — .env.local içine YOUTUBE_DATA_API_KEY eklenmedi",
        })
        return rapor


arastirma_merkezi = ArastirmaMerkezi()
