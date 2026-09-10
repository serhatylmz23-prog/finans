# SyFinansOtağı — Güncelleme Notları

## ⚠️ Önce bunu oku: API anahtarları

`.env.local` içinde gerçek (canlı) API anahtarların düz metin olarak duruyordu
(Finnhub, Alpha Vantage, ExchangeRate-API, GoldAPI, CoinGecko). Bu dosya bana
bu sohbet üzerinden ulaştığı için artık "yalnızca sende olan bir sır" değil.
Önerim:
- Mümkün olan anahtarları ilgili panellerden **iptal edip yeniden üret**.
- `.env.local` dosyasını asla bir zip/repo/paylaşım içinde dışarı çıkarma
  (eklediğim `.gitignore` bunu Git için engelliyor, ama zip'leyip birine
  gönderirsen yine dışarı çıkar).

## Bu turda ne değişti

1. **Video desteği** — `goruntu_isleyici.py` artık videodan eşit aralıklarla
   kare çıkarıp (varsayılan 8 kare) her karede OCR çalıştırıyor ve sonuçları
   birleştiriyor (`videodan_metin_cikar`). `main.py` içindeki
   `/api/kasa/gorsel-aktar` artık dosyanın video mu foto mu olduğunu
   otomatik ayırt ediyor.
2. **Sayı ayrıştırma hatası düzeltildi** — eski kod `"80.67"` gibi bir ondalık
   değeri bindelik ayıracı sanıp `8067`'ye çeviriyordu; bu maliyet/kâr-zarar
   hesaplarını ciddi şekilde bozardı. Yeni `_sayi_coz()` fonksiyonu hem
   `"80,67"`, hem `"80.67"`, hem `"1.234,56"` biçimlerini doğru okuyor.
   (Sentetik test görsel/videolarla doğrulandı.)
3. **Kategoriler** — Kapsam dokümanındaki Kasam alt başlıklarına uygun olarak
   her varlık otomatik sınıflandırılıyor: *Hisselerim / Fonlarım / Dövizlerim
   / Kıymetli madenlerim*. Arayüzde sekmelerle filtreleniyor.
4. **Sıralama** — Tablo başlıklarına tıklayarak (Adet, Maliyet, Canlı Fiyat,
   K/Z %, Toplam Tutar, Güven) artan/azalan sıralama yapılabiliyor;
   `/api/kasa/analiz?sirala=...&yon=asc|desc&kategori=...` parametreleriyle
   API üzerinden de kullanılabiliyor.
5. **Toplu / tekil silme** — zaten vardı, korundu ve kategoriyle birlikte
   çalışacak şekilde güncellendi.
6. **Çoklu dosya + önizleme + sürükle-bırak** — birden fazla foto/video
   seçilebiliyor, yüklemeden önce küçük önizlemeler görünüyor, tek tek
   kaldırılabiliyor, işlenirken durum göstergesi çıkıyor.
7. **PWA (kurulabilir uygulama) desteği** — `manifest.json` + `sw.js` eklendi,
   `finans.html` bunları bağlıyor. Bir sunucuda çalıştırıp telefonundan
   Safari/Chrome ile açtığında "Ana ekrana ekle" ile gerçek bir uygulama
   ikonu/splash ekranıyla kurulabiliyor; masaüstünde Chrome/Edge "Uygulamayı
   yükle" seçeneğini gösteriyor.
8. `requirements.txt` düzeltildi — kod FastAPI/uvicorn kullanıyordu ama dosya
   Flask listeliyordu; artık gerçek bağımlılıklarla eşleşiyor.

## Kapsam dokümanına göre henüz eksik olanlar

`SyFinansOtağı_Kapsamı.txt` çok daha geniş bir yapı tanımlıyor (TCMB/KAP/TEFAS
canlı bağlantıları, Planlar sekmesi — bütçe dağılımı/kademeli alım-satım,
Analiz sekmesinde Kanıt Gücü/Risk/Adaylar/Piyasa davranışı, "Kaşif" araştırma
ajanı, kendi kendini geliştiren öğrenme katmanı). Zip'te bunların kod tarafı
yoktu; `__pycache__` içinde kaynağı artık mevcut olmayan derlenmiş
(`.pyc`) dosyalar vardı (`kasa.py`, `planlar.py`, `alarm_sistemi.py`,
`kendini_gelistir.py`, `syfinans_ajan.py`, `web_scraper.py`, eski
`kaynak_merkezi.py`) — muhtemelen önceki bir sürümden kalma. Bunları
decompile etmeyi denemedim çünkü Python 3.14 bytecode'u için güvenilir bir
decompiler yok; bunun yerine kapsam dokümanına göre sıfırdan yazmak daha
sağlıklı. İstersen bir sonraki adımda bunlardan birini (örn. Planlar veya
Kaşif) birlikte kurabiliriz.

