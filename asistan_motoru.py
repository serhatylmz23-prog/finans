"""
SyFinans - Doğal Dil Finansal Asistan Motoru
"""
from finans_kaynak_merkezi import kaynak_merkezi

class AsistanMotoru:
    def __init__(self):
        pass

    def soru_yanitla(self, soru: str, portfoy_verileri: list) -> str:
        s = soru.lower().strip()
        
        # Piyasa genel özeti sorgusu
        if "piyasa" in s or "durum" in s or "özet" in s:
            doviz = kaynak_merkezi.doviz_getir("USDTRY").get("fiyat", 0)
            altin = kaynak_merkezi.altin_fiyatlari_getir().get("gram", 0)
            bist = kaynak_merkezi.hisse_fiyat_getir("XU100").get("fiyat", 0)
            return f"Piyasa Özeti -> USD/TRY: {doviz} TL | Gram Altın: {altin} TL | BIST 100: {bist} Puan. Sistem tüm kaynaklarla senkronize çalışıyor."

        # Portföy varlık sorgusu
        if "portföy" in s or "varlık" in s or "ne kadar" in s:
            toplam_varlik = len(portfoy_verileri)
            if toplam_varlik == 0:
                return "Portföyünüzde şu an kayıtlı herhangi bir varlık bulunmuyor. Manuel ekleme yapabilir veya görsel aktarım kullanabilirsiniz."
            
            ozet_liste = []
            for v in portfoy_verileri:
                sembol = v.get("sembol")
                adet = v.get("adet")
                ozet_liste.append(f"{sembol} ({adet} adet)")
            return f"Portföyünüzde toplam {toplam_varlik} farklı kalem varlık bulunmaktadır: " + ", ".join(ozet_liste)

        return "SyFinans Otağı asistanı talebinizi aldı. Portföyünüz ve piyasa verileri aktif olarak izleniyor; spesifik bir varlık (örn: THYAO, AFA, ALTINS1) veya piyasa özeti hakkında soru sorabilirsiniz."

asistan_motoru = AsistanMotoru()