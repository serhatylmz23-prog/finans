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
from asistan_motoru import asistan_motoru

app = FastAPI(title="SyFinansOtağı")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PWA (kurulabilir uygulama) ikonları ve manifest desteği
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
        "gumus": {"gram": 89.50, "kaynak": "Spot Ons (başlangıç/yedek)", "guven": 50, "guncelleme": "-"}
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

class AsistanIstegi(BaseModel):
    soru: str


@app.get("/api/piyasa/ozet")
def get_piyasa():
    now = time.time()
    if now - CACHE_PIYASA["son_guncelleme"] > 5:
        try:
            doviz = kaynak_merkezi.doviz_getir("USDTRY")
            altin = kaynak_merkezi.altin_fiyatlari_getir()
            bist = kaynak_merkezi.hisse_fiyat_getir("XU100")
            gumus = kaynak_merkezi.gumus_fiyatlari_getir()

            if doviz.get("fiyat", 0) > 0:
                CACHE_PIYASA["veri"]["doviz"] = doviz
            if altin.get("gram", 0) > 0:
                CACHE_PIYASA["veri"]["altin"] = altin
            if bist.get("fiyat", 0) > 0:
                CACHE_PIYASA["veri"]["bist"] = bist
            if gumus.get("gram", 0) > 0:
                CACHE_PIYASA["veri"]["gumus"] = gumus

            CACHE_PIYASA["son_guncelleme"] = now
        except Exception:
            pass
    return CACHE_PIYASA["veri"]


@app.post("/api/asistan/sor")
def asistan_sor(istek: AsistanIstegi):
    """Kullanıcının portföyü ve piyasa hakkında doğal dilde sorduğu soruları yanıtlar."""
    kasa = kasa_oku()
    yanit = asistan_motoru.soru_yanitla(istek.soru, kasa)
    return {"durum": "Basarili", "yanit": yanit}


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
    gumus_gram = float(piyasa.get("gumus", {}).get("gram", 89.50))

    for varlik in kasa:
        sembol = str(varlik.get("sembol", "")).upper().strip()
        tur = varlik.get("tur") or varlik_turu_belirle(sembol)
        varlik["tur"] = tur

        if kategori and kategori not in ["Tümü", "Tumu", ""]:
            if kategori.lower() != tur.lower():
                continue

        aylik_getiri = "-"
        yillik_getiri = "-"
        maliyet = float(varlik.get("maliyet", 0.0))
        fiyat = 0.0
        veri_kaynagi = "Bilinmiyor"
        veri_kaynagi_guveni = 60.0

        if "ALTIN.S1" in sembol or "ALTINS1" in sembol or "S1" in sembol:
            veri = kaynak_merkezi.hisse_fiyat_getir("ALTIN")
            fiyat = float(veri.get("fiyat", 0.0) or 0.0)
            veri_kaynagi = veri.get("kaynak", "Bilinmiyor")
            veri_kaynagi_guveni = float(veri.get("guven", 45))
            if fiyat <= 0:
                fiyat = round(altin_gram * 0.0101, 2)
                veri_kaynagi = "TAHMİNİ (BIST'ten ALTIN.IS alınamadı, spot altın bazlı hesap)"
                veri_kaynagi_guveni = 40.0
            getiri = kaynak_merkezi.gercek_getiri_hesapla("ALTIN.IS") or kaynak_merkezi.gercek_getiri_hesapla("GC=F")
            if getiri:
                aylik_getiri = f"%{getiri['aylik_getiri']}"
                yillik_getiri = f"%{getiri['yillik_getiri']}"

        elif "XAG" in sembol or "GUMUS" in sembol or "GÜMÜŞ" in sembol:
            fiyat = gumus_gram
            veri_kaynagi = piyasa["gumus"].get("kaynak", "Spot Ons (Gümüş)")
            veri_kaynagi_guveni = float(piyasa["gumus"].get("guven", 85))
            getiri = kaynak_merkezi.gercek_getiri_hesapla("SI=F")
            if getiri:
                aylik_getiri = f"%{getiri['aylik_getiri']}"
                yillik_getiri = f"%{getiri['yillik_getiri']}"

        elif "USD" in sembol:
            fiyat = doviz_fiyat
            veri_kaynagi = piyasa["doviz"].get("kaynak", "Piyasa Kuru")
            veri_kaynagi_guveni = float(piyasa["doviz"].get("guven", 90))
            getiri = kaynak_merkezi.gercek_getiri_hesapla("USDTRY=X")
            if getiri:
                aylik_getiri = f"%{getiri['aylik_getiri']}"
                yillik_getiri = f"%{getiri['yillik_getiri']}"

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

        elif len(sembol) == 3 and not sembol.endswith("IS") and sembol not in ["XAG", "XAU"]:
            try:
                fon_veri = fon_takip.fon_bilgisi_getir(sembol)
                cekilen_fiyat = float(fon_veri.get("fiyat", 0.0))
                if cekilen_fiyat > 0:
                    fiyat = cekilen_fiyat
                    veri_kaynagi = "TEFAS"
                    veri_kaynagi_guveni = 90.0
                    aylik_ham = fon_veri.get("aylik_getiri")
                    yillik_ham = fon_veri.get("yillik_getiri")
                    if aylik_ham is not None and yillik_ham is not None:
                        aylik_getiri = f"%{aylik_ham}"
                        yillik_getiri = f"%{yillik_ham}"
                else:
                    fiyat = maliyet
                    veri_kaynagi = fon_veri.get("durum", "TEFAS'a ulaşılamadı — son bilinen maliyet")
                    veri_kaynagi_guveni = 40.0
            except Exception:
                fiyat = maliyet
                veri_kaynagi_guveni = 40.0

        else:
            try:
                hisse_veri = kaynak_merkezi.hisse_fiyat_getir(sembol)
                cekilen_fiyat = float(hisse_veri.get("fiyat", 0.0))
                fiyat = cekilen_fiyat if cekilen_fiyat > 0 else maliyet
                veri_kaynagi = hisse_veri.get("kaynak", "Bilinmiyor")
                veri_kaynagi_guveni = float(hisse_veri.get("guven", 60))

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
    return {
        "veri_kaynaklari": kaynak_merkezi.durum_raporu(),
        "acik_kaynak_arastirma": arastirma_merkezi.durum(),
    }


