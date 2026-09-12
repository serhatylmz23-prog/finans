from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import uuid
import time
import requests

from finans_kaynak_merkezi import kaynak_merkezi
from goruntu_isleyici import goruntu_ajani
from analiz_motoru import analiz_motoru
from fon_takip import fon_takip
from arastirma_merkezi import arastirma_merkezi

app = FastAPI(title="SyFinansOtağı")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PWA'nın (kurulabilir uygulamanın) çalışması için ikonlar ve manifest.json
# gerçekten servis edilmeli. Önceden hiçbir route/mount bu dosyalara
# bakmıyordu; index.html <link rel="manifest"> eklese bile 404 alıyordu.
if os.path.exists("icons"):
    app.mount("/icons", StaticFiles(directory="icons"), name="icons")


@app.get("/manifest.json")
def get_manifest():
    if os.path.exists("manifest.json"):
        return FileResponse("manifest.json", media_type="application/manifest+json")
    return HTMLResponse("", status_code=404)

KASA_DOSYASI = "kasa_verileri.json"

CACHE_PIYASA = {
    "son_guncelleme": 0,
    "veri": {
        "doviz": {"sembol": "USDTRY", "fiyat": 48.55, "kaynak": "Piyasa Kuru", "guncelleme": "Canlı"},
        "altin": {"gram": 6815.93, "ceyrek": 11109.97, "kaynak": "Spot Ons", "guncelleme": "Canlı"},
        "bist": {"sembol": "XU100", "fiyat": 14467.3, "kaynak": "BIST"},
        "gumus": {"gram": 89.50, "kaynak": "Spot Ons"}
    }
}

def varlik_turu_belirle(sembol: str) -> str:
    s = sembol.upper().strip()
    if any(k in s for k in ["USD", "EUR", "GBP", "DOVIZ", "DÖVİZ"]):
        return "Dövizlerim"
    if any(k in s for k in ["ALTIN", "CEYREK", "ÇEYREK", "GUMUS", "GÜMÜŞ", "XAG", "XAU"]):
        return "Kıymetli madenlerim"
    if len(s) == 3 and not s.endswith("IS") and s not in ["XAG", "XAU"]:
        return "Fonlarım"
    return "Hisselerim"

