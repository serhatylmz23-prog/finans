import numpy as np

class AnalizVeStratejiMotoru:
    """
    Kasa verileri ile canlı fiyatları kıyaslayıp
    Kademeli Al/Sat, Stop-Loss ve Trend tavsiyeleri üretir.
    """
    def rsi_hesapla(self, prices, period=14):
        if len(prices) < period + 1:
            return 50.0
        deltas = np.diff(prices)
        seed = deltas[:period]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        rs = up / down if down != 0 else 0
        rsi = np.zeros_like(prices)
        rsi[:period] = 100. - 100. / (1. + rs)
        return float(rsi[-1])

    def _adet_formatla(self, adet):
        try:
            if float(adet).is_integer():
                return str(int(adet))
            return f"{adet:.2f}".rstrip("0").rstrip(".")
        except Exception:
            return str(adet)

    def sinyal_ve_plan_uret(self, varlik, canli_fiyat):
        maliyet = varlik.get("maliyet", 0.0)
        adet = varlik.get("adet", 1.0)
        kar_zarar_yuzde = ((canli_fiyat - maliyet) / maliyet * 100) if maliyet > 0 else 0.0

        # Karar matrisi
        tavsiye = "TUT"
        aksiyon = "Mevcut pozisyonu koruyun."
        guven_endeksi = 85

        if maliyet <= 0:
            aksiyon = "Maliyet bilgisi bu ekrandan alınamadı, bu yüzden kâr/zarar % hesaplanamıyor. Tablo satırındaki kategori menüsünün yanına maliyeti elle girebilirsin."
            guven_endeksi = 50

        elif kar_zarar_yuzde >= 18.0 and canli_fiyat > 0 and adet > 0:
            tavsiye = "KADEMELİ SAT"
            tam_adet_mi = float(adet).is_integer()
            if tam_adet_mi:
                d1 = round(adet * 0.34)
                d2 = round(adet * 0.33)
                d3 = int(adet) - d1 - d2
            else:
                d1 = round(adet * 0.34, 2)
                d2 = round(adet * 0.33, 2)
                d3 = round(adet - d1 - d2, 2)
            f1 = canli_fiyat
            f2 = round(canli_fiyat * 1.03, 2)
            f3 = round(canli_fiyat * 1.06, 2)
            aksiyon = (
                f"Örnek (kesin tavsiye değil) kademeli satış planı: "
                f"{self._adet_formatla(d1)} adet ≈₺{f1:.2f}'den şimdi, "
                f"{self._adet_formatla(d2)} adet ≈₺{f2:.2f}'ye ulaşırsa (mevcut fiyatın %3 üstü), "
                f"{self._adet_formatla(d3)} adet ≈₺{f3:.2f}'ye ulaşırsa (mevcut fiyatın %6 üstü) satılabilir."
            )
            guven_endeksi = 92

        elif kar_zarar_yuzde <= -8.0 and maliyet > 0:
            tavsiye = "DİKKAT / STOP-LOSS"
            stop_fiyat = round(maliyet * 0.90, 2)
            ort_dusurme_adet = max(round(adet * 0.25), 1) if adet > 0 else 0
            aksiyon = (
                f"Zarar %{abs(kar_zarar_yuzde):.1f}. Örnek stop seviyesi ≈₺{stop_fiyat:.2f} "
                f"(maliyetin %10 altı) — fiyat bu seviyeye inerse pozisyonu kapatmayı düşünebilirsin. "
                f"Alternatif: ortalama maliyeti düşürmek için ≈{ort_dusurme_adet} adet daha eklemeyi değerlendirebilirsin."
            )
            guven_endeksi = 88

        elif kar_zarar_yuzde > 0 and kar_zarar_yuzde < 10.0:
            tavsiye = "TREND YUKARI - KORU"
            aksiyon = "Yükseliş trendi sürüyor, hedeflere kadar taşımaya devam edebilirsin."
            guven_endeksi = 80

        return {
            "sembol": varlik["sembol"],
            "adet": adet,
            "maliyet": maliyet,
            "canli_fiyat": canli_fiyat,
            "kar_zarar_yuzde": round(kar_zarar_yuzde, 2),
            "toplam_deger": round(adet * canli_fiyat, 2),
            "tavsiye": tavsiye,
            "aksiyon_plani": aksiyon,
            "guven_endeksi": guven_endeksi
        }

analiz_motoru = AnalizVeStratejiMotoru()