@app.get("/api/kasa/arastir/{sembol}")
def get_sembol_arastirma(sembol: str):
    sonuclar = arastirma_merkezi.sembol_icin_kaynak_bul(sembol)
    if not sonuclar:
        sonuclar = arastirma_merkezi.genel_piyasa_basliklari(5)
        return {"sembole_ozel": False, "haberler": sonuclar}
    return {"sembole_ozel": True, "haberler": sonuclar}


@app.get("/api/kasa/detay/{sembol}")
def get_sembol_detay(sembol: str, tur: Optional[str] = Query(None)):
    sembol = sembol.upper().strip()
    tur = (tur or "").lower()

    usd_kuru = 0.0
    try:
        usd_kuru = float(kaynak_merkezi.doviz_getir("USDTRY").get("fiyat", 0.0))
    except Exception:
        pass

    if tur == "fon" or (len(sembol) == 3 and sembol not in ["XAG", "XAU"]):
        fon_veri = fon_takip.fon_bilgisi_getir(sembol)
        if fon_veri.get("fiyat", 0) > 0:
            piyasa_degeri_try = fon_veri.get("piyasa_degeri")
            return {
                "sembol": sembol, "tur": "Fon",
                "piyasa_degeri_try": piyasa_degeri_try,
                "piyasa_degeri_usd": round(piyasa_degeri_try / usd_kuru, 2) if (piyasa_degeri_try and usd_kuru > 0) else None,
                "yatirimci_sayisi": fon_veri.get("yatirimci_sayisi"),
                "pay_sayisi": fon_veri.get("pay_adedi"),
                "temettu_tarihi": None,
                "durum": fon_veri.get("durum"),
            }

    ek = kaynak_merkezi.hisse_ek_bilgi_getir(sembol)
    piyasa_degeri_try = ek.get("piyasa_degeri_try")
    return {
        "sembol": sembol, "tur": "Hisse",
        "piyasa_degeri_try": piyasa_degeri_try,
        "piyasa_degeri_usd": round(piyasa_degeri_try / usd_kuru, 2) if (piyasa_degeri_try and usd_kuru > 0) else None,
        "yatirimci_sayisi": None,
        "pay_sayisi": ek.get("pay_sayisi"),
        "temettu_tarihi": ek.get("temettu_tarihi"),
        "temettu_verimi": ek.get("temettu_verimi"),
        "durum": "yfinance .info üzerinden güncellendi",
    }


@app.post("/api/kasa/gorsel-aktar")
async def gorsel_aktar(files: List[UploadFile] = File(...)):
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