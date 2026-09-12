class AnalizMotoru:
    def sinyal_ve_plan_uret(self, varlik: dict, guncel_fiyat: float) -> dict:
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

        # Dinamik Fiyat Seviyeleri Hesabı
        stop_seviyesi = round(maliyet * 0.90, 2)
        hedef_1 = round(guncel_fiyat * 1.05, 2)
        hedef_2 = round(guncel_fiyat * 1.12, 2)

        # Karar ve Açıklama Üretimi
        if kz_orani <= -15.0:
            karar = "DİKKAT / STOP-LOSS"
            guven = 92
            kademe_adet = max(1, int(adet * 0.5))
            aciklama = (
                f"Pozisyonda %{abs(kz_orani)} oranında derin kayıp var. Kritik stop seviyesi: ₺{stop_seviyesi}. "
                f"Riski sınırlamak için en az {kademe_adet} adet zararına satış değerlendirilebilir veya maliyet düşürmek için taban aranmalı."
            )
        elif -15.0 < kz_orani <= -5.0:
            karar = "STOP-LOSS / İZLE"
            guven = 85
            aciklama = (
                f"Pozisyon %{abs(kz_orani)} ekside. Fiyat maliyetin altına sarktı. "
                f"₺{stop_seviyesi} seviyesinin altında günlük kapanış gelirse pozisyonu kapatın. Yeni ekleme yapmayın."
            )
        elif -5.0 < kz_orani < 15.0:
            karar = "TUT / POZİSYON KORU"
            guven = 88
            aciklama = (
                f"Kâr/Zarar nötr bantta (%{kz_orani}). Trend stabilitesini koruyor. "
                f"İlk kâr hedefi ₺{hedef_1} olarak izlenmeli. Stop noktanız ₺{stop_seviyesi} seviyesinde tutulmalıdır."
            )
        elif 15.0 <= kz_orani < 50.0:
            karar = "KADEMELİ SAT (KÂR AL)"
            guven = 90
            satilacak = max(1, int(adet * 0.33))
            aciklama = (
                f"Güçlü getiri: +%{kz_orani} kazançtasınız. Kârı realize etmek için {satilacak} adet ₺{hedef_1} seviyesinde, "
                f"kalanlar ₺{hedef_2} seviyesinde kademeli satılabilir."
            )
        else:
            karar = "GÜÇLÜ KÂR SATIŞI"
            guven = 95
            satilacak = max(1, int(adet * 0.50))
            aciklama = (
                f"Yüksek kâr: +%{kz_orani} (+₺{kar_zarar_tl:,.2f}). Ana sermayeyi korumak için en az {satilacak} adet "
                f"satılarak kâr nakde dönüştürülmelidir."
            )

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
            "analiz_notu": aciklama
        }

analiz_motoru = AnalizMotoru()