def kasa_oku():
    if os.path.exists(KASA_DOSYASI):
        try:
            with open(KASA_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def kasa_kaydet(veriler):
    with open(KASA_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veriler, f, ensure_ascii=False, indent=2)

class SilmeIstegi(BaseModel):
    idler: List[str]

class ManuelVarlik(BaseModel):
    sembol: str
    adet: float
    maliyet: float
    tur: Optional[str] = None

@app.get("/api/piyasa/ozet")
def get_piyasa():
    now = time.time()
    if now - CACHE_PIYASA["son_guncelleme"] > 5:
        try:
            doviz = kaynak_merkezi.doviz_getir("USDTRY")
            altin = kaynak_merkezi.altin_fiyatlari_getir()
            bist = kaynak_merkezi.hisse_fiyat_getir("XU100")
            
            if doviz.get("fiyat", 0) > 0:
                CACHE_PIYASA["veri"]["doviz"] = doviz
            if altin.get("gram", 0) > 0:
                CACHE_PIYASA["veri"]["altin"] = altin
            if bist.get("fiyat", 0) > 0:
                CACHE_PIYASA["veri"]["bist"] = bist
                
            CACHE_PIYASA["son_guncelleme"] = now
        except Exception:
            pass
    return CACHE_PIYASA["veri"]

@app.post("/api/kasa/manuel-ekle")
def manuel_ekle(v: ManuelVarlik):
    kasa = kasa_oku()
    sembol_temiz = v.sembol.upper().strip()
    yeni = {
        "id": str(uuid.uuid4())[:8],
        "sembol": sembol_temiz,
        "adet": v.adet,
        "maliyet": v.maliyet,
        "tur": v.tur if v.tur else varlik_turu_belirle(sembol_temiz)
    }
    kasa.append(yeni)
    kasa_kaydet(kasa)
    return {"durum": "Eklendi", "varlik": yeni}

@app.get("/api/kasa/analiz")
def get_kasa_analiz(
    kategori: Optional[str] = Query(None),
    sirala: Optional[str] = Query(None),
    yon: Optional[str] = Query("desc")
):
    kasa = kasa_oku()
    sonuc = []
    piyasa = get_piyasa()
    doviz_fiyat = float(piyasa["doviz"].get("fiyat", 48.55))
    altin_gram = float(piyasa["altin"].get("gram", 6815.93))
    altin_ceyrek = float(piyasa["altin"].get("ceyrek", 11109.97))
    gumus_gram = 89.50

    for varlik in kasa:
        sembol = str(varlik.get("sembol", "")).upper().strip()
        tur = varlik.get("tur") or varlik_turu_belirle(sembol)
        varlik["tur"] = tur

        if kategori and kategori not in ["Tümü", "Tumu", ""]:
            if kategori.lower() != tur.lower():
                continue

        # Not: Aşağıda hiçbir yerde sabit/uydurma bir aylık-yıllık getiri
        # yüzdesi YOK. Getiri gerçekten hesaplanamıyorsa "-" (veri yok)
        # olarak kalır; analiz_motoru bunu "eksik veri" sayıp güven
        # skorunu buna göre düşürür. Böylece hem yanlış/sabit yorum
        # üretilmez hem de kullanıcı hangi verinin gerçek olmadığını görür.
        aylik_getiri = "-"
        yillik_getiri = "-"
        maliyet = float(varlik.get("maliyet", 0.0))
        fiyat = 0.0
        veri_kaynagi = "Bilinmiyor"
        veri_kaynagi_guveni = 60.0

        # 1. Darphane Altın Sertifikası (ALTIN.S1)
        if "ALTIN.S1" in sembol or "ALTINS1" in sembol or "S1" in sembol:
            try:
                veri = kaynak_merkezi.hisse_fiyat_getir("ALTINS1")
                fiyat = float(veri.get("fiyat", 0.0))
                veri_kaynagi = veri.get("kaynak", "Referans")
                veri_kaynagi_guveni = float(veri.get("guven", 80))
                if fiyat == 0:
                    fiyat = round(altin_gram / 100.0, 2)
            except Exception:
                fiyat = round(altin_gram / 100.0, 2)
            getiri = kaynak_merkezi.gercek_getiri_hesapla("GC=F")
            if getiri:
                aylik_getiri = f"%{getiri['aylik_getiri']}"
                yillik_getiri = f"%{getiri['yillik_getiri']}"

        # 2. Gümüş
        elif "XAG" in sembol or "GUMUS" in sembol or "GÜMÜŞ" in sembol:
            fiyat = gumus_gram
            veri_kaynagi = "Spot Ons (Gümüş)"
            veri_kaynagi_guveni = 85.0
            getiri = kaynak_merkezi.gercek_getiri_hesapla("SI=F")
            if getiri:
                aylik_getiri = f"%{getiri['aylik_getiri']}"
                yillik_getiri = f"%{getiri['yillik_getiri']}"

        # 3. Döviz
        elif "USD" in sembol:
            fiyat = doviz_fiyat
            veri_kaynagi = piyasa["doviz"].get("kaynak", "Piyasa Kuru")
            veri_kaynagi_guveni = float(piyasa["doviz"].get("guven", 90))
            getiri = kaynak_merkezi.gercek_getiri_hesapla("USDTRY=X")
            if getiri:
                aylik_getiri = f"%{getiri['aylik_getiri']}"
                yillik_getiri = f"%{getiri['yillik_getiri']}"

        # 4. Altın
        elif "CEYREK" in sembol or "ÇEYREK" in sembol:
            fiyat = altin_ceyrek
            veri_kaynagi = piyasa["altin"].get("kaynak", "Spot Ons")
            veri_kaynagi_guveni = float(piyasa["altin"].get("guven", 90))
            getiri = kaynak_merkezi.gercek_getiri_hesapla("GC=F")
            if getiri:
                aylik_getiri = f"%{getiri['aylik_getiri']}"
                yillik_getiri = f"%{getiri['yillik_getiri']}"
        elif "ALTIN" in sembol or "XAU" in sembol or "GRAM" in sembol:
            fiyat = altin_gram
            veri_kaynagi = piyasa["altin"].get("kaynak", "Spot Ons")
            veri_kaynagi_guveni = float(piyasa["altin"].get("guven", 90))
            getiri = kaynak_merkezi.gercek_getiri_hesapla("GC=F")
            if getiri:
                aylik_getiri = f"%{getiri['aylik_getiri']}"
                yillik_getiri = f"%{getiri['yillik_getiri']}"

        # 5. TEFAS Fonları
        elif len(sembol) == 3 and not sembol.endswith("IS") and sembol not in ["XAG", "XAU"]:
            try:
                fon_veri = fon_takip.fon_bilgisi_getir(sembol)
                cekilen_fiyat = float(fon_veri.get("fiyat", 0.0))
                if cekilen_fiyat > 0:
                    fiyat = cekilen_fiyat
                    veri_kaynagi = "TEFAS"
                    veri_kaynagi_guveni = 90.0
                    # TEFAS gerçekten aylık/yıllık getiri veriyorsa kullan;
                    # vermiyorsa (0.0 varsayılanı) "-" bırak, uydurma yapma.
                    if fon_veri.get("aylik_getiri") or fon_veri.get("yillik_getiri"):
                        aylik_getiri = f"%{fon_veri.get('aylik_getiri', 0.0)}"
                        yillik_getiri = f"%{fon_veri.get('yillik_getiri', 0.0)}"
                else:
                    fiyat = maliyet
                    veri_kaynagi = "TEFAS'a ulaşılamadı — son bilinen maliyet"
                    veri_kaynagi_guveni = 40.0
            except Exception:
                fiyat = maliyet
                veri_kaynagi_guveni = 40.0

        # 6. BIST Hisseleri (DARDL, THYAO, SASA vb.)
        else:
            try:
                hisse_veri = kaynak_merkezi.hisse_fiyat_getir(sembol)
                cekilen_fiyat = float(hisse_veri.get("fiyat", 0.0))
                fiyat = cekilen_fiyat if cekilen_fiyat > 0 else maliyet
                veri_kaynagi = hisse_veri.get("kaynak", "Bilinmiyor")
                veri_kaynagi_guveni = float(hisse_veri.get("guven", 60))

                # Gerçek 1 aylık / 1 yıllık getiri: kullanıcının maliyetinden
                # DEĞİL, hissenin kendi fiyat geçmişinden hesaplanıyor.
                getiri = kaynak_merkezi.gercek_getiri_hesapla(f"{sembol}.IS")
                if getiri:
                    aylik_getiri = f"%{getiri['aylik_getiri']}"
                    yillik_getiri = f"%{getiri['yillik_getiri']}"
            except Exception:
                fiyat = maliyet
                veri_kaynagi_guveni = 40.0

        if fiyat <= 0:
            fiyat = maliyet
            veri_kaynagi_guveni = min(veri_kaynagi_guveni, 45.0)

        # Kaşif: bu sembolle ilgili gerçek, kaynağı linkli açık kaynak haber var mı?
        try:
            kaynak_linkleri = arastirma_merkezi.sembol_icin_kaynak_bul(sembol)
        except Exception:
            kaynak_linkleri = []

        analiz = analiz_motoru.sinyal_ve_plan_uret(
            varlik, fiyat, aylik_getiri, yillik_getiri,
            veri_kaynagi=veri_kaynagi,
            veri_kaynagi_guveni=veri_kaynagi_guveni,
            kaynak_linkleri=kaynak_linkleri,
        )
        analiz["id"] = varlik.get("id", str(uuid.uuid4())[:8])
        analiz["tur"] = tur
        analiz["aylik_getiri"] = aylik_getiri
        analiz["yillik_getiri"] = yillik_getiri
        sonuc.append(analiz)

    # Sıralama: önceden bu parametreler kabul edilip hiç kullanılmıyordu
    # (API "çalışıyor" görünüyordu ama sirala= ne verilirse verilsin sonuç
    # değişmiyordu). Artık gerçekten uygulanıyor.
    if sirala:
        ters = (yon or "desc").lower() != "asc"
        def _anahtar(x):
            deger = x.get(sirala)
            return deger if isinstance(deger, (int, float)) else 0
        try:
            sonuc.sort(key=_anahtar, reverse=ters)
        except Exception:
            pass

    return {"kasa_analizi": sonuc}


@app.get("/api/piyasa/durum")
def get_piyasa_durum():
    """Panelde daha önce hep sabit '%100 Çalışıyor' gösteren yanıltıcı
    durum yerine, kaynakların gerçekten test edilmiş halini döner."""
    return {
        "veri_kaynaklari": kaynak_merkezi.durum_raporu(),
        "acik_kaynak_arastirma": arastirma_merkezi.durum(),
    }


@app.get("/api/kasa/arastir/{sembol}")
def get_sembol_arastirma(sembol: str):
    """Belirli bir sembol için Kaşif'in bulduğu gerçek, linkli haberler."""
    sonuclar = arastirma_merkezi.sembol_icin_kaynak_bul(sembol)
    if not sonuclar:
        sonuclar = arastirma_merkezi.genel_piyasa_basliklari(5)
        return {"sembole_ozel": False, "haberler": sonuclar}
    return {"sembole_ozel": True, "haberler": sonuclar}

@app.post("/api/kasa/gorsel-aktar")
async def gorsel_aktar(files: List[UploadFile] = File(...)):
    """
    Portföy ekran görüntülerini (banka/aracı kurum uygulaması vb.) okuyup
    OCR ile sembol/adet/maliyet çıkarır ve otomatik olarak kasaya ekler.
    Not: Şu an yalnızca FOTOĞRAF/ekran görüntüsü destekleniyor (video değil) -
    goruntu_isleyici.py içinde video çözümleme bulunmuyor.
    """
    kasa = kasa_oku()
    eklenenler = []
    hatalar = []

    for dosya in files:
        try:
            icerik = await dosya.read()
            metin = goruntu_ajani.resimden_metin_cikar(icerik)
            adaylar = goruntu_ajani.portfoy_ayikla(metin)

            if not adaylar:
                hatalar.append(f"{dosya.filename}: varlık okunamadı")
                continue

            for aday in adaylar:
                sembol_temiz = str(aday.get("sembol", "")).upper().strip()
                if not sembol_temiz:
                    continue

                mevcut = next((k for k in kasa if k.get("sembol") == sembol_temiz), None)
                if mevcut:
                    mevcut["adet"] = float(aday.get("adet", mevcut.get("adet", 0.0)))
                    mevcut["maliyet"] = float(aday.get("maliyet", mevcut.get("maliyet", 0.0)))
                    eklenenler.append(mevcut)
                else:
                    yeni = {
                        "id": str(uuid.uuid4())[:8],
                        "sembol": sembol_temiz,
                        "adet": float(aday.get("adet", 0.0)),
                        "maliyet": float(aday.get("maliyet", 0.0)),
                        "tur": varlik_turu_belirle(sembol_temiz)
                    }
                    kasa.append(yeni)
                    eklenenler.append(yeni)
        except Exception as e:
            hatalar.append(f"{dosya.filename}: {e}")

    if eklenenler:
        kasa_kaydet(kasa)

    return {"eklenen_adet": len(eklenenler), "adaylar": eklenenler, "hatalar": hatalar}


@app.post("/api/kasa/sil")
def kasa_sil(istek: SilmeIstegi):
    kasa = kasa_oku()
    yeni_kasa = [k for k in kasa if k.get("id") not in istek.idler]
    kasa_kaydet(yeni_kasa)
    return {"silinen_adet": len(kasa) - len(yeni_kasa)}

@app.delete("/api/kasa/sifirla")
def kasa_sifirla():
    kasa_kaydet([])
    return {"durum": "Kasa temizlendi"}

@app.get("/sw.js")
def get_sw():
    if os.path.exists("sw.js"):
        return FileResponse("sw.js", media_type="application/javascript")
    return HTMLResponse("", status_code=204)

@app.get("/", response_class=HTMLResponse)
def index():
    dosya = "index.html" if os.path.exists("index.html") else "finans.html"
    with open(dosya, "r", encoding="utf-8") as f:
        return f.read()

def calistir():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    calistir()