`icons/` altındaki `SYK_FINANS_OTAGI_RUNTIME_v1.0` ve `SYK_ICON_ENGINE_*`
klasörleri gerçek veri bağlantısı olmayan marka/ikon sistemleri
(kendi `manifest.json`'ları `"market_data_connector_included": false` diyor)
— görsel kimlik hazır ama işlevsellik değil.

## Gerçekçi kapsam notu (iOS / Android / masaüstü)

Bu sohbet ortamından App Store / Play Store'a native bir uygulama
yayınlayamam, sürekli (7/24) çalışan bir bulut sunucusu da kuramam/işletemem
— bunlar Xcode/Android Studio, geliştirici hesapları ve gerçek bir hosting
gerektirir. Yukarıdaki PWA yaklaşımı, bugün elimdeki araçlarla ulaşabileceğin
en gerçekçi "üç platformda da kurulabilir tek uygulama" çözümü: kodu kendi
bilgisayarında, ev sunucunda ya da ucuz bir VPS'te çalıştırırsan, telefon ve
masaüstünden gerçek bir uygulama gibi kurulup kullanılabilir.

Ajanlar konusunda kapsam dokümanındaki kural korunuyor: sistem hiçbir zaman
kendi başına emir vermiyor, yalnızca analiz/öneri üretiyor
(`Kendi kendine al/sat: HAYIR`).

## Mevcut kasandaki bozuk kayıtlar hakkında

Test ettiğim gerçek ekran görüntülerinde şunu fark ettim: `kasa_verileri.json`
içinde zaten **eski (düzeltilmemiş) parser'ın ürettiği hatalı kayıtlar** var:

- `DEGER: adet 19522, maliyet 52` → aslında "Günlük Değer **19.522,52** TL"
  yazısının TL tutarı ikiye bölünüp sembol/adet/maliyet sanılmış.
- `AYA: adet 3275, maliyet 62` → aslında "₺**3.275,62**" tutarı.
- `DEI: adet 4812, maliyet 99` → aslında "DFI" sembolünün yanlış okunması +
  "₺**4.812,99**" tutarı.
- `EAL`, `EMR` de büyük ihtimalle benzer kaynaklı.

Yeni parser bu ekran tiplerini artık doğru okuyor, ama **geçmişte eklenmiş
bu hatalı kayıtları otomatik silmedim** (yanlışlıkla doğru bir kaydı
silmek istemedim). Arayüzdeki "Fonlarım" ve "Hisselerim" sekmelerinden bu
satırları gözden geçirip, gerçek dışı olanları (checkbox işaretleyip
"Seçilenleri Sil" ile) temizlemeni, sonra ilgili ekran görüntülerini
yeniden yüklemeni öneririm — bu sefer doğru ayrıştırılacaklar.

## Bu turda eklenen yeni format desteği

Gönderdiğin 4 farklı ekran tipini test ettim, hepsi artık doğru okunuyor:
1. **Broker portföy tablosu** (Sembol/Miktar/Ort.Mlyt./K-Z) — zaten çalışıyordu.
2. **Banka kıymetli maden hesabı** ("Vadesiz XAG ... 20,16 XAG") — çalışıyordu.
3. **TEFAS fon detay kartı** ("... FONU" başlığı + "Günlük Değer" / "Ortalama
   Maliyet" satırları) — **yeni eklendi**. Bu tarz kayıtlar `adet=1`,
   `son_bilinen_deger` (o anki TL değeri) ve `maliyet` (TL bazlı ortalama
   maliyet) olarak saklanıyor; TEFAS'a canlı bağlantı olmadığı için fiyat
   her yeni ekran görüntüsü yüklendiğinde güncelleniyor.
4. **Uygulama ana ekranı listesi** (Midas tarzı: sembol + `₺değer` +
   değişim satırı) — **yeni eklendi**. Aynı şekilde `son_bilinen_deger`
   olarak saklanıyor; bu formatta maliyet bilgisi ekranda yer almadığı için
   `maliyet=0` kalıyor (kâr/zarar % hesaplanamıyor, "TUT" varsayılan
   tavsiyesi veriliyor) — bunu istersen tablo satırındaki kategori
   menüsünün yanına maliyet elle girme alanı ekleyerek tamamlayabiliriz.
5. Aynı sembol için değer güncellenirse (örn. AYA'yı bir hafta sonra tekrar
   yüklersen) **yeni kayıt açmıyor, mevcut kaydı güncelliyor**.

## Çalıştırma

```bash
pip install -r requirements.txt
# Tesseract OCR motorunun sistemde kurulu olması gerekir (Windows: Tesseract-OCR,
# Linux/Mac: apt/brew install tesseract-ocr tesseract-ocr-tur)
python main.py
# tarayıcıdan http://localhost:8000 adresini aç
```
