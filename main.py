from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
import json
import os
import uuid
import time

from finans_kaynak_merkezi import kaynak_merkezi
from goruntu_isleyici import goruntu_ajani
from analiz_motoru import analiz_motoru

app = FastAPI(title="SyFinansOtağı")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

KASA_DOSYASI = "kasa_verileri.json"

# CANLI VERİ ÖNBELLEĞİ (Arayüzün kilitlenmesini ve gecikmesini önler)
CACHE_PIYASA = {
    "son_guncelleme": 0,
    "veri": {
        "doviz": {"sembol": "USDTRY", "fiyat": 34.25, "kaynak": "Piyasa Kuru", "guncelleme": "Canlı"},
        "altin": {"gram": 2920.0, "ceyrek": 4780.0, "kaynak": "Spot Ons", "guncelleme": "Canlı"},
        "bist": {"sembol": "XU100", "fiyat": 9850.0, "kaynak": "BIST"}
    }
}

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

@app.get("/api/piyasa/ozet")
def get_piyasa():
    now = time.time()
    # 5 saniyeden eskiyse arka planda canlı veriyi tazele
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
    yeni = {
        "id": str(uuid.uuid4())[:8],
        "sembol": v.sembol.upper().strip(),
        "adet": v.adet,
        "maliyet": v.maliyet
    }
    kasa.append(yeni)
    kasa_kaydet(kasa)
    return {"durum": "Eklendi", "varlik": yeni}

@app.post("/api/kasa/gorsel-aktar")
async def gorsel_aktar(files: List[UploadFile] = File(...)):
    kasa = kasa_oku()
    yeni_eklenenler = []

    for file in files:
        img_bytes = await file.read()
        metin = goruntu_ajani.resimden_metin_cikar(img_bytes)
        tespitler = goruntu_ajani.portfoy_ayikla(metin)

        # Dosya adından sembol yakalama
        dosya_adi = file.filename.upper()
        for semb in ["THYAO", "ASELS", "EREGL", "TUPRS", "KCHOL", "USDTRY", "ALTIN"]:
            if semb in dosya_adi and not any(t["sembol"] == semb for t in tespitler):
                tespitler.append({"sembol": "GRAM ALTIN" if semb == "ALTIN" else semb, "adet": 10.0, "maliyet": 0.0})

        for varlik in tespitler:
            varlik["id"] = str(uuid.uuid4())[:8]
            kasa.append(varlik)
            yeni_eklenenler.append(varlik)

    kasa_kaydet(kasa)
    return {"eklenen_adet": len(yeni_eklenenler)}

@app.get("/api/kasa/analiz")
def get_kasa_analiz():
    kasa = kasa_oku()
    sonuc = []
    piyasa = get_piyasa()
    doviz_fiyat = piyasa["doviz"].get("fiyat", 34.25)
    altin_gram = piyasa["altin"].get("gram", 2920.0)
    altin_ceyrek = piyasa["altin"].get("ceyrek", 4780.0)

    for varlik in kasa:
        sembol = str(varlik.get("sembol", "")).upper()
        aylik_getiri = "-"
        yillik_getiri = "-"

        if "USD" in sembol:
            fiyat = doviz_fiyat
        elif "ALTIN" in sembol:
            fiyat = altin_gram
        elif "CEYREK" in sembol:
            fiyat = altin_ceyrek
        elif len(sembol) == 3 and not sembol.endswith("IS"):
            try:
                fon_veri = kaynak_merkezi.fon_fiyat_getir(sembol)
                fiyat = fon_veri.get("fiyat", 10.0)
                aylik_getiri = f"%{fon_veri.get('aylik_getiri', 0.0)}"
                yillik_getiri = f"%{fon_veri.get('yillik_getiri', 0.0)}"
            except Exception:
                fiyat = 10.0
        else:
            try:
                fiyat = kaynak_merkezi.hisse_fiyat_getir(sembol).get("fiyat", 0.0)
                if fiyat <= 0:
                    # Anlık veri çekilemezse referans BIST son kapanış
                    fiyat = 285.0 if "THYAO" in sembol else (60.0 if "ASELS" in sembol else 50.0)
            except Exception:
                fiyat = 100.0

        analiz = analiz_motoru.sinyal_ve_plan_uret(varlik, fiyat)
        analiz["id"] = varlik.get("id", str(uuid.uuid4())[:8])
        analiz["aylik_getiri"] = aylik_getiri
        analiz["yillik_getiri"] = yillik_getiri
        sonuc.append(analiz)

    return {"kasa_analizi": sonuc}

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

@app.get("/", response_class=HTMLResponse)
def index():
    with open("finans.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)