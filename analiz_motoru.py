class AnalizMotoru:
    def sinyal_ve_plan_uret(self, varlik: dict, guncel_fiyat: float, aylik_getiri=0.0, yillik_getiri=0.0) -> dict:
        sembol = str(varlik.get("sembol", "")).upper().strip()
        maliyet = float(varlik.get("maliyet", 0.0))
        adet = float(varlik.get("adet", 0.0))
        
        guncel_fiyat = float(guncel_fiyat) if guncel_fiyat > 0 else maliyet
        toplam_tutar = round(adet * guncel_fiyat, 2)
        toplam_maliyet = round(adet * maliyet, 2)
        kar_zarar_tl = round(toplam_tutar - toplam_maliyet, 2)
        
        kz_orani = 0.0
        if maliyet > 0:
            kz_orani = round(((guncel_fiyat - maliyet) / maliyet) * 100, 2)

        aciklamalar = []

        # 1. İşlem Kısıtı / Likidite Donması / Yakın İzleme Pazarı Tespiti
        # UMPAS gibi tahtası kapalı veya getirisi donmuş hisselerin dinamik yakalanması
        try:
            aylik_val = abs(float(str(aylik_getiri).replace("%", "").replace(",", ".") or 0))
            yillik_val = abs(float(str(yillik_getiri).replace("%", "").replace(",", ".") or 0))
        except Exception:
            aylik_val, yillik_val = 1.0, 1.0

        hareketsiz_mi = (aylik_val < 0.25 and yillik_val < 0.6)
        ozel_tedbir_hisseleri = ["UMPAS", "DARDL", "BRKO", "MEMS1"]

        if sembol in ozel_tedbir_hisseleri or (hareketsiz_mi and kz_orani < 0):
            karar = "DİKKAT / İŞLEM KISITI"
            guven = 95
            aciklamalar.append(f"⛔ <strong>Piyasa Uyarısı:</strong> {sembol} payında likidite/işlem kısıtı veya Yakın İzleme Pazarı (YİP) tedbiri tespit edilmiştir.")
            aciklamalar.append("⚠️ <strong>Kısıtlama:</strong> Serbest fiyat oluşumu engelli. Tek fiyat emir toplama, brüt takas veya açığa satış/kredili işlem yasağı kapsamındadır.")
            aciklamalar.append("💡 <strong>Ajan Görüşü:</strong> Payda kesinlikle yeni maliyet düşürme alımı yapılmamalıdır. Eşleşme sağlandığında öncelikli portföy tahliyesi ve likidite çıkışı hedeflenmelidir.")

        # 2. Derin Zarardaki Hisseler İçin Matematiksel Maliyet Düşürme
        elif kz_orani <= -20.0:
            karar = "DİKKAT / STOP-LOSS"
            guven = 91
            hedef_maliyet = round((maliyet + guncel_fiyat) / 2, 2)
            ek_adet = int(adet * 0.40)
            ek_tutar = round(ek_adet * guncel_fiyat, 2)

            aciklamalar.append(f"📉 <strong>Derin Kayıp:</strong> Pozisyon maliyetin %{abs(kz_orani)} altında bulunuyor.")
            aciklamalar.append(
                f"🎯 <strong>Kademeli Müdahale:</strong> Fiyatı ortalamak için mevcut fiyattan (₺{guncel_fiyat:.2f}) "
                f"<strong>+{ek_adet} adet</strong> (₺{ek_tutar:,.2f}) ilave edilirse maliyet doğrudan <strong>₺{maliyet:.2f} ➔ ₺{hedef_maliyet:.2f}</strong> seviyesine çekilebilir."
            )
            aciklamalar.append(f"🛑 <strong>Kritik Stop:</strong> Fiyat ₺{(guncel_fiyat * 0.92):.2f} altını görürse daha fazla kayıp yaşamamak adına pozisyon kapatılmalıdır.")

        # 3. Dengeli / Koruma Bandı
        elif -20.0 < kz_orani < 15.0:
            karar = "TUT / İZLE"
            guven = 86
            aciklamalar.append(f"📌 K/Z bandı dengeli bantta (%{kz_orani}). Trend desteği takip ediliyor.")
            aciklamalar.append(f"🎯 Kâr Realizasyon Seviyesi: ₺{(guncel_fiyat * 1.08):.2f} | Stop Seviyesi: ₺{(maliyet * 0.92):.2f}.")

        # 4. Yüksek Kâr Realizasyonu
        else:
            karar = "KADEMELİ KÂR AL"
            guven = 94
            sat_adet = max(1, int(adet * 0.35))
            aciklamalar.append(f"🚀 <strong>Güçlü Kâr:</strong> +%{kz_orani} (+₺{kar_zarar_tl:,.2f}). Kârı koruma planı:")
            aciklamalar.append(f"1. Kademe: {sat_adet} adet ₺{(guncel_fiyat * 1.05):.2f} seviyesinde nakde dönüştürülmeli.")

        return {
            "sembol": sembol,
            "adet": adet,
            "maliyet": maliyet,
            "canli_fiyat": guncel_fiyat,
            "fiyat": guncel_fiyat,
            "toplam_tutar": toplam_tutar,
            "toplam_deger": toplam_tutar,
            "kar_zarar_orani": kz_orani,
            "kar_zarar_tl": kar_zarar_tl,
            "ajan_karari": karar,
            "guven_skoru": guven,
            "analiz_notu": "<br><br>".join(aciklamalar)
        }

analiz_motoru = AnalizMotoru()