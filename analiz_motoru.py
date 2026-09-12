class AnalizMotoru:
    """
    Portföydeki her varlık için sinyal/plan üretir.

    Önemli ilke: Bu motor hiçbir zaman kendi başına emir vermez, yalnızca
    şeffaf ve kaynağı belli olan bir değerlendirme sunar. "Kesin kazanç"
    ya da "garanti" ifadesi kullanılmaz; güven skoru veri kalitesine göre
    değişir, sabit bir rakam değildir.
    """

    def _guven_hesapla(self, veri_kaynagi_guveni: float, veri_tam_mi: bool, hareketsiz_mi: bool) -> int:
        """
        Güven skorunu, önceki sürümde olduğu gibi karar dalına göre sabit
        basmak yerine gerçek veri kalitesinden türetir:
        - Fiyat canlı bir kaynaktan mı geldi yoksa yedek/referans mı?
        - Aylık/yıllık getiri gerçekten hesaplanabildi mi yoksa "-" mi?
        - Hareketsizlik/likidite şüphesi var mı (daha düşük güven)?
        """
        guven = veri_kaynagi_guveni  # 0-100, kaynağın kendi güven puanı (örn. "BIST Canlı" = 95, "Yedek Referans" = 80)
        if not veri_tam_mi:
            guven -= 15  # getiri verisi eksikse kararın gerekçesi de eksik demektir
        if hareketsiz_mi:
            guven -= 10  # şüpheli/donuk fiyat hareketi güveni düşürür, artırmaz
        guven = max(40, min(99, round(guven)))
        return int(guven)

    def sinyal_ve_plan_uret(
        self,
        varlik: dict,
        guncel_fiyat: float,
        aylik_getiri=0.0,
        yillik_getiri=0.0,
        veri_kaynagi: str = "Bilinmiyor",
        veri_kaynagi_guveni: float = 70.0,
        kaynak_linkleri: list = None,
    ) -> dict:
        sembol = str(varlik.get("sembol", "")).upper().strip()
        maliyet = float(varlik.get("maliyet", 0.0))
        adet = float(varlik.get("adet", 0.0))

        guncel_fiyat = float(guncel_fiyat) if guncel_fiyat and guncel_fiyat > 0 else maliyet
        toplam_tutar = round(adet * guncel_fiyat, 2)
        toplam_maliyet = round(adet * maliyet, 2)
        kar_zarar_tl = round(toplam_tutar - toplam_maliyet, 2)

        kz_orani = 0.0
        if maliyet > 0:
            kz_orani = round(((guncel_fiyat - maliyet) / maliyet) * 100, 2)

        # Getiri verisi gerçekten var mı, yoksa "-" placeholder mı?
        veri_tam_mi = True
        aylik_val, yillik_val = 0.0, 0.0
        try:
            if aylik_getiri in (None, "-", "") or yillik_getiri in (None, "-", ""):
                veri_tam_mi = False
            else:
                aylik_val = abs(float(str(aylik_getiri).replace("%", "").replace(",", ".")))
                yillik_val = abs(float(str(yillik_getiri).replace("%", "").replace(",", ".")))
        except Exception:
            veri_tam_mi = False

        # Hareketsizlik/olası likidite sorunu: SADECE gerçek getiri verisine
        # dayanır. Önceki sürümde belirli semboller (UMPAS, DARDL, BRKO,
        # MEMS1 vb.) koda gömülü sabit bir "kesin kısıtlı" listesiydi; bu
        # hem güncelliğini yitirebilir hem de o sembolü tutan herkes için
        # gerçek durumdan bağımsız hep aynı (yanlış olabilecek) yorumu
        # üretirdi. Artık böyle bir sabit liste yok; tespit tamamen o anki
        # veriye dayanıyor ve "kesin" değil "olası" olarak sunuluyor.
        hareketsiz_mi = veri_tam_mi and (aylik_val < 0.25 and yillik_val < 0.6)

        guven = self._guven_hesapla(veri_kaynagi_guveni, veri_tam_mi, hareketsiz_mi)

        aciklamalar = []
        guven_gerekce = []
        if veri_kaynagi_guveni < 85:
            guven_gerekce.append(f"fiyat kaynağı '{veri_kaynagi}' (yedek/referans olabilir)")
        if not veri_tam_mi:
            guven_gerekce.append("aylık/yıllık getiri verisi eksik")
        if hareketsiz_mi:
            guven_gerekce.append("fiyat hareketi anormal derecede durgun görünüyor")

        # 1. Olası Fiyat Durgunluğu (SADECE bir sezgi/varsayımdır — KAP/BIST'e
        # bağlı bir kontrol DEĞİLDİR. Önceki sürümde bu durum yanıltıcı
        # biçimde "İŞLEM KISITI" olarak sunuluyordu; bu, gerçekten KAP'a
        # bağlanıp doğrulanmış izlenimi veriyordu ama böyle bir bağlantı hiç
        # yoktu/yok. Artık bunu açıkça "veri durgun, KAP'ta doğrulanmadı"
        # olarak etiketliyoruz ve kullanıcıyı gerçek kaynağa yönlendiriyoruz.
        if hareketsiz_mi and kz_orani < 0:
            karar = "DİKKAT / FİYAT VERİSİ DURGUN (KAP'TA DOĞRULANMADI)"
            kap_link = f"https://www.kap.org.tr/tr/bildirim-sorgu?sirket={sembol}"
            aciklamalar.append(
                f"⚠️ <strong>Veri Uyarısı (varsayım, doğrulanmadı):</strong> {sembol} için son bir ay/yıl "
                "getiri verisi neredeyse hiç değişmemiş görünüyor. Bu bir işlem kısıtı (YİP/tahta kapalı) "
                "olabileceği gibi, sadece kullanılan veri kaynağının bu sembolü güncelleyememesinden de "
                "kaynaklanabilir. <u>Bu uygulama KAP veya BIST'e canlı bağlı değildir</u> — bu yalnızca "
                "fiyat hareketinden çıkarılan bir sezgidir, gerçek bir doğrulama değildir."
            )
            aciklamalar.append(
                f'🔗 <strong>Kendin doğrula:</strong> <a href="{kap_link}" target="_blank" rel="noopener">'
                "KAP bildirim arama sayfasını aç</a> ve orada bu sembolü ara (KAP'ın arama kutusunu "
                "otomatik doldurduğu garanti değildir, link sadece doğru sayfaya götürür)."
            )

        # 2. Derin Zarardaki Varlıklar İçin Matematiksel Maliyet Düşürme
        elif kz_orani <= -20.0:
            karar = "DİKKAT / STOP-LOSS DEĞERLENDİR"
            hedef_maliyet = round((maliyet + guncel_fiyat) / 2, 2)
            ek_adet = int(adet * 0.40)
            ek_tutar = round(ek_adet * guncel_fiyat, 2)

            aciklamalar.append(f"📉 <strong>Derin Kayıp:</strong> Pozisyon maliyetin %{abs(kz_orani):.2f} altında.")
            aciklamalar.append(
                f"🎯 <strong>Matematiksel Senaryo (tavsiye değil, hesaplama):</strong> Mevcut fiyattan (₺{guncel_fiyat:.2f}) "
                f"<strong>+{ek_adet} adet</strong> (≈₺{ek_tutar:,.2f}) eklenirse ortalama maliyet "
                f"<strong>₺{maliyet:.2f} ➔ ₺{hedef_maliyet:.2f}</strong> seviyesine iner. Bu, ek sermaye riskini artırır; "
                "yalnızca bir hesaplamadır, alım tavsiyesi değildir."
            )
            aciklamalar.append(f"🛑 <strong>Not:</strong> Fiyat ₺{(guncel_fiyat * 0.92):.2f} altına inerse kayıp derinleşir; risk toleransına göre değerlendirilmelidir.")

        # 3. Dengeli / Koruma Bandı
        elif -20.0 < kz_orani < 15.0:
            karar = "TUT / İZLEMEYE DEVAM"
            aciklamalar.append(f"📌 K/Z bandı dengeli aralıkta (%{kz_orani}).")
            aciklamalar.append(f"🎯 Referans seviyeler — olası kâr realizasyonu: ₺{(guncel_fiyat * 1.08):.2f} | olası stop: ₺{(maliyet * 0.92):.2f} (bunlar öneri değil, referans hesaplamalardır).")

        # 4. Yüksek Kâr Bölgesi
        else:
            karar = "KADEMELİ KÂR REALİZASYONU DEĞERLENDİR"
            sat_adet = max(1, int(adet * 0.35))
            aciklamalar.append(f"🚀 <strong>Güçlü Kâr Bölgesi:</strong> +%{kz_orani} (+₺{kar_zarar_tl:,.2f}).")
            aciklamalar.append(f"1. Olası kademe: {sat_adet} adet ₺{(guncel_fiyat * 1.05):.2f} seviyesinde nakde dönüştürme senaryosu (karar sana ait).")

        if guven_gerekce:
            aciklamalar.append("🔎 <strong>Güven skoru neden bu seviyede:</strong> " + "; ".join(guven_gerekce) + ".")

        if kaynak_linkleri:
            kaynak_html = " ".join(
                f'<a href="{k.get("link","#")}" target="_blank" rel="noopener">🔗 {k.get("baslik","kaynak")} ({k.get("kaynak","")})</a>'
                for k in kaynak_linkleri[:3]
            )
            aciklamalar.append("📰 <strong>İlgili açık kaynak haberler:</strong><br>" + kaynak_html)

        return {
            "sembol": sembol,
            "adet": adet,
            "birim_maliyet": maliyet,
            "maliyet": maliyet,  # geriye dönük uyumluluk için korunuyor
            "toplam_maliyet": toplam_maliyet,
            "canli_fiyat": guncel_fiyat,
            "fiyat": guncel_fiyat,
            "toplam_tutar": toplam_tutar,
            "toplam_deger": toplam_tutar,
            "kar_zarar_orani": kz_orani,
            "kar_zarar_tl": kar_zarar_tl,
            "ajan_karari": karar,
            "guven_skoru": guven,
            "veri_kaynagi": veri_kaynagi,
            "analiz_notu": "<br><br>".join(aciklamalar),
        }


analiz_motoru = AnalizMotoru()
